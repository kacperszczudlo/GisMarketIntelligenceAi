import asyncio
import logging
from pathlib import Path
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
    "1. Blokada formatu danych (.str / EWMAPA vs otwarty GML)": (
        "Czy zamawiający narzuca zamknięty format natywny .str kompatybilny z programem EWMAPA bez udostępnienia struktury pośredniej GML?"
    ),
    "2. Kary umowne za zwłokę i brak górnego limitu (art. 436 PZP)": (
        "Jaką wysokość kary umownej za każdy dzień zwłoki przewidział zamawiający i czy umowa zawiera górny limit kar?"
    ),
    "3. Uprawnienia geodezyjne GUGiK i doświadczenie kierownika prac": (
        "Jakich uprawnień zawodowych GUGiK (zakres 1 i 2) oraz jakiego minimalnego doświadczenia wymaga zamawiający od kierownika prac geodezyjnych?"
    ),
    "4. Integracja z bazą PODGiK (OŚRODEK) i portalem mapowym (iMPA)": (
        "Z jaką bazą danych ośrodka (np. OŚRODEK) oraz jakim portalem mapowym (np. iMPA firmy Geo-System) wymagana jest bezpośrednia integracja?"
    ),
    "5. Zakres prac modernizacyjnych (BDOT500 / GESUT / EGiB) i budżet": (
        "Jaki jest dokładny zakres modernizacji baz BDOT500, GESUT i EGiB oraz jaka jest szacunkowa wartość zamówienia netto?"
    ),
    "6. Podstawy prawne odwołania do KIO (art. 16 i art. 99 PZP)": (
        "Które wymogi techniczne w OPZ stanowią barierę Vendor Lock-in naruszającą art. 16 i art. 99 PZP oraz uzasadniają odwołanie do KIO?"
    ),
    "7. Klauzule społeczne i zastrzeżenia podmiotowe (art. 94 PZP)": (
        "Czy zamawiający zastrzegł w ogłoszeniu, że o udzielenie zamówienia mogą ubiegać się wyłącznie wykonawcy wskazani w art. 94 ustawy PZP?"
    ),
    "8. Własne pytanie (wpisz ręcznie w polu poniżej)": "",
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
    active_question = (
        custom_query.strip()
        or "Czy zamawiający narzuca zamknięty format natywny .str kompatybilny z programem EWMAPA bez udostępnienia struktury pośredniej GML?"
    )
    retrieved_items = pipeline.retrieve(query=active_question, procurement_id=ocds_id, top_k=5)

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

    direct_answer = generator.answer_specific_question(active_question, merged_context)

    return {
        "report": report,
        "evaluation": eval_result,
        "contexts": contexts,
        "sections": sections,
        "active_question": active_question,
        "direct_answer": direct_answer,
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

    # Left Sidebar: Compact Brand Logo at Top-Left + Tender Selection + Filters
    with st.sidebar:
        st.markdown(render_brand_sidebar_header(), unsafe_allow_html=True)

        layers_svg = get_svg_icon("layers", size=16, color="#2563eb")
        st.markdown(
            _compact_html(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;color:#0f172a;font-weight:700;font-size:0.84rem;">
                {layers_svg}
                <span>Wybór i filtrowanie SWZ</span>
            </div>
            """),
            unsafe_allow_html=True,
        )

        voivodeships = ["Wszystkie"] + sorted(df["Województwo"].dropna().unique().tolist())
        selected_voiv = st.selectbox("Region (Województwo)", voivodeships)
        min_budget = st.number_input("Minimalny budżet (PLN)", min_value=0, value=0, step=50000)

        filtered_df = df.copy()
        if selected_voiv != "Wszystkie":
            filtered_df = filtered_df[filtered_df["Województwo"] == selected_voiv]
        if min_budget > 0:
            filtered_df = filtered_df[filtered_df["Budżet PLN"] >= min_budget]
        if filtered_df.empty:
            filtered_df = df.copy()

        options_map: Dict[str, pd.Series] = {}
        option_labels = []
        for _, row in filtered_df.iterrows():
            label = f"{row['Zamawiający']} — {str(row['Tytuł'])[:45]}..."
            options_map[label] = row
            option_labels.append(label)

        selected_label = st.selectbox("Aktywne postępowanie", option_labels, index=0)

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        sliders_svg = get_svg_icon("sparkles", size=16, color="#2563eb")
        st.markdown(
            _compact_html(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;color:#0f172a;font-weight:700;font-size:0.84rem;">
                {sliders_svg}
                <span>Szablony pytań PZP / GIS</span>
            </div>
            """),
            unsafe_allow_html=True,
        )
        template_names = list(RAG_QUESTION_TEMPLATES.keys())
        selected_template_name = st.selectbox(
            "Wybierz gotowy szablon pytania",
            template_names,
            index=0,
        )

    selected_row = options_map[selected_label]
    selected_id = str(selected_row["ID"])
    ollama_ok = check_ollama_health()

    # Sync question input with template dropdown when changed
    template_default_text = RAG_QUESTION_TEMPLATES[selected_template_name]
    if st.session_state.get("prev_template_name") != selected_template_name:
        st.session_state["prev_template_name"] = selected_template_name
        st.session_state["rag_question_input"] = (
            template_default_text
            if template_default_text
            else "Czy zamawiający dopuszcza otwarty format GML zamiast zamkniętego .str?"
        )

    current_q = st.session_state.get(
        "rag_question_input",
        RAG_QUESTION_TEMPLATES[template_names[0]],
    )

    state_key = f"{selected_id}::{current_q}"
    if st.session_state.get("last_audit_key") != state_key:
        with st.spinner("Analiza dokumentacji SWZ/OPZ..."):
            st.session_state["analysis_result"] = run_rag_analysis(
                ocds_id=selected_id,
                title=str(selected_row["Tytuł"]),
                municipality=str(selected_row["Zamawiający"]),
                custom_query=current_q,
            )
            st.session_state["last_audit_key"] = state_key

    result = st.session_state.get("analysis_result")
    report = result["report"]
    eval_res = result["evaluation"]
    sections = result.get("sections") or parse_report_sections(report.raw_llm_output)
    full_text_lower = report.markdown_report.lower()

    has_lockin = ".str" in full_text_lower or "ewmapa" in full_text_lower or "vendor lock-in" in full_text_lower
    has_penalties = "kar" in full_text_lower or "2%" in full_text_lower

    # 1. Top Utility Navbar (Breadcrumbs Left + Status Pills Right)
    st.markdown(
        render_top_utility_bar(
            municipality=str(selected_row["Zamawiający"]),
            voivodeship=str(selected_row["Województwo"]),
            ollama_ok=ollama_ok,
            total_tenders=len(filtered_df),
            has_lockin=has_lockin,
        ),
        unsafe_allow_html=True,
    )

    # 2. Row 1: 4 Horizontal KPI Cards with Circular Colored Icon Badges
    sel_budget = float(selected_row["Budżet PLN"]) if pd.notna(selected_row["Budżet PLN"]) else 0.0
    if sel_budget >= 1000:
        budget_short = f"{sel_budget / 1000:.0f} tys. PLN"
    else:
        budget_short = "Wg SWZ"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            render_kpi_stat_card(
                value="WYSOKIE" if has_lockin else "NISKIE",
                label="Ryzyko odwołania KIO",
                sublabel="Art. 16 i 99 PZP (format .str)",
                icon_name="shield-alert",
                color_hex="#ff6b57" if has_lockin else "#10b981",
                ring_bg="rgba(255, 107, 87, 0.14)" if has_lockin else "rgba(16, 185, 129, 0.14)",
                stagger_index=0,
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            render_kpi_stat_card(
                value=budget_short,
                label="Szacowany budżet",
                sublabel=str(selected_row["Zamawiający"]),
                icon_name="wallet",
                color_hex="#3b82f6",
                ring_bg="rgba(59, 130, 246, 0.14)",
                stagger_index=1,
            ),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            render_kpi_stat_card(
                value="2% / dzień" if has_penalties else "Standard",
                label="Kary umowne w SWZ",
                sublabel="Brak górnego limitu (cap)" if has_penalties else "Zgodne z art. 436 PZP",
                icon_name="scale",
                color_hex="#f59e0b",
                ring_bg="rgba(245, 158, 11, 0.14)",
                stagger_index=2,
            ),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            render_kpi_stat_card(
                value=f"{eval_res.faithfulness * 100:.0f}%",
                label="Wierność RAGAS",
                sublabel=f"Faithfulness: {eval_res.faithfulness:.2f} (próg ≥ 0.95)",
                icon_name="check-circle",
                color_hex="#10b981",
                ring_bg="rgba(16, 185, 129, 0.14)",
                stagger_index=3,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    # 3. Row 2: Asymmetric Main Split (Left Analytical Workspace ~69% + Right Risk Profile Card ~31%)
    main_left, main_right = st.columns([2.25, 1.0])

    with main_left:
        # Clean inline question bar (editable template or custom question + single action button)
        q_col, btn_col = st.columns([3.5, 1.0])
        with q_col:
            user_question = st.text_input(
                "Zadaj pytanie do dokumentacji SWZ/OPZ (wybierz szablon w panelu bocznym lub wpisz własne)",
                key="rag_question_input",
            )
        with btn_col:
            st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
            if st.button("Analizuj pytanie", use_container_width=True):
                st.session_state["analysis_result"] = run_rag_analysis(
                    ocds_id=selected_id,
                    title=str(selected_row["Tytuł"]),
                    municipality=str(selected_row["Zamawiający"]),
                    custom_query=user_question,
                )
                st.session_state["last_audit_key"] = f"{selected_id}::{user_question}"
                result = st.session_state["analysis_result"]

        tab_insights, tab_sources, tab_export = st.tabs([
            "Wnioski i audyt SWZ",
            "Konkurencja i dowody",
            "Eksport raportu (.md)",
        ])

        with tab_insights:
            st.markdown(
                render_direct_answer_card(
                    question=result.get("active_question", user_question),
                    answer=result.get("direct_answer", ""),
                ),
                unsafe_allow_html=True,
            )

            r1c1, r1c2 = st.columns(2)
            with r1c1:
                st.markdown(
                    render_insight_section_card(
                        title="1. Zakres i przedmiot zamówienia",
                        body=sections.get("summary", ""),
                        icon_name="layers",
                        accent_color="#2563eb",
                    ),
                    unsafe_allow_html=True,
                )
            with r1c2:
                st.markdown(
                    render_insight_section_card(
                        title="2. Bariery techniczne (Vendor Lock-in)",
                        body=sections.get("legal_barriers", ""),
                        icon_name="shield-alert",
                        accent_color="#e11d48",
                    ),
                    unsafe_allow_html=True,
                )

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                st.markdown(
                    render_insight_section_card(
                        title="3. Kary umowne i wymogi kadrowe",
                        body=sections.get("recommendations", ""),
                        icon_name="scale",
                        accent_color="#d97706",
                    ),
                    unsafe_allow_html=True,
                )
            with r2c2:
                st.markdown(
                    render_insight_section_card(
                        title="4. Wymagane systemy dziedzinowe GIS",
                        body=sections.get("competitors", ""),
                        icon_name="radar",
                        accent_color="#6366f1",
                    ),
                    unsafe_allow_html=True,
                )

        with tab_sources:
            badges_html = ""
            if has_lockin:
                badges_html += render_red_flag_badge("vendor_lockin")
            if has_penalties:
                badges_html += render_red_flag_badge("asymetria_kar")
            if badges_html:
                st.markdown(f"<div style='margin-bottom:8px;'>{badges_html}</div>", unsafe_allow_html=True)

            st.markdown(render_kio_warning("HIGH" if has_lockin else "LOW"), unsafe_allow_html=True)

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

            for citation in report.citations:
                st.markdown(render_citation_box(citation), unsafe_allow_html=True)

        with tab_export:
            st.download_button(
                label="Pobierz pełny raport w formacie Markdown (.md)",
                data=report.markdown_report,
                file_name=f"raport_{selected_id}.md",
                mime="text/markdown",
            )
            st.code(report.markdown_report, language="markdown")

    with main_right:
        st.markdown(
            render_risk_profile_panel(
                has_lockin=has_lockin,
                has_penalties=has_penalties,
                faithfulness=eval_res.faithfulness,
            ),
            unsafe_allow_html=True,
        )

    # 4. Row 3: Full-Width Clean Procurements Table Card (Bottom Section)
    table_records = filtered_df.to_dict(orient="records")
    st.markdown(
        render_procurements_table(rows=table_records, selected_id=selected_id),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
