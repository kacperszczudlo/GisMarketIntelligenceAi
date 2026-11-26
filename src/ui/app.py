import asyncio
import html
import logging
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path when invoked via `streamlit run src/ui/app.py`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
from urllib.parse import quote
from src.auth.service import AuthService, UserRecord, create_session_token, verify_session_token
from src.config import settings
from src.database.connection import db_manager
from src.evaluation.ragas_guard import RagasGuard
from src.inference.ollama_client import OllamaClient
from src.inference.pdf_exporter import export_report_to_pdf_bytes
from src.inference.report_generator import TenderReportGenerator
from src.ingestion.client import NUTS_PROVINCE_MAP
from src.retrieval.pipeline import RetrievalPipeline
from src.ui.components import (
    _compact_html,
    get_glassmorphism_stylesheet,
    get_svg_icon,
    render_brand_sidebar_header,
    render_citation_box,
    render_clickable_procurements_table,
    render_competitor_matrix,
    render_direct_answer_card,
    render_insight_section_card,
    render_kio_warning,
    render_kpi_stat_card,
    render_procurements_table,
    render_red_flag_badge,
    render_risk_profile_panel,
    render_top_utility_bar,
)

logger = logging.getLogger("src.ui.app")

st.set_page_config(
    page_title="GisMarket Intelligence AI | Audyt zamówień GIS",
    layout="wide",
    initial_sidebar_state="expanded",
)

RAG_QUESTION_TEMPLATES: Dict[str, str] = {
    "1. Format danych (.str / .giv vs otwarty GML)": (
        "Czy zamawiający narzuca zamknięty format natywny (.str lub .giv) bez dopuszczenia otwartego standardu GML?"
    ),
    "2. Kary umowne za zwłokę i limit kar (art. 436 PZP)": (
        "Jaką wysokość kary umownej za każdy dzień zwłoki przewidział zamawiający i czy umowa określa górny limit kar?"
    ),
    "3. Uprawnienia geodezyjne GUGiK i doświadczenie kadry": (
        "Jakich uprawnień zawodowych GUGiK oraz jakiego minimalnego doświadczenia wymaga zamawiający od kierownika prac?"
    ),
    "4. Wadium i zabezpieczenie należytego wykonania umowy": (
        "Ile wynosi wymagane wadium w tym postępowaniu oraz jaka jest wysokość zabezpieczenia należytego wykonania umowy?"
    ),
    "5. Kryteria oceny ofert (waga ceny, gwarancji, SLA)": (
        "Jakie są kryteria oceny ofert oraz ich wagi procentowe (cena, okres gwarancji i rękojmi, SLA)?"
    ),
    "6. Termin realizacji zamówienia i etapy odbioru": (
        "Jaki jest wymagany termin realizacji zamówienia (w dniach lub miesiącach) i jak podzielono etapy odbiorcze?"
    ),
    "7. Wymagane systemy dziedzinowe PODGiK i geoportale": (
        "Z jakim systemem dziedzinowym (np. EWMAPA, OŚRODEK, GEO-INFO, EWOPIS) lub portalem mapowym (iMPA) wymagana jest integracja?"
    ),
    "8. Podstawy odwołania do KIO i klauzule z art. 94 PZP": (
        "Które wymogi w SWZ/OPZ stanowią podstawę odwołania do KIO (art. 16 i 99 PZP) i czy zastosowano wykluczenia z art. 94 PZP?"
    ),
    "9. Własne pytanie (wpisz dowolne pytanie w polu obok)": "",
}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_procurements_from_db() -> pd.DataFrame:
    """Fetches tender notices from the PostgreSQL database and normalizes province codes."""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT 
                    ocds_id,
                    title,
                    municipality_name,
                    voivodeship,
                    COALESCE(estimated_budget_pln, 0.0) AS estimated_budget_pln,
                    date_published,
                    date_deadline,
                    status
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
            """)
            rows = cur.fetchall()
            columns = [
                "ID", "Tytuł", "Zamawiający", "Województwo", "Budżet PLN", "Publikacja", "Termin", "Status"
            ]
            if not rows:
                return pd.DataFrame(columns=columns)
            df = pd.DataFrame(rows, columns=columns)
            df["Województwo"] = df["Województwo"].apply(
                lambda val: NUTS_PROVINCE_MAP.get(str(val).strip().upper(), str(val))
            )
            df["Budżet PLN"] = pd.to_numeric(df["Budżet PLN"], errors="coerce").fillna(0.0)
            return df
    except Exception as e:
        logger.error("Błąd pobierania postępowań z bazy: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def check_ollama_health() -> bool:
    """Checks if Ollama daemon is reachable (cached for 60s to avoid UI lag)."""
    try:
        client = OllamaClient()
        return asyncio.run(client.check_health())
    except Exception:
        return False


def fetch_full_tender_context(ocds_id: str) -> str:
    """Fetches all parent node sections for a specific procurement from PostgreSQL for complete audit synthesis."""
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
    except Exception as e:
        logger.debug("Could not fetch full parent_nodes context: %s", e)
    return ""


def parse_report_sections(raw_output: str) -> Dict[str, str]:
    """Extracts the 4 structured content sections from the generated markdown report."""
    def _clean_section(header_prefix: str) -> str:
        raw_sec = TenderReportGenerator._extract_section(raw_output, header_prefix)
        if not raw_sec:
            return ""
        sentences = TenderReportGenerator._split_clean_sentences(raw_sec)
        return " ".join(sentences) if sentences else raw_sec.strip()

    return {
        "summary": _clean_section("### 1. Podsumowanie"),
        "legal_barriers": _clean_section("### 2. Zidentyfikowane"),
        "competitors": _clean_section("### 3. Zestawienie"),
        "recommendations": _clean_section("### 5. Rekomendacje"),
    }


@st.cache_resource(show_spinner=False)
def get_retrieval_pipeline() -> RetrievalPipeline:
    """Caches the BGE-M3 and Cross-Encoder pipeline across Streamlit reruns."""
    return RetrievalPipeline()


def extract_tender_metrics(full_text: str, budget_pln: float) -> Dict[str, Any]:
    """Extracts dynamic, tender-specific KPIs, risk scores, and competitors from the tender's SWZ text."""
    low = full_text.lower()

    # 1. KIO Risk & Format Score
    if ".str" in low and ("bez udostępnienia" in low or "bez udostepnienia" in low):
        kio_level = "HIGH"
        kio_label = "WYSOKIE"
        kio_color = "#dc2626"
        kio_sub = "Art. 16 i 99 PZP — wymóg zamkniętego formatu .str"
        format_score = 94
        has_lockin = True
    elif ".giv" in low or "pozornej równoważności" in low or "konektora replikacji" in low:
        kio_level = "MEDIUM"
        kio_label = "ŚREDNIE"
        kio_color = "#d97706"
        kio_sub = "Art. 99 ust. 5 PZP — koszt konektora GEO-INFO (.giv)"
        format_score = 62
        has_lockin = True
    elif "otwartym standardzie gml" in low or "brak ryzyka vendor lock-in" in low:
        kio_level = "LOW"
        kio_label = "NISKIE"
        kio_color = "#059669"
        kio_sub = "Pełna zgodność ze standardem GML 2021 i GeoTIFF"
        format_score = 18
        has_lockin = False
    else:
        kio_level = "LOW"
        kio_label = "UMIARKOWANE"
        kio_color = "#475569"
        kio_sub = "Standardowe wymogi ogłoszenia BZP"
        format_score = 35
        has_lockin = False

    # 2. Penalties & Limit
    pen_match = re.search(r"kar[aęy][^.\n]{1,65}?(\d+(?:[.,]\d+)?%)\s*(?:wynagrodzenia|wartości)", full_text, re.IGNORECASE)
    penalty_rate = f"{pen_match.group(1)} / dzień" if pen_match else "Wg umowy SWZ"
    if "nie określono górnego limitu" in low or "bez gornego limitu" in low or "bez górnego limitu" in low:
        penalty_sub = "Brak górnego limitu kar (naruszenie art. 436 PZP)"
        penalty_score = 90
        has_penalties = True
    else:
        cap_match = re.search(r"limitem\s+(\d+%)|wynosi\s+(\d+%)\s+całkowitego", full_text, re.IGNORECASE)
        cap_val = (cap_match.group(1) or cap_match.group(2)) if cap_match else "zgodny z PZP"
        penalty_sub = f"Górny limit kar: {cap_val} umowy brutto"
        penalty_score = 32 if "0,2%" in penalty_rate else 48
        has_penalties = False

    # 3. Wadium & Evaluation Criteria
    wad_match = re.search(r"wadium[^0-9]{1,35}(\d[\d\s]*,\d{2})\s*(?:PLN|zł)", full_text, re.IGNORECASE)
    wadium_str = f"{wad_match.group(1).strip()} PLN" if wad_match else "Brak wymogu"

    # 4. Dynamic Competitors & Tags
    competitors: List[Dict[str, str]] = []
    system_tags: List[str] = []
    if "ewmapa" in low or "geobid" in low:
        competitors.append({
            "name": "Geobid Sp. z o.o.",
            "product": "EWMAPA / OŚRODEK",
            "advantage": "Wymóg przekazywania operatów w zamkniętym formacie natywnym .str",
        })
        system_tags.append("Geobid: EWMAPA (.str)")
    if "impa" in low or "geo-system" in low:
        competitors.append({
            "name": "Geo-System Sp. z o.o.",
            "product": "iMPA / e-Gmina",
            "advantage": "Wymagana bezpośrednia integracja z portalem mapowym gminy",
        })
        system_tags.append("Geo-System: iMPA")
    if "geo-info" in low or "systherm" in low:
        competitors.append({
            "name": "Systherm-Info Sp. z o.o.",
            "product": "GEO-INFO V (.giv)",
            "advantage": "Wymagana dwukierunkowa replikacja z bazą powiatową GEO-INFO",
        })
        competitors.append({
            "name": "Integratorzy OGC / GML",
            "product": "QGIS / PostGIS / GML",
            "advantage": "Dopuszczeni pod warunkiem budowy konektora replikacji na koszt wykonawcy",
        })
        system_tags.extend(["Systherm: GEO-INFO (.giv)", "OGC WMS/WFS"])
    if "ewopis" in low or "turboewid" in low:
        competitors.append({
            "name": "Geomatyka-Kraków s.c.",
            "product": "EWOPIS / TurboEWID",
            "advantage": "System bazowy w starostwie z udostępnionym otwartym interfejsem GML",
        })
        competitors.append({
            "name": "Wykonawcy geodezyjni GML",
            "product": "Standard GML 2021 / GeoTIFF",
            "advantage": "Równy dostęp konkurencyjny dzięki otwartym walidatorom PZGiK",
        })
        system_tags.extend(["Standard GML 2021", "EWOPIS / TurboEWID"])
    if not competitors:
        if "infomedica" in low or "amms" in low:
            competitors.append({
                "name": "Asseco Poland S.A.",
                "product": "InfoMedica / AMMS",
                "advantage": "Autorskie prawa majątkowe do serwisowanego systemu HIS",
            })
            system_tags.append("InfoMedica / AMMS")
        else:
            competitors.append({
                "name": "Integratorzy IT / JST",
                "product": "Systemy dziedzinowe BZP",
                "advantage": "Weryfikacja referencji i certyfikatów inżynierów wdrożeniowych",
            })
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


@st.cache_data(ttl=120, show_spinner=False)
def run_rag_analysis(ocds_id: str, title: str, municipality: str, custom_query: str = "") -> Dict[str, Any]:
    """Executes fast hybrid retrieval and deterministic grounded synthesis for instant UI responsiveness."""
    pipeline = get_retrieval_pipeline()
    active_question = (
        custom_query.strip()
        or "Czy zamawiający narzuca zamknięty format natywny (.str lub .giv) bez dopuszczenia otwartego standardu GML?"
    )
    retrieved_items = pipeline.retrieve(query=active_question, procurement_id=ocds_id, top_k=5)

    retrieved_contexts = [
        item["content"] if isinstance(item, dict) else getattr(item, "content", str(item))
        for item in retrieved_items
    ]
    full_tender_doc = fetch_full_tender_context(ocds_id)
    merged_context = full_tender_doc if full_tender_doc else ("\n\n---\n\n".join(retrieved_contexts) if retrieved_contexts else "Brak dokumentów w bazie.")

    generator = TenderReportGenerator()
    report = asyncio.run(
        generator.generate(
            procurement_id=ocds_id,
            title=title,
            municipality=municipality,
            context=merged_context,
            use_fast_synthesis=True,
        )
    )

    guard = RagasGuard(min_faithfulness=0.95)
    eval_contexts = [merged_context] + retrieved_contexts
    eval_result = guard.evaluate_claims_grounding(report.markdown_report, eval_contexts)
    sections = parse_report_sections(report.raw_llm_output)

    # Answer the user's specific question using both the top retrieved chunks and full tender context
    question_context = ("\n".join(retrieved_contexts[:3]) + "\n" + merged_context).strip()
    direct_answer = generator.answer_specific_question(active_question, question_context)

    top_chunks_meta = []
    for item in retrieved_items[:3]:
        if isinstance(item, dict):
            top_chunks_meta.append({
                "section_title": item.get("section_title") or "Rozdział SWZ",
                "rerank_score": item.get("rerank_score") or item.get("rrf_score") or 0.98,
                "content": item.get("content", ""),
            })

    return {
        "report": report,
        "evaluation": eval_result,
        "contexts": retrieved_contexts,
        "full_text": merged_context,
        "sections": sections,
        "active_question": active_question,
        "direct_answer": direct_answer,
        "top_chunks": top_chunks_meta,
    }


def get_sample_procurements() -> pd.DataFrame:
    """Provides realistic fallback data if DB is empty."""
    return pd.DataFrame([
        {
            "ID": "ocds-148610-niepolomice",
            "Tytuł": "Modernizacja bazy BDOT500, GESUT oraz EGiB dla Miasta i Gminy Niepołomice",
            "Zamawiający": "Urząd Miasta i Gminy w Niepołomicach",
            "Województwo": "Małopolskie",
            "Budżet PLN": 320000.0,
            "Publikacja": "2026-10-15",
            "Termin": "2026-11-20",
            "Status": "ACTIVE",
        },
        {
            "ID": "ocds-148610-kornik",
            "Tytuł": "Wdrożenie Zintegrowanego Systemu Informacji Przestrzennej (SIP) i e-usług MPZP",
            "Zamawiający": "Urząd Miasta i Gminy Kórnik",
            "Województwo": "Wielkopolskie",
            "Budżet PLN": 480000.0,
            "Publikacja": "2026-10-18",
            "Termin": "2026-11-25",
            "Status": "ACTIVE",
        },
    ])


_AUTH_INITIALIZED = False


def ensure_auth_initialized() -> bool:
    """Ensures the PostgreSQL users table and default admin account exist (retries until DB is reachable)."""
    global _AUTH_INITIALIZED
    if _AUTH_INITIALIZED:
        return True
    try:
        AuthService.ensure_schema_and_admin()
        _AUTH_INITIALIZED = True
        return True
    except Exception as exc:
        logger.warning("Could not initialize auth schema in PostgreSQL: %s", exc)
        return False


def _apply_user_table_changes(
    actor: UserRecord,
    existing_workers: List[UserRecord],
    edited_rows: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Applies creates, password/status updates, and deletions from the admin data_editor."""
    existing_by_name = {u.username: u for u in existing_workers}
    kept_names = set()
    stats = {"created": 0, "updated": 0, "deleted": 0}

    for row in edited_rows:
        raw_login = str(row.get("Login") or "").strip()
        raw_pw = str(row.get("Nowe hasło") or "").strip()
        is_active = bool(row.get("Aktywne", True))
        mark_delete = bool(row.get("Usuń", False))

        if not raw_login:
            continue

        if raw_login == actor.username or (raw_login in existing_by_name and existing_by_name[raw_login].role == "admin"):
            raise ValueError(f"Konto administratora '{raw_login}' jest chronione.")

        if raw_login in existing_by_name:
            if mark_delete:
                AuthService.delete_user(actor, raw_login)
                stats["deleted"] += 1
                continue
            kept_names.add(raw_login)
            prev = existing_by_name[raw_login]
            changed = False
            if is_active != prev.is_active:
                AuthService.set_user_active(actor, raw_login, is_active)
                changed = True
            if raw_pw:
                AuthService.update_user_password(actor, raw_login, raw_pw)
                changed = True
            if changed:
                stats["updated"] += 1
        else:
            if mark_delete:
                continue
            if not raw_pw:
                raise ValueError(f"Podaj hasło (min. 6 znaków) dla nowego użytkownika '{raw_login}'.")
            created = AuthService.create_user(actor, username=raw_login, password=raw_pw, role="user")
            if not is_active:
                AuthService.set_user_active(actor, created.username, False)
            kept_names.add(created.username)
            stats["created"] += 1

    # Any existing worker removed via data_editor row trash icon
    for old_name in existing_by_name:
        if old_name not in kept_names and not any(
            str(r.get("Login") or "").strip() == old_name and bool(r.get("Usuń", False))
            for r in edited_rows
        ):
            AuthService.delete_user(actor, old_name)
            stats["deleted"] += 1

    return stats


def render_login_view() -> None:
    """Renders the login-only screen (no self-registration, hidden sidebar)."""
    st.markdown("<style>[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1.0, 1.2, 1.0])
    with center_col:
        st.markdown("<div style='height:48px;'></div>", unsafe_allow_html=True)
        st.markdown(render_brand_sidebar_header(), unsafe_allow_html=True)
        st.markdown(
            "<h3 style='margin-top:8px;margin-bottom:4px;color:#0f172a;'>Logowanie do systemu</h3>"
            "<p style='color:#475569;font-size:0.88rem;margin-bottom:16px;'>"
            "Dostęp wyłącznie dla uprawnionych pracowników. Konta zakłada administrator.</p>",
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Login", placeholder="Wpisz login użytkownika")
            password = st.text_input("Hasło", type="password", placeholder="Wpisz hasło")
            submitted = st.form_submit_button("Zaloguj się", type="primary", use_container_width=True)
            if submitted:
                try:
                    ensure_auth_initialized()
                    user = AuthService.authenticate(username=username, password=password)
                except Exception as exc:
                    st.error(f"Błąd połączenia z bazą PostgreSQL: {exc}")
                    return
                if user is None:
                    st.error("Nieprawidłowy login, hasło lub konto jest nieaktywne.")
                else:
                    token = create_session_token(user)
                    st.session_state["auth_user"] = user
                    st.session_state["auth_token"] = token
                    st.session_state["ui_page"] = "Pulpit"
                    st.query_params.clear()
                    st.query_params["session"] = token
                    st.rerun()


def render_settings_view(user: UserRecord) -> None:
    """Renders clean account settings for workers and user management for the sole admin."""
    if user.role != "admin":
        safe_user = html.escape(user.username)
        st.markdown(
            _compact_html(f"""
            <div class="glass-layer-2" style="padding:18px 22px;margin-bottom:16px;">
                <div style="font-size:1.05rem;font-weight:700;color:#0f172a;margin-bottom:6px;">Profil użytkownika</div>
                <div style="display:flex;flex-wrap:wrap;gap:24px;font-size:0.86rem;color:#334155;">
                    <div>Login: <strong>{safe_user}</strong></div>
                    <div>Rola: <strong>Pracownik</strong></div>
                    <div>Status: <strong style="color:#059669;">{'Aktywne' if user.is_active else 'Nieaktywne'}</strong></div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
        st.info("Zarządzanie kontami pracowników jest dostępne wyłącznie dla administratora systemu.")
        return

    try:
        all_users = AuthService.list_users(user)
    except Exception as exc:
        st.error(f"Nie udało się pobrać listy użytkowników: {exc}")
        return

    workers = [u for u in all_users if u.role != "admin"]

    st.markdown("### Zarządzanie kontami pracowników")

    pending_delete = st.session_state.get("confirm_delete_user")
    if pending_delete:
        st.warning(f"Czy na pewno chcesz trwale usunąć konto pracownika **{pending_delete}**?")
        c_yes, c_no, _ = st.columns([1.0, 1.0, 3.0])
        with c_yes:
            if st.button("Tak, usuń", key="confirm_delete_yes", type="primary", use_container_width=True):
                try:
                    AuthService.delete_user(user, pending_delete)
                    st.session_state.pop("confirm_delete_user", None)
                    st.success(f"Usunięto konto `{pending_delete}`.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Nie udało się usunąć konta: {exc}")
        with c_no:
            if st.button("Anuluj", key="confirm_delete_no", type="secondary", use_container_width=True):
                st.session_state.pop("confirm_delete_user", None)
                st.rerun()

    with st.container(border=True):
        h1, h2, h3 = st.columns([1.8, 2.3, 1.14], vertical_alignment="center")
        h1.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748b;letter-spacing:0.03em;'>LOGIN</div>", unsafe_allow_html=True)
        h2.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748b;letter-spacing:0.03em;'>HASŁO</div>", unsafe_allow_html=True)
        h3.markdown("<div style='font-size:0.75rem;font-weight:700;color:#64748b;letter-spacing:0.03em;text-align:center;'>AKCJE</div>", unsafe_allow_html=True)

        for w in workers:
            c1, c2, c_save, c_toggle, c_del = st.columns([1.8, 2.3, 0.38, 0.38, 0.38], vertical_alignment="center")
            with c1:
                st.markdown(
                    f"<div style='height:48px;display:flex;align-items:center;padding:0 12px;background:#f8fafc;"
                    f"border:1px solid #e2e8f0;border-radius:10px;font-weight:700;color:#0f172a;font-size:0.88rem;'>"
                    f"{html.escape(w.username)}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                row_pw = st.text_input(
                    f"Hasło {w.username}",
                    key=f"pw_edit_{w.username}",
                    type="password",
                    label_visibility="collapsed",
                    placeholder="Wpisz nowe hasło, aby zmienić",
                )
            with c_save:
                if st.button(
                    "💾",
                    key=f"save_pw_{w.username}",
                    type="secondary",
                    use_container_width=True,
                    help=f"Zapisz nowe hasło dla {w.username}",
                ):
                    try:
                        AuthService.update_user_password(user, w.username, row_pw.strip())
                        st.success(f"Zapisano nowe hasło dla `{w.username}`.")
                    except Exception as exc:
                        st.error(f"Błąd: {exc}")
            with c_toggle:
                toggle_icon = "✓" if w.is_active else "🔒"
                toggle_type = "primary" if w.is_active else "secondary"
                toggle_help = "Konto aktywne — kliknij, aby zablokować" if w.is_active else "Konto zablokowane — kliknij, aby aktywować"
                if st.button(
                    toggle_icon,
                    key=f"toggle_btn_{w.username}",
                    type=toggle_type,
                    use_container_width=True,
                    help=toggle_help,
                ):
                    try:
                        AuthService.set_user_active(user, w.username, not w.is_active)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Błąd zmiany statusu: {exc}")
            with c_del:
                if st.button(
                    "🗑",
                    key=f"delete_btn_{w.username}",
                    type="secondary",
                    use_container_width=True,
                    help=f"Usuń konto {w.username}",
                ):
                    st.session_state["confirm_delete_user"] = w.username
                    st.rerun()

        # Inline new-worker row inside the exact same card
        st.markdown("<hr style='margin:10px 0;border:none;border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
        if st.session_state.pop("_pending_clear_new_worker", False):
            st.session_state["inline_new_worker_login"] = ""
            st.session_state["inline_new_worker_pw"] = ""
        n1, n2, n_add, _ = st.columns([1.8, 2.3, 0.38, 0.76], vertical_alignment="center")
        with n1:
            new_login = st.text_input(
                "Nowy login",
                key="inline_new_worker_login",
                label_visibility="collapsed",
                placeholder="Nowy login pracownika",
            )
        with n2:
            new_pw = st.text_input(
                "Nowe hasło",
                key="inline_new_worker_pw",
                type="password",
                label_visibility="collapsed",
                placeholder="Hasło (min. 6 znaków)",
            )
        with n_add:
            if st.button("＋", key="inline_add_worker_btn", type="primary", use_container_width=True, help="Dodaj nowego pracownika"):
                try:
                    created = AuthService.create_user(user, username=new_login, password=new_pw, role="user")
                    st.session_state["_pending_clear_new_worker"] = True
                    st.success(f"Dodano pracownika `{created.username}`.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Błąd: {exc}")


def render_tender_list_view(df: pd.DataFrame, session_token: str) -> None:
    """Renders filters above the clickable table-first procurement list (no checkboxes)."""
    f1, f2, f3 = st.columns([1.6, 1.0, 1.0])
    with f1:
        st.text_input(
            "Szukaj (zamawiający, tytuł lub ID)",
            key="list_search_text",
        )
    with f2:
        voivodeships = ["Wszystkie"] + sorted(df["Województwo"].dropna().unique().tolist())
        st.selectbox("Województwo", voivodeships, key="list_filter_voiv")
    with f3:
        st.number_input("Minimalny budżet (PLN)", min_value=0, step=50000, key="list_filter_budget")

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    search_text = st.session_state.get("list_search_text", "").strip().lower()
    selected_voiv = st.session_state.get("list_filter_voiv", "Wszystkie")
    min_budget = int(st.session_state.get("list_filter_budget", 0) or 0)

    filtered_df = df.copy()
    if selected_voiv != "Wszystkie":
        filtered_df = filtered_df[filtered_df["Województwo"] == selected_voiv]
    if min_budget > 0:
        filtered_df = filtered_df[filtered_df["Budżet PLN"] >= min_budget]
    if search_text:
        mask = (
            filtered_df["Zamawiający"].astype(str).str.lower().str.contains(search_text, na=False)
            | filtered_df["Tytuł"].astype(str).str.lower().str.contains(search_text, na=False)
            | filtered_df["ID"].astype(str).str.lower().str.contains(search_text, na=False)
        )
        filtered_df = filtered_df[mask]

    if filtered_df.empty:
        st.warning("Brak postępowań spełniających wybrane kryteria filtrowania.")
    else:
        table_records = filtered_df.to_dict(orient="records")
        st.markdown(
            render_clickable_procurements_table(rows=table_records, session_token=session_token),
            unsafe_allow_html=True,
        )


def render_tender_detail_view(selected_row: pd.Series, total_tenders: int, session_token: str) -> None:
    """Renders full audit KPIs, report sections, and side-by-side question composer for one tender."""
    selected_id = str(selected_row["ID"])

    back_col, title_col = st.columns([0.42, 4.58], vertical_alignment="center")
    with back_col:
        if st.button("←", key="back_to_list_btn", type="secondary", help="Wróć do listy przetargów"):
            st.session_state.pop("selected_ocds_id", None)
            st.query_params.clear()
            if session_token:
                st.query_params["session"] = session_token
            st.rerun()
    with title_col:
        st.markdown(
            f"<div style='font-size:1.05rem;font-weight:800;color:#0f172a;line-height:1.3;'>"
            f"{html.escape(str(selected_row['Zamawiający']))} — {html.escape(str(selected_row['Tytuł']))}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # 1. Instant Stats & Baseline Analysis (with visible progress indicator on load)
    load_slot = st.empty()
    with load_slot.container():
        prog = st.progress(20, text="Wyszukiwanie fragmentów SWZ w bazie wektorowej...")
        with st.spinner("Obliczanie wskaźników KIO i weryfikacja RAGAS..."):
            baseline = run_rag_analysis(
                ocds_id=selected_id,
                title=str(selected_row["Tytuł"]),
                municipality=str(selected_row["Zamawiający"]),
                custom_query="",
            )
            prog.progress(100, text="Gotowe!")
    load_slot.empty()

    report = baseline["report"]
    eval_res = baseline["evaluation"]
    sections = baseline["sections"]
    full_text = baseline.get("full_text", report.markdown_report)

    sel_budget = float(selected_row["Budżet PLN"]) if pd.notna(selected_row["Budżet PLN"]) else 0.0
    metrics = extract_tender_metrics(full_text=full_text, budget_pln=sel_budget)

    # Row 1: 4 Architectural KPI Cards (always visible immediately)
    budget_short = f"{sel_budget:,.0f} PLN".replace(",", " ") if sel_budget > 0 else "Wg SWZ"
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            render_kpi_stat_card(
                value=metrics["kio_label"],
                label="Ryzyko odwołania KIO",
                sublabel=metrics["kio_sub"],
                icon_name="shield-alert",
                color_hex=metrics["kio_color"],
                ring_bg="#fef2f2" if metrics["kio_level"] == "HIGH" else ("#fffbeb" if metrics["kio_level"] == "MEDIUM" else "#ecfdf5"),
                stagger_index=0,
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            render_kpi_stat_card(
                value=budget_short,
                label="Szacowana wartość netto",
                sublabel=f"Wadium: {metrics['wadium_str']}",
                icon_name="wallet",
                color_hex="#0f172a",
                ring_bg="#f8fafc",
                stagger_index=1,
            ),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            render_kpi_stat_card(
                value=metrics["penalty_rate"],
                label="Kary umowne za zwłokę",
                sublabel=metrics["penalty_sub"],
                icon_name="scale",
                color_hex="#d97706" if metrics["has_penalties"] else "#0f172a",
                ring_bg="#fffbeb" if metrics["has_penalties"] else "#f8fafc",
                stagger_index=2,
            ),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            render_kpi_stat_card(
                value=f"{eval_res.faithfulness * 100:.0f}%",
                label="Wierność odpowiedzi RAGAS",
                sublabel=f"Faithfulness: {eval_res.faithfulness:.2f} (próg ≥ 0.95)",
                icon_name="check-circle",
                color_hex="#059669",
                ring_bg="#ecfdf5",
                stagger_index=3,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    st.markdown(render_kio_warning(metrics["kio_level"]), unsafe_allow_html=True)

    # Organized collapsible full audit (keeps viewport focused on stats + continuous chat)
    with st.expander("Szczegółowy audyt SWZ, profil ryzyka i macierz konkurencji", expanded=False):
        main_left, main_right = st.columns([2.25, 1.0])
        with main_left:
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                st.markdown(
                    render_insight_section_card(
                        title="1. Zakres, budżet i termin realizacji",
                        body=sections.get("summary", ""),
                        icon_name="layers",
                    ),
                    unsafe_allow_html=True,
                )
            with r1c2:
                st.markdown(
                    render_insight_section_card(
                        title="2. Wymagania formatów i ocena barier PZP",
                        body=sections.get("legal_barriers", ""),
                        icon_name="shield-alert",
                    ),
                    unsafe_allow_html=True,
                )

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                st.markdown(
                    render_insight_section_card(
                        title="3. Kadra, wadium, kryteria i kary umowne",
                        body=sections.get("recommendations", ""),
                        icon_name="scale",
                    ),
                    unsafe_allow_html=True,
                )
            with r2c2:
                st.markdown(
                    render_insight_section_card(
                        title="4. Wymagane systemy dziedzinowe i integracja",
                        body=sections.get("competitors", ""),
                        icon_name="radar",
                    ),
                    unsafe_allow_html=True,
                )

        with main_right:
            st.markdown(
                render_risk_profile_panel(
                    has_lockin=metrics["has_lockin"],
                    has_penalties=metrics["has_penalties"],
                    faithfulness=eval_res.faithfulness,
                    format_score=metrics["format_score"],
                    penalty_score=metrics["penalty_score"],
                    personnel_score=metrics["personnel_score"],
                    system_tags=metrics["system_tags"],
                ),
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown(render_competitor_matrix(metrics["competitors"]), unsafe_allow_html=True)
            st.download_button(
                label="Pobierz pełny raport audytu (.pdf)",
                data=export_report_to_pdf_bytes(report.markdown_report),
                file_name=f"raport_{selected_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    # 2. Continuous Conversation History for this tender
    history_key = f"chat_history_{selected_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
    history: List[Dict[str, Any]] = st.session_state[history_key]

    chat_hdr_l, chat_hdr_r = st.columns([4.2, 0.8], vertical_alignment="center")
    with chat_hdr_l:
        st.markdown("#### Rozmowa z dokumentacją SWZ")
    with chat_hdr_r:
        if history and st.button("Wyczyść", key="clear_chat_history_btn", type="secondary", use_container_width=True):
            st.session_state[history_key] = []
            st.rerun()

    if not history:
        st.markdown(
            "<div style='background:#ffffff;border:1px dashed #cbd5e1;border-radius:12px;padding:18px 20px;"
            "color:#475569;font-size:0.88rem;margin-bottom:14px;'>"
            "Zadaj pytanie w oknie czatu poniżej lub wybierz gotowy szablon, aby rozpocząć analizę konwersacyjną tego przetargu."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        for turn in history:
            st.markdown(
                render_direct_answer_card(
                    question=turn["question"],
                    answer=turn["answer"],
                    top_chunks=turn.get("chunks", []),
                ),
                unsafe_allow_html=True,
            )

    chat_loading_slot = st.empty()

    # 3. Sticky Bottom Continuous Chat Composer (always pinned at the bottom)
    if st.session_state.pop("_pending_clear_chat", False):
        st.session_state["rag_question_input"] = ""
    pending_tpl = st.session_state.pop("_pending_chat_template", None)
    if pending_tpl is not None:
        st.session_state["rag_question_input"] = pending_tpl
    if "rag_question_input" not in st.session_state:
        st.session_state["rag_question_input"] = ""

    with st.container(border=True):
        st.markdown("<div class='sticky-chat-marker' style='display:none;'></div>", unsafe_allow_html=True)
        user_question = st.text_area(
            "Pytanie do dokumentacji",
            key="rag_question_input",
            height=74,
            label_visibility="collapsed",
            placeholder="Wpisz pytanie do dokumentacji SWZ/OPZ...",
        )

        c_tpl, c_model, c_fmt, c_spacer, c_send = st.columns(
            [1.05, 1.35, 1.45, 2.2, 0.45],
            vertical_alignment="center",
        )
        with c_tpl:
            with st.popover("Szablony", use_container_width=True):
                st.caption("Wybierz gotowe pytanie eksperckie:")
                for idx, (tpl_label, tpl_text) in enumerate(RAG_QUESTION_TEMPLATES.items()):
                    if not tpl_text:
                        continue
                    if st.button(tpl_label, key=f"tpl_pick_{idx}", type="secondary", use_container_width=True):
                        st.session_state["_pending_chat_template"] = tpl_text
                        st.rerun()

        with c_model:
            cpu_svg = get_svg_icon("cpu", size=16, color="#475569")
            safe_model = html.escape(settings.OLLAMA_MODEL)
            st.markdown(
                _compact_html(f"""
                <div class="chat-model-pill" title="Model lokalny Ollama (stały)" style="display:flex;align-items:center;justify-content:center;gap:6px;height:38px;padding:0 12px;border-radius:9px;background:#f8fafc;border:1px solid #e2e8f0;color:#334155;font-size:0.8rem;font-weight:600;white-space:nowrap;">
                    {cpu_svg}
                    <span>Ollama · {safe_model}</span>
                </div>
                """),
                unsafe_allow_html=True,
            )

        with c_fmt:
            selected_format = st.selectbox(
                "Format odpowiedzi",
                ["Standard (SWZ)", "Zwięzły (Punkty)", "Audyt PZP / KIO"],
                key="chat_response_format",
                label_visibility="collapsed",
            )

        with c_send:
            send_clicked = st.button("↑", key="chat_send_btn", type="primary", help="Wyślij pytanie")

        if send_clicked and user_question.strip():
            q_clean = user_question.strip()
            with chat_loading_slot.container():
                chat_prog = st.progress(30, text="Przeszukiwanie SWZ/OPZ (BGE-M3 + Reranker)...")
                with st.spinner("Generowanie odpowiedzi i weryfikacja RAGAS..."):
                    q_res = run_rag_analysis(
                        ocds_id=selected_id,
                        title=str(selected_row["Tytuł"]),
                        municipality=str(selected_row["Zamawiający"]),
                        custom_query=q_clean,
                    )
                    chat_prog.progress(100, text="Odpowiedź gotowa!")
            chat_loading_slot.empty()
            direct_ans = q_res.get("direct_answer", "")
            if selected_format == "Zwięzły (Punkty)" and direct_ans:
                parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", direct_ans) if p.strip()]
                if len(parts) > 1:
                    direct_ans = " • ".join(parts)
            elif selected_format == "Audyt PZP / KIO" and direct_ans:
                direct_ans = f"[Tryb audytu PZP/KIO] {direct_ans}"

            st.session_state[history_key].append(
                {
                    "question": q_clean,
                    "answer": direct_ans,
                    "chunks": q_res.get("top_chunks", []),
                }
            )
            st.session_state["_pending_clear_chat"] = True
            st.rerun()


def render_about_view(total_tenders: int) -> None:
    """Renders technical stack, model info, and live engine status in 'O programie'."""
    ollama_ok = check_ollama_health()
    status_label = "Aktywny (Online)" if ollama_ok else "Tryb deterministyczny (Offline)"
    status_color = "#059669" if ollama_ok else "#d97706"

    st.markdown("## O programie")
    st.markdown(
        _compact_html(f"""
        <div class="glass-layer-2" style="padding:20px 24px;margin-bottom:16px;">
            <div style="font-size:1.05rem;font-weight:800;color:#0f172a;margin-bottom:8px;">
                GisMarket Intelligence AI
            </div>
            <p style="font-size:0.9rem;color:#334155;margin:0 0 14px 0;">
                Lokalny system RAG do audytu specyfikacji warunków zamówienia (SWZ/OPZ) w polskich przetargach geodezyjnych i GIS.
            </p>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;font-size:0.84rem;color:#334155;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <div style="color:#64748b;font-size:0.74rem;font-weight:700;text-transform:uppercase;">Silnik wektorowy</div>
                    <div style="color:#0f172a;font-weight:700;margin-top:4px;">BGE-M3 + pgvector (HNSW)</div>
                </div>
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <div style="color:#64748b;font-size:0.74rem;font-weight:700;text-transform:uppercase;">Reranker i Quality Gate</div>
                    <div style="color:#0f172a;font-weight:700;margin-top:4px;">bge-reranker-v2-m3 · RAGAS ≥ 0.95</div>
                </div>
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <div style="color:#64748b;font-size:0.74rem;font-weight:700;text-transform:uppercase;">Model LLM (Ollama)</div>
                    <div style="color:{status_color};font-weight:700;margin-top:4px;">{html.escape(settings.OLLAMA_MODEL)} · {status_label}</div>
                </div>
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;">
                    <div style="color:#64748b;font-size:0.74rem;font-weight:700;text-transform:uppercase;">Baza postępowań</div>
                    <div style="color:#0f172a;font-weight:700;margin-top:4px;">{total_tenders} SWZ w PostgreSQL</div>
                </div>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def main() -> None:
    st.markdown(get_glassmorphism_stylesheet(), unsafe_allow_html=True)
    ensure_auth_initialized()

    # Restore session from signed query param across F5 refreshes
    current_user: Optional[UserRecord] = st.session_state.get("auth_user")
    if current_user is None:
        qp_token = st.query_params.get("session")
        if qp_token:
            restored = verify_session_token(str(qp_token))
            if restored is not None:
                st.session_state["auth_user"] = restored
                st.session_state["auth_token"] = str(qp_token)
                current_user = restored

    if current_user is None:
        render_login_view()
        return

    session_token = st.session_state.get("auth_token") or create_session_token(current_user)
    st.session_state["auth_token"] = session_token
    if st.query_params.get("session") != session_token:
        st.query_params["session"] = session_token

    # Sync navigation state from query params (clickable logo / clickable table rows)
    qp_page = st.query_params.get("page")
    qp_tender = st.query_params.get("tender")
    if qp_page == "settings":
        st.session_state["ui_page"] = "Ustawienia"
        st.session_state.pop("selected_ocds_id", None)
    elif qp_page == "about":
        st.session_state["ui_page"] = "O programie"
        st.session_state.pop("selected_ocds_id", None)
    elif qp_tender:
        st.session_state["ui_page"] = "Pulpit"
        st.session_state["selected_ocds_id"] = str(qp_tender)
    elif "ui_page" not in st.session_state:
        st.session_state["ui_page"] = "Pulpit"

    active_page = st.session_state.get("ui_page", "Pulpit")
    home_href = f"?session={quote(session_token, safe='')}"
    safe_user = html.escape(current_user.username)
    role_label = "Administrator" if current_user.role == "admin" else "Pracownik"

    # Compact Left Sidebar: Clickable Logo (home) + User Card + Ustawienia + Wyloguj się
    with st.sidebar:
        st.markdown(render_brand_sidebar_header(href=home_href), unsafe_allow_html=True)
        st.markdown(
            _compact_html(f"""
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="width:8px;height:8px;border-radius:999px;background:#059669;display:inline-block;flex-shrink:0;"></span>
                    <span style="font-size:0.84rem;font-weight:700;color:#0f172a;overflow:hidden;text-overflow:ellipsis;">{safe_user}</span>
                </div>
                <div style="font-size:0.72rem;font-weight:600;color:#2563eb;background:#eff6ff;display:inline-block;padding:2px 8px;border-radius:999px;">
                    {role_label}
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

        if st.button(
            "Główna",
            key="sidebar_home_btn",
            type="primary" if active_page == "Pulpit" else "secondary",
            use_container_width=True,
        ):
            st.session_state["ui_page"] = "Pulpit"
            st.session_state.pop("selected_ocds_id", None)
            st.query_params.clear()
            st.query_params["session"] = session_token
            st.rerun()

        if st.button(
            "Ustawienia",
            key="sidebar_settings_btn",
            type="primary" if active_page == "Ustawienia" else "secondary",
            use_container_width=True,
        ):
            st.session_state["ui_page"] = "Ustawienia"
            st.session_state.pop("selected_ocds_id", None)
            st.query_params.clear()
            st.query_params["session"] = session_token
            st.query_params["page"] = "settings"
            st.rerun()

        if st.button(
            "O programie",
            key="sidebar_about_btn",
            type="primary" if active_page == "O programie" else "secondary",
            use_container_width=True,
        ):
            st.session_state["ui_page"] = "O programie"
            st.session_state.pop("selected_ocds_id", None)
            st.query_params.clear()
            st.query_params["session"] = session_token
            st.query_params["page"] = "about"
            st.rerun()

        if st.button("Wyloguj się", key="sidebar_logout_btn", type="secondary", use_container_width=True):
            st.session_state.pop("auth_user", None)
            st.session_state.pop("auth_token", None)
            st.session_state.pop("ui_page", None)
            st.session_state.pop("selected_ocds_id", None)
            st.query_params.clear()
            st.rerun()

    if active_page == "Ustawienia":
        render_settings_view(current_user)
        return

    df = fetch_procurements_from_db()
    if df.empty:
        df = get_sample_procurements()

    if active_page == "O programie":
        render_about_view(total_tenders=len(df))
        return

    selected_ocds_id = st.session_state.get("selected_ocds_id")
    if selected_ocds_id:
        matching = df[df["ID"].astype(str) == str(selected_ocds_id)]
        if not matching.empty:
            render_tender_detail_view(matching.iloc[0], total_tenders=len(df), session_token=session_token)
            return
        st.session_state.pop("selected_ocds_id", None)

    render_tender_list_view(df, session_token=session_token)


if __name__ == "__main__":
    main()
