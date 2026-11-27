"""FastAPI backend serving the GisMarket Intelligence AI REST API and React SPA."""

import asyncio
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.auth.service import AuthService, UserRecord, create_session_token, verify_session_token
from src.config import settings
from src.database.connection import db_manager
from src.evaluation.ragas_guard import RagasGuard
from src.inference.ollama_client import OllamaClient
from src.inference.pdf_exporter import export_report_to_pdf_bytes
from src.inference.prompts import (
    CONVERSATIONAL_SWZ_SYSTEM_PROMPT,
    STRICT_GROUNDING_SYSTEM_PROMPT,
    build_chat_prompt,
    build_universal_report_prompt,
)
from src.inference.report_generator import TenderReportGenerator
from src.ingestion.client import NUTS_PROVINCE_MAP
from src.retrieval.pipeline import RetrievalPipeline
from src.retrieval.query_expander import expand_swz_query

logger = logging.getLogger("src.api")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

# In-memory caches for instant repeat responses
_SUMMARY_CACHE: Dict[str, Dict[str, Any]] = {}
_PDF_CACHE: Dict[str, bytes] = {}
_OLLAMA_HEALTH_CACHE: Dict[str, Any] = {"ok": False, "ts": 0.0}
_PIPELINE_INSTANCE: Optional[RetrievalPipeline] = None


def _get_pipeline() -> RetrievalPipeline:
    global _PIPELINE_INSTANCE
    if _PIPELINE_INSTANCE is None:
        _PIPELINE_INSTANCE = RetrievalPipeline()
    return _PIPELINE_INSTANCE


def _extract_tender_metrics(full_text: str) -> Dict[str, Any]:
    """Extracts KIO risk, penalties, wadium, and competitors from tender SWZ text."""
    low = full_text.lower()

    if ".str" in low and ("bez udostępnienia" in low or "bez udostepnienia" in low):
        kio_level, kio_label, kio_color = "HIGH", "WYSOKIE", "#dc2626"
        kio_sub = "Art. 16 i 99 PZP — wymóg zamkniętego formatu .str"
        format_score, has_lockin = 94, True
    elif ".giv" in low or "pozornej równoważności" in low or "konektora replikacji" in low:
        kio_level, kio_label, kio_color = "MEDIUM", "ŚREDNIE", "#d97706"
        kio_sub = "Art. 99 ust. 5 PZP — koszt konektora GEO-INFO (.giv)"
        format_score, has_lockin = 62, True
    elif "otwartym standardzie gml" in low or "brak ryzyka vendor lock-in" in low:
        kio_level, kio_label, kio_color = "LOW", "NISKIE", "#059669"
        kio_sub = "Pełna zgodność ze standardem GML 2021 i GeoTIFF"
        format_score, has_lockin = 18, False
    else:
        kio_level, kio_label, kio_color = "LOW", "UMIARKOWANE", "#475569"
        kio_sub = "Standardowe wymogi ogłoszenia BZP"
        format_score, has_lockin = 35, False

    pen_match = re.search(r"kar[aęy][^.\n]{1,65}?(\d+(?:[.,]\d+)?%)\s*(?:wynagrodzenia|wartości)", full_text, re.IGNORECASE)
    penalty_rate = f"{pen_match.group(1)} / dzień" if pen_match else "Wg umowy SWZ"
    if "nie określono górnego limitu" in low or "bez gornego limitu" in low or "bez górnego limitu" in low:
        penalty_sub = "Brak górnego limitu kar (naruszenie art. 436 PZP)"
        penalty_score, has_penalties = 90, True
    else:
        cap_match = re.search(r"limitem\s+(\d+%)|wynosi\s+(\d+%)\s+całkowitego", full_text, re.IGNORECASE)
        cap_val = (cap_match.group(1) or cap_match.group(2)) if cap_match else "zgodny z PZP"
        penalty_sub = f"Górny limit kar: {cap_val} umowy brutto"
        penalty_score = 32 if "0,2%" in penalty_rate else 48
        has_penalties = False

    wad_match = re.search(r"wadium[^0-9]{1,35}(\d[\d\s]*,\d{2})\s*(?:PLN|zł)", full_text, re.IGNORECASE)
    wadium_str = f"{wad_match.group(1).strip()} PLN" if wad_match else "Brak wymogu"

    competitors: List[Dict[str, str]] = []
    system_tags: List[str] = []
    if "ewmapa" in low or "geobid" in low:
        competitors.append({"name": "Geobid Sp. z o.o.", "product": "EWMAPA / OŚRODEK", "advantage": "Wymóg przekazywania operatów w zamkniętym formacie natywnym .str"})
        system_tags.append("Geobid: EWMAPA (.str)")
    if "impa" in low or "geo-system" in low:
        competitors.append({"name": "Geo-System Sp. z o.o.", "product": "iMPA / e-Gmina", "advantage": "Wymagana bezpośrednia integracja z portalem mapowym gminy"})
        system_tags.append("Geo-System: iMPA")
    if "geo-info" in low or "systherm" in low:
        competitors.append({"name": "Systherm-Info Sp. z o.o.", "product": "GEO-INFO V (.giv)", "advantage": "Wymagana dwukierunkowa replikacja z bazą powiatową GEO-INFO"})
        system_tags.extend(["Systherm: GEO-INFO (.giv)", "OGC WMS/WFS"])
    if "ewopis" in low or "turboewid" in low:
        competitors.append({"name": "Geomatyka-Kraków s.c.", "product": "EWOPIS / TurboEWID", "advantage": "System bazowy z otwartym interfejsem GML"})
        system_tags.extend(["Standard GML 2021", "EWOPIS / TurboEWID"])
    if not competitors:
        competitors.append({"name": "Integratorzy IT / JST", "product": "Systemy dziedzinowe BZP", "advantage": "Weryfikacja referencji i certyfikatów wdrożeniowych"})
        system_tags.append("Zamówienie BZP")

    personnel_score = 68 if "5 lat" in low else (52 if "3 lata" in low else 45)
    return {
        "kio_level": kio_level,
        "kio_label": kio_label,
        "kio_color": kio_color,
        "kio_sub": kio_sub,
        "has_lockin": has_lockin,
        "has_penalties": has_penalties,
        "penalty_rate": penalty_rate,
        "penalty_sub": penalty_sub,
        "wadium_str": wadium_str,
        "format_score": format_score,
        "penalty_score": penalty_score,
        "personnel_score": personnel_score,
        "competitors": competitors,
        "system_tags": system_tags,
    }


def _fetch_procurements_rows() -> List[Dict[str, Any]]:
    """Loads procurement list from PostgreSQL with NUTS normalization."""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute(
                """
                SELECT
                    ocds_id, title, municipality_name, voivodeship,
                    COALESCE(estimated_budget_pln, 0.0) AS estimated_budget_pln,
                    date_published, date_deadline, status
                FROM procurements
                ORDER BY
                    CASE ocds_id
                        WHEN 'ocds-148610-niepolomice' THEN 0
                        WHEN 'ocds-148610-kornik' THEN 1
                        WHEN 'ocds-148610-piaseczno' THEN 2
                        ELSE 3
                    END,
                    estimated_budget_pln DESC,
                    date_published DESC
                LIMIT 100;
                """
            )
            rows = cur.fetchall()
        if rows:
            return [
                {
                    "id": str(r[0]),
                    "title": str(r[1]),
                    "municipality": str(r[2]),
                    "voivodeship": NUTS_PROVINCE_MAP.get(str(r[3]).strip().upper(), str(r[3])),
                    "budget_pln": float(r[4] or 0.0),
                    "published": str(r[5])[:10],
                    "deadline": str(r[6])[:10],
                    "status": str(r[7]),
                }
                for r in rows
            ]
    except Exception as exc:
        logger.warning("Could not fetch procurements from PostgreSQL: %s", exc)

    return [
        {
            "id": "ocds-148610-niepolomice",
            "title": "Modernizacja bazy BDOT500, GESUT oraz EGiB dla Miasta i Gminy Niepołomice",
            "municipality": "Urząd Miasta i Gminy w Niepołomicach",
            "voivodeship": "Małopolskie",
            "budget_pln": 320000.0,
            "published": "2026-10-15",
            "deadline": "2026-11-20",
            "status": "ACTIVE",
        },
        {
            "id": "ocds-148610-kornik",
            "title": "Wdrożenie Zintegrowanego Systemu Informacji Przestrzennej (SIP) i e-usług MPZP",
            "municipality": "Urząd Miasta i Gminy Kórnik",
            "voivodeship": "Wielkopolskie",
            "budget_pln": 480000.0,
            "published": "2026-10-18",
            "deadline": "2026-11-25",
            "status": "ACTIVE",
        },
    ]


def _fetch_full_tender_context(ocds_id: str) -> str:
    try:
        with db_manager.get_cursor() as cur:
            cur.execute(
                """
                SELECT pn.section_title, pn.content
                FROM parent_nodes pn
                JOIN attachments a ON pn.attachment_id = a.id
                JOIN procurements p ON a.procurement_id = p.id
                WHERE p.ocds_id = %s
                ORDER BY pn.created_at ASC;
                """,
                (ocds_id,),
            )
            rows = cur.fetchall()
            if rows:
                return "\n\n".join(f"# {r[0] or 'Sekcja'}\n{r[1]}" for r in rows)
    except Exception as exc:
        logger.debug("Could not fetch parent_nodes for %s: %s", ocds_id, exc)
    return ""


def _parse_report_sections(raw_output: str) -> Dict[str, str]:
    def _clean(prefix: str) -> str:
        raw_sec = TenderReportGenerator._extract_section(raw_output, prefix)
        if not raw_sec:
            return ""
        sentences = TenderReportGenerator._split_clean_sentences(raw_sec)
        return " ".join(sentences) if sentences else raw_sec.strip()

    return {
        "summary": _clean("### 1. Podsumowanie"),
        "legal_barriers": _clean("### 2. Zidentyfikowane"),
        "competitors": _clean("### 3. Zestawienie"),
        "recommendations": _clean("### 5. Rekomendacje"),
    }


async def _build_tender_summary(ocds_id: str) -> Dict[str, Any]:
    if ocds_id in _SUMMARY_CACHE:
        return _SUMMARY_CACHE[ocds_id]

    tenders = _fetch_procurements_rows()
    tender = next((t for t in tenders if t["id"] == ocds_id), None)
    if tender is None:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono postępowania {ocds_id}")

    full_ctx = _fetch_full_tender_context(ocds_id)
    if not full_ctx:
        pipeline = _get_pipeline()
        items = pipeline.retrieve(query="wymagania format .str GML kary umowne wadium", procurement_id=ocds_id, top_k=5)
        full_ctx = "\n\n---\n\n".join(
            it["content"] if isinstance(it, dict) else getattr(it, "content", str(it))
            for it in items
        ) or "Brak dokumentów w bazie."

    generator = TenderReportGenerator()
    report = await generator.generate(
        procurement_id=ocds_id,
        title=tender["title"],
        municipality=tender["municipality"],
        context=full_ctx,
        use_fast_synthesis=True,
    )
    guard = RagasGuard(min_faithfulness=0.95)
    eval_res = guard.evaluate_claims_grounding(report.markdown_report, [full_ctx])
    sections = _parse_report_sections(report.raw_llm_output)
    metrics = _extract_tender_metrics(full_ctx)

    summary_payload = {
        "tender": tender,
        "metrics": metrics,
        "faithfulness": eval_res.faithfulness,
        "sections": sections,
        "markdown_report": report.markdown_report,
        "full_context": full_ctx,
    }
    _SUMMARY_CACHE[ocds_id] = summary_payload
    return summary_payload


_METRICS_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "wadium_str": {"type": "string"},
        "penalty_rate": {"type": "string"},
        "penalty_sub": {"type": "string"},
        "kio_sub": {"type": "string"},
    },
    "required": ["wadium_str", "penalty_rate", "penalty_sub", "kio_sub"],
}


async def _enrich_metrics_with_llm(full_ctx: str, base_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Uses Ollama structured JSON output to fill missing SWZ metrics when Ollama is online."""
    needs_enrichment = (
        base_metrics.get("wadium_str") == "Brak wymogu"
        or base_metrics.get("penalty_rate") == "Wg umowy SWZ"
    )
    if not needs_enrichment:
        return base_metrics

    client = OllamaClient(timeout=4.0)
    if not await client.check_health():
        return base_metrics

    prompt = (
        "Wyciągnij z poniższego tekstu SWZ wyłącznie faktyczne wartości i zwróć JSON.\n"
        "Jeśli brak danej w tekście, wpisz pusty string \"\".\n"
        "- wadium_str: kwota wadium z walutą (np. '9 000,00 PLN')\n"
        "- penalty_rate: stawka kary umownej (np. '0,2% / dzień')\n"
        "- penalty_sub: limit kar umownych (np. 'Górny limit: 20% umowy')\n"
        "- kio_sub: krótkie uzasadnienie ryzyka KIO lub PZP\n\n"
        f"TEKST SWZ:\n{full_ctx[:3500]}"
    )
    extracted = await client.generate_json(prompt=prompt, schema=_METRICS_JSON_SCHEMA)
    if not extracted:
        return base_metrics

    merged = dict(base_metrics)
    if merged["wadium_str"] == "Brak wymogu" and extracted.get("wadium_str"):
        merged["wadium_str"] = str(extracted["wadium_str"]).strip()
    if merged["penalty_rate"] == "Wg umowy SWZ" and extracted.get("penalty_rate"):
        merged["penalty_rate"] = str(extracted["penalty_rate"]).strip()
    if extracted.get("penalty_sub") and merged["penalty_sub"].startswith("Górny limit kar: zgodny"):
        merged["penalty_sub"] = str(extracted["penalty_sub"]).strip()
    return merged


# ------------------------------------------------------------------
# Pydantic Schemas & Auth Dependencies
# ------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class UpdatePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


class ToggleActiveRequest(BaseModel):
    is_active: bool


class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    response_format: str = Field(default="Standard (SWZ)")
    history: List[Dict[str, str]] = Field(default_factory=list)


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> UserRecord:
    raw_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ", 1)[1].strip()
    elif token:
        raw_token = token.strip()

    user = verify_session_token(raw_token) if raw_token else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Brak ważnej sesji użytkownika.")
    return user


def require_admin(user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wymagane uprawnienia administratora.")
    return user


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        AuthService.ensure_schema_and_admin()
    except Exception as exc:
        logger.warning("Auth schema init deferred (PostgreSQL unreachable at startup): %s", exc)
    yield


app = FastAPI(title="GisMarket Intelligence AI API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/auth/login")
def api_login(body: LoginRequest) -> Dict[str, Any]:
    try:
        AuthService.ensure_schema_and_admin()
        user = AuthService.authenticate(body.username, body.password)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Błąd połączenia z bazą PostgreSQL: {exc}") from exc

    if user is None:
        raise HTTPException(status_code=401, detail="Nieprawidłowy login, hasło lub konto jest nieaktywne.")

    token = create_session_token(user)
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active},
    }


@app.get("/api/auth/me")
def api_me(user: UserRecord = Depends(get_current_user)) -> Dict[str, Any]:
    return {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active}


@app.get("/api/users")
def api_list_users(admin: UserRecord = Depends(require_admin)) -> List[Dict[str, Any]]:
    users = AuthService.list_users(admin)
    return [
        {"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active}
        for u in users
        if u.role != "admin"
    ]


@app.post("/api/users", status_code=201)
def api_create_user(body: CreateUserRequest, admin: UserRecord = Depends(require_admin)) -> Dict[str, Any]:
    try:
        created = AuthService.create_user(admin, username=body.username, password=body.password, role="user")
        return {"id": created.id, "username": created.username, "role": created.role, "is_active": created.is_active}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/users/{username}/password")
def api_update_password(
    username: str,
    body: UpdatePasswordRequest,
    admin: UserRecord = Depends(require_admin),
) -> Dict[str, str]:
    try:
        AuthService.update_user_password(admin, target_username=username, new_password=body.new_password)
        return {"status": "ok"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/users/{username}/active")
def api_toggle_active(
    username: str,
    body: ToggleActiveRequest,
    admin: UserRecord = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        AuthService.set_user_active(admin, target_username=username, is_active=body.is_active)
        return {"username": username, "is_active": body.is_active}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/users/{username}")
def api_delete_user(username: str, admin: UserRecord = Depends(require_admin)) -> Dict[str, str]:
    try:
        AuthService.delete_user(admin, target_username=username)
        return {"status": "deleted"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/procurements")
def api_list_procurements(_user: UserRecord = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return _fetch_procurements_rows()


@app.get("/api/procurements/{ocds_id}/summary")
async def api_procurement_summary(ocds_id: str, _user: UserRecord = Depends(get_current_user)) -> Dict[str, Any]:
    data = await _build_tender_summary(ocds_id)
    return {
        "tender": data["tender"],
        "metrics": data["metrics"],
        "faithfulness": data["faithfulness"],
        "sections": data["sections"],
    }


def _format_bzp_text(text: str) -> str:
    """Restores readable paragraph breaks for flattened BZP/SWZ announcements."""
    formatted = re.sub(r"\s+(SEKCJA\s+[IVX]+\b)", r"\n\n\1", text)
    formatted = re.sub(r"\s+(\d+\.\d+(?:\.\d+)?\.\))", r"\n\1", formatted)
    return formatted.strip()


def _extract_relevant_window(text: str, query: str, max_len: int = 750) -> str:
    """Extracts a concise excerpt centered around the first matching query term."""
    formatted = _format_bzp_text(text)
    if len(formatted) <= max_len:
        return formatted

    terms = [
        w.lower()
        for w in re.findall(r"[a-ząćęłńóśźż0-9.]{3,}", query)
        if w.lower() not in {"czy", "jak", "jaki", "jakie", "jaka", "jest", "ile", "dla", "przy", "oraz", "wynoszą", "wynosi", "dokładnie"}
    ]
    lower_text = formatted.lower()
    hit_idx = -1
    for term in terms:
        pos = lower_text.find(term[:5] if len(term) > 5 else term)
        if pos != -1:
            hit_idx = pos
            break

    if hit_idx == -1:
        return formatted[:max_len].rstrip() + "..."

    start = max(0, hit_idx - 180)
    end = min(len(formatted), start + max_len)
    if start > 0:
        space_pos = formatted.find(" ", start)
        if 0 < space_pos - start < 40:
            start = space_pos + 1
    snippet = formatted[start:end].rstrip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(formatted):
        snippet = snippet + "..."
    return snippet


def _build_llm_context_window(contexts: List[str], full_context: str, query: str, max_chars: int = 4500) -> str:
    """Builds LLM context without dropping later sections of huge single-node BZP documents."""
    raw = "\n\n---\n\n".join(contexts).strip() if contexts else full_context.strip()
    if len(raw) <= max_chars:
        return raw
    header = raw[:1500].rstrip()
    relevant = _extract_relevant_window(raw[1500:], query, max_len=max_chars - 1520)
    return f"{header}\n\n[...]\n\n{relevant}"


def _retrieve_question_context(
    ocds_id: str,
    question: str,
    full_context: str,
) -> tuple[str, List[Dict[str, Any]]]:
    """Expands colloquial queries for retrieval and builds grounded context + UI chunks."""
    pipeline = _get_pipeline()
    expanded_query = expand_swz_query(question)
    retrieved = pipeline.retrieve(
        query=expanded_query,
        procurement_id=ocds_id,
        top_candidates=30,
        top_k=3,
    )
    contexts = [
        it["content"] if isinstance(it, dict) else getattr(it, "content", str(it))
        for it in retrieved
    ]
    q_context = _build_llm_context_window(contexts, full_context, question, max_chars=4500)
    chunks = [
        {
            "section_title": it.get("section_title") or "Rozdział SWZ",
            "rerank_score": it.get("cross_encoder_score") or it.get("rerank_score") or it.get("rrf_score") or 0.98,
            "content": _extract_relevant_window(it.get("content", ""), question, max_len=750),
        }
        for it in retrieved[:3]
        if isinstance(it, dict)
    ]
    return q_context, chunks


@app.post("/api/procurements/{ocds_id}/ask")
async def api_ask_procurement(
    ocds_id: str,
    body: AskQuestionRequest,
    _user: UserRecord = Depends(get_current_user),
) -> Dict[str, Any]:
    summary = await _build_tender_summary(ocds_id)
    q_context, chunks = _retrieve_question_context(ocds_id, body.question, summary["full_context"])

    answer = ""
    engine = "fallback"
    client = OllamaClient(timeout=180.0)
    try:
        if await client.check_health():
            prompt = build_chat_prompt(
                question=body.question,
                context=q_context[:4500],
                response_format=body.response_format,
                history=body.history,
            )
            answer = await client.generate(
                prompt=prompt,
                system=CONVERSATIONAL_SWZ_SYSTEM_PROMPT,
                temperature=0.1,
            )
            if answer:
                engine = "ollama"
    except Exception as exc:
        logger.warning("Ollama /ask generation failed, using fallback (%r)", exc)

    if not answer:
        answer = _format_answer_text(
            TenderReportGenerator.answer_specific_question(body.question, q_context),
            body.response_format,
        )

    return {"question": body.question, "answer": answer, "chunks": chunks, "engine": engine}


def _format_answer_text(answer: str, response_format: str) -> str:
    if response_format == "Zwięzły (Punkty)" and answer:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", answer) if p.strip()]
        if len(parts) > 1:
            return " • ".join(parts)
    elif response_format == "Audyt PZP / KIO" and answer:
        return f"[Tryb audytu PZP/KIO] {answer}"
    return answer


@app.post("/api/procurements/{ocds_id}/ask/stream")
async def api_ask_procurement_stream(
    ocds_id: str,
    body: AskQuestionRequest,
    _user: UserRecord = Depends(get_current_user),
) -> StreamingResponse:
    summary = await _build_tender_summary(ocds_id)
    q_context, chunks = _retrieve_question_context(ocds_id, body.question, summary["full_context"])

    async def event_stream():
        yield f"data: {json.dumps({'type': 'chunks', 'chunks': chunks}, ensure_ascii=False)}\n\n"

        client = OllamaClient(timeout=180.0)
        streamed_any = False
        try:
            if await client.check_health():
                prompt = build_chat_prompt(
                    question=body.question,
                    context=q_context[:4500],
                    response_format=body.response_format,
                    history=body.history,
                )
                async for token in client.stream_generate(
                    prompt=prompt,
                    system=CONVERSATIONAL_SWZ_SYSTEM_PROMPT,
                    temperature=0.1,
                ):
                    if not streamed_any:
                        yield f"data: {json.dumps({'type': 'meta', 'engine': 'ollama'}, ensure_ascii=False)}\n\n"
                    streamed_any = True
                    yield f"data: {json.dumps({'type': 'token', 'text': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.warning("Streaming via Ollama failed, using grounded fallback (%s)", exc)

        if not streamed_any:
            yield f"data: {json.dumps({'type': 'meta', 'engine': 'fallback'}, ensure_ascii=False)}\n\n"
            notice = "*[Tryb awaryjny — Ollama niedostępna lub przekroczyła czas odpowiedzi]*\n\n"
            yield f"data: {json.dumps({'type': 'token', 'text': notice}, ensure_ascii=False)}\n\n"
            fallback = _format_answer_text(
                TenderReportGenerator.answer_specific_question(body.question, q_context),
                body.response_format,
            )
            words = fallback.split(" ")
            for i in range(0, len(words), 4):
                piece = (" " if i > 0 else "") + " ".join(words[i : i + 4])
                yield f"data: {json.dumps({'type': 'token', 'text': piece}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.015)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/procurements/{ocds_id}/report.pdf")
async def api_download_pdf(
    ocds_id: str,
    use_llm: bool = Query(default=False),
    _user: UserRecord = Depends(get_current_user),
) -> Response:
    cache_key = f"{ocds_id}:{'llm' if use_llm else 'fast'}"
    if cache_key not in _PDF_CACHE:
        summary = await _build_tender_summary(ocds_id)
        md_report = summary["markdown_report"]
        if use_llm and await OllamaClient().check_health():
            tender = summary["tender"]
            full_ctx = summary["full_context"]
            llm_report = await TenderReportGenerator().generate(
                procurement_id=ocds_id,
                title=tender["title"],
                municipality=tender["municipality"],
                context=full_ctx,
                prompt_override=build_universal_report_prompt(
                    full_ctx[:4500], tender["title"], tender["municipality"]
                ),
                use_fast_synthesis=False,
            )
            md_report = llm_report.markdown_report
        _PDF_CACHE[cache_key] = export_report_to_pdf_bytes(md_report)
    return Response(
        content=_PDF_CACHE[cache_key],
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="raport_{ocds_id}.pdf"'},
    )


@app.get("/api/system/about")
async def api_system_about(_user: UserRecord = Depends(get_current_user)) -> Dict[str, Any]:
    now = time.time()
    if now - _OLLAMA_HEALTH_CACHE["ts"] > 60.0:
        try:
            _OLLAMA_HEALTH_CACHE["ok"] = await OllamaClient().check_health()
        except Exception:
            _OLLAMA_HEALTH_CACHE["ok"] = False
        _OLLAMA_HEALTH_CACHE["ts"] = now

    return {
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_ok": _OLLAMA_HEALTH_CACHE["ok"],
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "reranker_model": settings.RERANKER_MODEL_NAME,
        "total_tenders": len(_fetch_procurements_rows()),
    }


# Serve compiled React SPA if present
if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="assets")


@app.get("/{full_path:path}")
def serve_spa(full_path: str) -> Any:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Endpoint not found")
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "FastAPI backend running. Build frontend/ to serve React UI."}
