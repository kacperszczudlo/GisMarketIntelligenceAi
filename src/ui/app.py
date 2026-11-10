import asyncio
import logging
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

# Ensure project root is on sys.path when invoked via `streamlit run src/ui/app.py`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib
import pandas as pd
import streamlit as st
from src.database.connection import DatabaseManager
from src.evaluation.ragas_guard import RagasGuard
from src.inference.ollama_client import OllamaClient
import src.inference.report_generator as _rg_mod
import src.ui.components as _ui_mod

importlib.reload(_rg_mod)
importlib.reload(_ui_mod)

from src.inference.report_generator import TenderReportGenerator
from src.ingestion.client import NUTS_PROVINCE_MAP
from src.retrieval.pipeline import RetrievalPipeline
from src.ui.components import (
    _compact_html,
    get_glassmorphism_stylesheet,
    get_svg_icon,
    render_brand_sidebar_header,
    render_citation_box,
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
        db = DatabaseManager()
        with db.get_cursor() as cur:
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
        db = DatabaseManager()
        with db.get_cursor() as cur:
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
    if ".str" in low and "bez udostępnienia" in low or "bez udostepnienia" in low:
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


def main() -> None:
    st.markdown(get_glassmorphism_stylesheet(), unsafe_allow_html=True)

    df = fetch_procurements_from_db()
    if df.empty:
        df = get_sample_procurements()

    # Left Sidebar: Brand Logo at Top-Left + Region/Budget Filters
    with st.sidebar:
        st.markdown(render_brand_sidebar_header(), unsafe_allow_html=True)

        sliders_svg = get_svg_icon("sliders", size=16, color="#0f172a")
        st.markdown(
            _compact_html(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;color:#0f172a;font-weight:700;font-size:0.84rem;">
                {sliders_svg}
                <span>Filtrowanie bazy postępowań</span>
            </div>
            """),
            unsafe_allow_html=True,
        )

        voivodeships = ["Wszystkie"] + sorted(df["Województwo"].dropna().unique().tolist())
        selected_voiv = st.selectbox("Województwo", voivodeships)
        min_budget = st.number_input("Minimalny budżet (PLN)", min_value=0, value=0, step=50000)

        filtered_df = df.copy()
        if selected_voiv != "Wszystkie":
            filtered_df = filtered_df[filtered_df["Województwo"] == selected_voiv]
        if min_budget > 0:
            filtered_df = filtered_df[filtered_df["Budżet PLN"] >= min_budget]
        if filtered_df.empty:
            filtered_df = df.copy()

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        db_svg = get_svg_icon("database", size=16, color="#475569")
        st.markdown(
            _compact_html(f"""
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;font-size:0.78rem;color:#334155;line-height:1.5;">
                <div style="display:flex;align-items:center;gap:8px;font-weight:700;color:#0f172a;margin-bottom:6px;">
                    {db_svg}
                    <span>Zindeksowany korpus SWZ</span>
                </div>
                <div>Aktywnych postępowań: <strong>{len(filtered_df)}</strong></div>
                <div>Model wektorowy: <strong>BAAI/bge-m3</strong></div>
                <div>Reranker: <strong>Cross-Encoder v2</strong></div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    # Prominent Top Control Bar in Main Area (Full-width readable dropdowns + aligned search input)
    options_map: Dict[str, pd.Series] = {}
    option_labels = []
    for _, row in filtered_df.iterrows():
        b_val = float(row["Budżet PLN"]) if pd.notna(row["Budżet PLN"]) else 0.0
        b_str = f"{b_val:,.0f} PLN".replace(",", " ") if b_val > 0 else "Wg SWZ"
        label = f"{row['Zamawiający']} — {row['Tytuł']} ({b_str})"
        options_map[label] = row
        option_labels.append(label)

    ctrl_col1, ctrl_col2 = st.columns([1.25, 1.0])
    with ctrl_col1:
        selected_label = st.selectbox(
            "Wybierz postępowanie przetargowe do audytu SWZ/OPZ",
            option_labels,
            index=0,
        )
    with ctrl_col2:
        template_names = list(RAG_QUESTION_TEMPLATES.keys())
        selected_template_name = st.selectbox(
            "Wybierz gotowy szablon pytania eksperckiego (lub wpisz własne poniżej)",
            template_names,
            index=0,
        )

    selected_row = options_map[selected_label]
    selected_id = str(selected_row["ID"])

    # Sync text input when template dropdown changes
    template_default_text = RAG_QUESTION_TEMPLATES[selected_template_name]
    if st.session_state.get("prev_template_name") != selected_template_name:
        st.session_state["prev_template_name"] = selected_template_name
        if template_default_text:
            st.session_state["rag_question_input"] = template_default_text

    if "rag_question_input" not in st.session_state:
        st.session_state["rag_question_input"] = RAG_QUESTION_TEMPLATES[template_names[0]]

    # Pixel-aligned Question Input + Action Button on the exact same horizontal line
    q_col, btn_col = st.columns([4.2, 1.0], vertical_alignment="bottom")
    with q_col:
        user_question = st.text_input(
            "Treść pytania analitycznego do dokumentacji SWZ/OPZ (możesz edytować szablon lub wpisać własne pytanie)",
            key="rag_question_input",
            placeholder="Np. Ile wynosi wadium, jakie są wagi kryteriów oceny ofert lub czy dopuszczony jest format GML?",
        )
    with btn_col:
        st.button("Zadaj pytanie", use_container_width=True)

    # Execute cached/fast RAG analysis BEFORE rendering KPIs and cards so every change reflects immediately
    result = run_rag_analysis(
        ocds_id=selected_id,
        title=str(selected_row["Tytuł"]),
        municipality=str(selected_row["Zamawiający"]),
        custom_query=user_question,
    )

    report = result["report"]
    eval_res = result["evaluation"]
    sections = result["sections"]
    full_text = result.get("full_text", report.markdown_report)
    ollama_ok = check_ollama_health()

    sel_budget = float(selected_row["Budżet PLN"]) if pd.notna(selected_row["Budżet PLN"]) else 0.0
    metrics = extract_tender_metrics(full_text=full_text, budget_pln=sel_budget)

    # 1. Top Breadcrumb & Status Bar
    st.markdown(
        render_top_utility_bar(
            municipality=str(selected_row["Zamawiający"]),
            voivodeship=str(selected_row["Województwo"]),
            ollama_ok=ollama_ok,
            total_tenders=len(filtered_df),
            has_lockin=metrics["has_lockin"],
        ),
        unsafe_allow_html=True,
    )

    # 2. Row 1: 4 Restrained Architectural KPI Cards (Dynamic per tender)
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

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # 3. Row 2: Main Analytical Split (Left Executive Audit + Right Risk Profile & Competitors)
    main_left, main_right = st.columns([2.25, 1.0])

    with main_left:
        # Direct Answer Card (updates immediately for every template or custom question!)
        st.markdown(
            render_direct_answer_card(
                question=result.get("active_question", user_question),
                answer=result.get("direct_answer", ""),
                top_chunks=result.get("top_chunks", []),
            ),
            unsafe_allow_html=True,
        )

        # Warning banner
        st.markdown(render_kio_warning(metrics["kio_level"]), unsafe_allow_html=True)

        # 2x2 Structured Audit Grid (Clean prose + dedicated source footers)
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
            label="Pobierz pełny raport audytu (.md)",
            data=report.markdown_report,
            file_name=f"raport_{selected_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # 4. Row 3: Full-Width Clean Procurements Table Card
    table_records = filtered_df.to_dict(orient="records")
    st.markdown(
        render_procurements_table(rows=table_records, selected_id=selected_id),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
