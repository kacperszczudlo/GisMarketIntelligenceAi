import asyncio
import html
import logging
from pathlib import Path
import re
import sys
from typing import Any, Dict

# Ensure project root is on sys.path when invoked via `streamlit run src/ui/app.py`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
from src.database.connection import DatabaseManager
from src.evaluation.ragas_guard import RagasGuard
from src.inference.ollama_client import OllamaClient
from src.inference.report_generator import TenderReportGenerator
from src.ingestion.client import NUTS_PROVINCE_MAP
from src.retrieval.pipeline import RetrievalPipeline
from src.ui.components import (
    _compact_html,
    get_glassmorphism_stylesheet,
    get_svg_icon,
    render_citation_box,
    render_competitor_matrix,
    render_insight_section_card,
    render_kio_warning,
    render_red_flag_badge,
    render_tender_card,
)

logger = logging.getLogger("src.ui.app")

st.set_page_config(
    page_title="GisMarketIntelligenceAi | Audyt zamówień GIS",
    layout="wide",
    initial_sidebar_state="expanded",
)

AUDIT_PRESETS: Dict[str, str] = {
    "Pełny audyt barier SWZ i ryzyka KIO": (
        "Bariery rynkowe, wymóg formatu .str, oprogramowanie EWMAPA, kary umowne oraz podstawy odwołania do KIO"
    ),
    "Weryfikacja blokad formatu (.str / EWMAPA / GML)": (
        "Wymagania techniczne, formaty wymiany danych .str, GML, EWMAPA, integracja z bazą OŚRODEK i portalem iMPA"
    ),
    "Analiza kar umownych i wymogów kadrowych": (
        "Warunki udziału w postępowaniu, uprawnienia geodezyjne zakresu 1 i 2, kary umowne za zwłokę"
    ),
    "Własne pytanie do dokumentacji SWZ": "",
}


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
                ORDER BY estimated_budget_pln DESC, date_published DESC
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


def check_ollama_health() -> bool:
    """Checks if Ollama daemon is reachable."""
    try:
        client = OllamaClient()
        return asyncio.run(client.check_health())
    except Exception:
        return False


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


def run_rag_analysis(ocds_id: str, title: str, municipality: str, custom_query: str = "") -> Dict[str, Any]:
    """Executes the complete retrieval and report generation pipeline."""
    pipeline = get_retrieval_pipeline()
    query = custom_query.strip() or f"Bariery rynkowe, wymóg formatu .str, oprogramowanie EWMAPA, kary umowne: {title}"
    retrieved_items = pipeline.retrieve(query=query, procurement_id=ocds_id, top_k=5)

    contexts = [
        item["content"] if isinstance(item, dict) else getattr(item, "content", str(item))
        for item in retrieved_items
    ]
    merged_context = "\n\n---\n\n".join(contexts) if contexts else "Brak dokumentów w bazie."

    generator = TenderReportGenerator()
    report = asyncio.run(
        generator.generate(
            procurement_id=ocds_id,
            title=title,
            municipality=municipality,
            context=merged_context,
        )
    )

    guard = RagasGuard(min_faithfulness=0.95)
    eval_result = guard.evaluate_claims_grounding(report.markdown_report, contexts)

    # Ensure clean structured sections if LLM output missed markdown headings or failed quality gate
    sections = parse_report_sections(report.raw_llm_output)
    if not eval_result.passed or not sections["summary"] or "------" in report.raw_llm_output:
        strict_body = generator._build_grounded_synthesis(merged_context, municipality)
        report.raw_llm_output = strict_body
        report.executive_summary = generator._extract_section(strict_body, "### 1. Podsumowanie") or strict_body[:300]
        report.citations = generator._extract_citations(strict_body)
        report.markdown_report = (
            f"# Raport przetargowy: {ocds_id}\n"
            f"**Zamawiający:** {municipality}  \n"
            f"**Przedmiot zamówienia:** {title}  \n\n---\n\n{strict_body}"
        )
        eval_result = guard.evaluate_claims_grounding(report.markdown_report, contexts)
        sections = parse_report_sections(strict_body)

    return {
        "report": report,
        "evaluation": eval_result,
        "contexts": contexts,
        "sections": sections,
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
            "Tytuł": "Wdrożenie zintegrowanego systemu informacji przestrzennej i geoportalu",
            "Zamawiający": "Gmina Kórnik",
            "Województwo": "Wielkopolskie",
            "Budżet PLN": 450000.0,
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

    # Sidebar: Filters & Infrastructure Status
    with st.sidebar:
        sliders_svg = get_svg_icon("sliders", size=20, color="#38bdf8")
        st.markdown(
            _compact_html(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
                {sliders_svg}
                <span style="font-weight:700;font-size:1rem;color:#f8fafc;">Filtrowanie zamówień</span>
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

        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        cpu_svg = get_svg_icon("cpu", size=20, color="#38bdf8")
        db_svg = get_svg_icon("database", size=16, color="#34d399")
        ollama_ok = check_ollama_health()
        status_dot_color = "#34d399" if ollama_ok else "#fbbf24"
        status_label = "Silnik Ollama aktywny" if ollama_ok else "Tryb syntezy deterministycznej"

        st.markdown(
            _compact_html(f"""
            <div class="glass-layer-1" style="padding:16px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    {cpu_svg}
                    <span style="font-weight:700;font-size:0.9rem;color:#f8fafc;">Status środowiska AI</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:0.84rem;color:#e2e8f0;">
                    <span style="width:8px;height:8px;border-radius:50%;background:{status_dot_color};box-shadow:0 0 10px {status_dot_color};display:inline-block;"></span>
                    <span>{status_label}</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;font-size:0.82rem;color:#cbd5e1;">
                    {db_svg}
                    <span>PostgreSQL 16 + pgvector HNSW</span>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    if filtered_df.empty:
        filtered_df = df.copy()

    # 1. Top Frosted Glass Header
    compass_svg = get_svg_icon("compass", size=24, color="#38bdf8")
    sparkles_svg = get_svg_icon("sparkles", size=16, color="#7dd3fc")
    st.markdown(
        _compact_html(f"""
        <div class="glass-layer-2" style="margin-bottom:24px;padding:20px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,rgba(56,189,248,0.24),rgba(99,102,241,0.24));border:1px solid rgba(255,255,255,0.28);display:flex;align-items:center;justify-content:center;box-shadow:0 8px 24px rgba(14,165,233,0.28);">
                    {compass_svg}
                </div>
                <div>
                    <h1 class="hero-title">GisMarketIntelligenceAi</h1>
                    <p style="margin:4px 0 0 0;color:#cbd5e1;font-size:0.94rem;">
                        Audyt barier konkurencyjnych SWZ/OPZ, weryfikacja formatów wymiany danych i ocena ryzyka odwołań do KIO
                    </p>
                </div>
            </div>
            <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(56,189,248,0.14);border:1px solid rgba(56,189,248,0.35);padding:8px 14px;border-radius:999px;font-size:0.82rem;color:#e0f2fe;font-weight:600;">
                {sparkles_svg}
                <span>Kontrola wierności RAGAS &ge; 0.95</span>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # 2. Immediate Interactive Cockpit at the Top (so user functions are immediately visible & accessible)
    options_map: Dict[str, pd.Series] = {}
    option_labels = []
    for _, row in filtered_df.iterrows():
        budget_val = float(row["Budżet PLN"]) if pd.notna(row["Budżet PLN"]) else 0.0
        budget_tag = f"{budget_val:,.0f} PLN".replace(",", " ") if budget_val > 0 else "Budżet wg SWZ"
        label = f"{row['Zamawiający']} | {str(row['Tytuł'])[:68]} ({budget_tag})"
        options_map[label] = row
        option_labels.append(label)

    col_select, col_mode, col_cta = st.columns([2.4, 1.8, 1.0])
    with col_select:
        selected_label = st.selectbox("Wybierz postępowanie do audytu", option_labels, index=0)
    with col_mode:
        selected_preset_name = st.selectbox("Zakres analizy AI", list(AUDIT_PRESETS.keys()), index=0)
    with col_cta:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        trigger_btn = st.button("Uruchom audyt SWZ", use_container_width=True)

    selected_row = options_map[selected_label]
    selected_id = str(selected_row["ID"])
    preset_query = AUDIT_PRESETS[selected_preset_name]

    custom_query = preset_query
    if selected_preset_name == "Własne pytanie do dokumentacji SWZ":
        custom_query = st.text_input(
            "Wpisz własne pytanie analityczne do dokumentacji SWZ/OPZ",
            value="Czy zamawiający wymaga zamkniętego formatu .str i jakie przewidział kary umowne?",
        )

    state_key = f"{selected_id}::{selected_preset_name}::{custom_query}"
    if trigger_btn or st.session_state.get("last_audit_key") != state_key:
        with st.spinner("Wyszukiwanie hybrydowe w dokumentacji SWZ i weryfikacja wierności RAGAS..."):
            st.session_state["analysis_result"] = run_rag_analysis(
                ocds_id=selected_id,
                title=str(selected_row["Tytuł"]),
                municipality=str(selected_row["Zamawiający"]),
                custom_query=custom_query,
            )
            st.session_state["last_audit_key"] = state_key

    result = st.session_state.get("analysis_result")

    # 3. Three High-Impact Spotlight Cards (Most Important Data Immediately Visible)
    if result:
        report = result["report"]
        eval_res = result["evaluation"]
        sections = result.get("sections") or parse_report_sections(report.raw_llm_output)
        full_text_lower = report.markdown_report.lower()

        has_lockin = ".str" in full_text_lower or "ewmapa" in full_text_lower or "vendor lock-in" in full_text_lower
        has_penalties = "kar" in full_text_lower or "2%" in full_text_lower

        kio_status = "WYSOKIE RYZYKO" if has_lockin else "NISKIE RYZYKO"
        kio_color = "#f87171" if has_lockin else "#34d399"
        kio_sub = "Wykryto wymóg zamkniętego formatu .str (art. 16 i 99 PZP)" if has_lockin else "Brak barier wykluczających"

        sel_budget = float(selected_row["Budżet PLN"]) if pd.notna(selected_row["Budżet PLN"]) else 0.0
        budget_display = f"{sel_budget:,.0f} PLN".replace(",", " ") if sel_budget > 0 else "Wg kosztorysu SWZ"
        faith_pct = f"{eval_res.faithfulness * 100:.0f}%"

        scale_svg = get_svg_icon("scale", size=20, color=kio_color)
        wallet_svg = get_svg_icon("wallet", size=20, color="#38bdf8")
        check_svg = get_svg_icon("check-circle", size=20, color="#34d399")

        sp1, sp2, sp3 = st.columns(3)
        with sp1:
            st.markdown(
                _compact_html(f"""
                <div class="glass-layer-3">
                    <div class="spotlight-label">{scale_svg}<span>Werdykt PZP i ryzyko KIO</span></div>
                    <div class="spotlight-value" style="color:{kio_color};">{kio_status}</div>
                    <div class="spotlight-caption">{html.escape(kio_sub)}</div>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with sp2:
            st.markdown(
                _compact_html(f"""
                <div class="glass-layer-2">
                    <div class="spotlight-label">{wallet_svg}<span>Wartość zamówienia i zamawiający</span></div>
                    <div class="spotlight-value">{budget_display}</div>
                    <div class="spotlight-caption">{html.escape(str(selected_row['Zamawiający']))} ({html.escape(str(selected_row['Województwo']))})</div>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with sp3:
            st.markdown(
                _compact_html(f"""
                <div class="glass-layer-2">
                    <div class="spotlight-label">{check_svg}<span>Wierność odpowiedzi AI (RAGAS)</span></div>
                    <div class="spotlight-value" style="color:#34d399;">{faith_pct}</div>
                    <div class="spotlight-caption">Faithfulness: {eval_res.faithfulness:.4f} (wymagany próg &ge; 0.95)</div>
                </div>
                """),
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        # 4. Clean Tabbed Navigation so content never blurs together
        tab_audit, tab_evidence, tab_catalog = st.tabs([
            "Wnioski i raport wykonawczy",
            "Konkurencja i dowody z SWZ",
            f"Katalog postępowań w bazie ({len(filtered_df)})",
        ])

        with tab_audit:
            badges_html = ""
            if has_lockin:
                badges_html += render_red_flag_badge("vendor_lockin")
            if has_penalties:
                badges_html += render_red_flag_badge("asymetria_kar")
            if badges_html:
                st.markdown(f"<div style='margin:8px 0 4px 0;'>{badges_html}</div>", unsafe_allow_html=True)

            st.markdown(render_kio_warning("HIGH" if has_lockin else "LOW"), unsafe_allow_html=True)

            # 2x2 Frosted Glass Insight Grid (replaces the unreadable raw markdown wall)
            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                st.markdown(
                    render_insight_section_card(
                        title="1. Zakres i przedmiot zamówienia",
                        body=sections.get("summary", ""),
                        icon_name="layers",
                        accent_color="#38bdf8",
                    ),
                    unsafe_allow_html=True,
                )
            with row1_col2:
                st.markdown(
                    render_insight_section_card(
                        title="2. Wykryte bariery techniczne i prawne",
                        body=sections.get("legal_barriers", ""),
                        icon_name="shield-alert",
                        accent_color="#f87171",
                    ),
                    unsafe_allow_html=True,
                )

            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                st.markdown(
                    render_insight_section_card(
                        title="3. Rekomendacje i ryzyka kontraktowe",
                        body=sections.get("recommendations", ""),
                        icon_name="scale",
                        accent_color="#fbbf24",
                    ),
                    unsafe_allow_html=True,
                )
            with row2_col2:
                st.markdown(
                    render_insight_section_card(
                        title="4. Układ sił i wymagane systemy GIS",
                        body=sections.get("competitors", ""),
                        icon_name="radar",
                        accent_color="#818cf8",
                    ),
                    unsafe_allow_html=True,
                )

            st.download_button(
                label="Pobierz pełny raport w formacie Markdown (.md)",
                data=report.markdown_report,
                file_name=f"raport_{selected_id}.md",
                mime="text/markdown",
            )

        with tab_evidence:
            ev_col1, ev_col2 = st.columns([1.15, 1.0])
            with ev_col1:
                radar_svg = get_svg_icon("radar", size=20, color="#38bdf8")
                st.markdown(
                    _compact_html(f"""
                    <div style="display:flex;align-items:center;gap:10px;margin:8px 0 12px 0;">
                        {radar_svg}
                        <h3 class="section-heading">Macierz konkurencji regionalnej</h3>
                    </div>
                    """),
                    unsafe_allow_html=True,
                )
                competitors_data = [
                    {
                        "name": "Geobid Sp. z o.o.",
                        "product": "EWMAPA / OŚRODEK",
                        "advantage": "Wymóg przekazywania operatów w zamkniętym formacie .str",
                    },
                    {
                        "name": "Geo-System Sp. z o.o.",
                        "product": "iMPA / e-Gmina",
                        "advantage": "Wymagana bezpośrednia integracja z portalem mapowym gminy",
                    },
                ]
                st.markdown(render_competitor_matrix(competitors_data), unsafe_allow_html=True)

            with ev_col2:
                file_svg = get_svg_icon("file-check", size=20, color="#34d399")
                st.markdown(
                    _compact_html(f"""
                    <div style="display:flex;align-items:center;gap:10px;margin:8px 0 12px 0;">
                        {file_svg}
                        <h3 class="section-heading">Zweryfikowane źródła dowodowe SWZ/OPZ</h3>
                    </div>
                    """),
                    unsafe_allow_html=True,
                )
                for citation in report.citations:
                    st.markdown(render_citation_box(citation), unsafe_allow_html=True)

        with tab_catalog:
            layers_svg = get_svg_icon("layers", size=20, color="#38bdf8")
            st.markdown(
                _compact_html(f"""
                <div style="display:flex;align-items:center;gap:10px;margin:8px 0 16px 0;">
                    {layers_svg}
                    <h3 class="section-heading">Wszystkie zindeksowane postępowania ({len(filtered_df)})</h3>
                </div>
                """),
                unsafe_allow_html=True,
            )
            for _, row in filtered_df.iterrows():
                row_id = str(row["ID"])
                st.markdown(
                    render_tender_card(
                        ocds_id=row_id,
                        title=str(row["Tytuł"]),
                        municipality=str(row["Zamawiający"]),
                        voivodeship=str(row["Województwo"]),
                        budget_pln=float(row["Budżet PLN"]) if pd.notna(row["Budżet PLN"]) else 0.0,
                        status=str(row.get("Status", "ACTIVE")),
                        is_selected=(row_id == selected_id),
                    ),
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
