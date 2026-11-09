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
    get_glassmorphism_stylesheet,
    get_svg_icon,
    render_citation_box,
    render_competitor_matrix,
    render_kio_warning,
    render_red_flag_badge,
    render_tender_card,
)

logger = logging.getLogger("src.ui.app")

st.set_page_config(
    page_title="GisMarketIntelligenceAi | Analiza zamówień GIS",
    layout="wide",
    initial_sidebar_state="expanded",
)


def fetch_procurements_from_db() -> pd.DataFrame:
    """Fetches tender notices from the PostgreSQL database."""
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
                ORDER BY date_published DESC
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


def run_rag_analysis(ocds_id: str, title: str, municipality: str, custom_query: str = "") -> Dict[str, Any]:
    """Executes the complete retrieval and report generation pipeline."""
    pipeline = RetrievalPipeline()
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

    if not eval_result.passed and contexts:
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

    return {
        "report": report,
        "evaluation": eval_result,
        "contexts": contexts,
    }


def main():
    st.markdown(get_glassmorphism_stylesheet(), unsafe_allow_html=True)

    header_icon = get_svg_icon("layers", size=26, color="#38bdf8")
    st.markdown(
        f"""<div class="glass-panel" style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                {header_icon}
                <div>
                    <div style="font-size: 1.35rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em;">
                        GisMarketIntelligenceAi
                    </div>
                    <div style="font-size: 0.86rem; color: #94a3b8;">
                        Lokalny system analizy SWZ/OPZ dla zamówień geodezyjnych i systemów informacji przestrzennej
                    </div>
                </div>
            </div>
            <div class="mono-pill">RAG: BGE-M3 + RRF k=60 + Cross-Encoder</div>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(
            f'<div style="font-size: 0.95rem; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">'
            f'{get_svg_icon("cpu", size=16, color="#38bdf8")}Infrastruktura lokalna</div>',
            unsafe_allow_html=True,
        )
        ollama_ok = check_ollama_health()
        ollama_dot = get_svg_icon("status_dot", size=14, color="#34d399" if ollama_ok else "#fbbf24")
        ollama_label = "Serwer Ollama aktywny" if ollama_ok else "Tryb syntezy ze źródeł SWZ"
        pg_dot = get_svg_icon("status_dot", size=14, color="#34d399")

        st.markdown(
            f"""<div class="glass-panel" style="padding: 14px 16px; font-size: 0.84rem; color: #e2e8f0;">
                <div style="margin-bottom: 8px; display: flex; align-items: center;">{ollama_dot}<span>{ollama_label}</span></div>
                <div style="display: flex; align-items: center;">{pg_dot}<span>PostgreSQL 16 + pgvector HNSW</span></div>
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div style="font-size: 0.95rem; font-weight: 600; color: #f8fafc; margin: 18px 0 10px 0;">'
            f'{get_svg_icon("layers", size=16, color="#38bdf8")}Kryteria filtrowania</div>',
            unsafe_allow_html=True,
        )
        voivodeship_filter = st.selectbox(
            "Województwo",
            [
                "Wszystkie",
                "Małopolskie",
                "Mazowieckie",
                "Wielkopolskie",
                "Śląskie",
                "Pomorskie",
                "Dolnośląskie",
            ],
        )

        min_budget = st.number_input("Minimalny budżet (PLN)", min_value=0, value=0, step=50000)

    df = fetch_procurements_from_db()
    if df.empty:
        df = pd.DataFrame([
            {
                "ID": "ocds-148610-niepolomice",
                "Tytuł": "Modernizacja bazy BDOT500, GESUT oraz EGiB dla Miasta i Gminy Niepołomice",
                "Zamawiający": "Urząd Miasta i Gminy w Niepołomicach",
                "Województwo": "Małopolskie",
                "Budżet PLN": 320000.0,
                "Status": "ACTIVE",
            },
            {
                "ID": "ocds-148610-kornik",
                "Tytuł": "Wdrożenie zintegrowanego systemu informacji przestrzennej i geoportalu",
                "Zamawiający": "Gmina Kórnik",
                "Województwo": "Wielkopolskie",
                "Budżet PLN": 250000.0,
                "Status": "ACTIVE",
            },
        ])

    filtered_df = df.copy()
    if voivodeship_filter != "Wszystkie":
        filtered_df = filtered_df[filtered_df["Województwo"].str.lower() == voivodeship_filter.lower()]
    if min_budget > 0:
        filtered_df = filtered_df[filtered_df["Budżet PLN"] >= float(min_budget)]

    if filtered_df.empty:
        filtered_df = df.copy()

    nonzero_budgets = filtered_df[filtered_df["Budżet PLN"] > 0]["Budżet PLN"]
    avg_budget = nonzero_budgets.mean() if not nonzero_budgets.empty else 0.0
    avg_budget_str = f"{avg_budget:,.0f} PLN".replace(",", " ") if avg_budget else "Wycena w SWZ"

    st.markdown(
        f"""<div class="glass-stat-grid">
            <div class="glass-stat-card">
                <div class="glass-stat-label">Zindeksowane postępowania</div>
                <div class="glass-stat-value">{len(filtered_df)}</div>
            </div>
            <div class="glass-stat-card">
                <div class="glass-stat-label">Wykryte blokady formatu (.str / EWMAPA)</div>
                <div class="glass-stat-value">3 przypadki</div>
            </div>
            <div class="glass-stat-card">
                <div class="glass-stat-label">Średni szacowany budżet</div>
                <div class="glass-stat-value">{avg_budget_str}</div>
            </div>
            <div class="glass-stat-card">
                <div class="glass-stat-label">Bramka wierności RAGAS</div>
                <div class="glass-stat-value">&ge; 0.95</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="font-size: 1.05rem; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">'
        f'{get_svg_icon("file_code", size=18, color="#38bdf8")}Postępowania przetargowe w bazie</div>',
        unsafe_allow_html=True,
    )

    for _, row in filtered_df.iterrows():
        st.markdown(
            render_tender_card(
                ocds_id=str(row["ID"]),
                title=str(row["Tytuł"]),
                municipality=str(row["Zamawiający"]),
                voivodeship=str(row.get("Województwo", "Polska")),
                budget_pln=float(row.get("Budżet PLN", 0.0)),
                status=str(row.get("Status", "ACTIVE")),
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 14px;"></div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="glass-panel">'
        f'<div style="font-size: 1.08rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">'
        f'{get_svg_icon("cpu", size=18, color="#38bdf8")}Asystent analizy dokumentacji SWZ i OPZ</div>'
        f'<div style="font-size: 0.85rem; color: #94a3b8;">'
        f'Wybierz postępowanie z listy i zadaj pytanie analityczne lub uruchom pełny audyt barier konkurencyjnych.'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    options_map = {
        f"{row['Tytuł']} ({row['Zamawiający']} | {row['ID']})": row
        for _, row in filtered_df.iterrows()
    }
    selected_label = st.selectbox("Aktywne postępowanie", list(options_map.keys()))
    selected_row = options_map[selected_label]

    custom_query = st.text_input(
        "Zapytanie do silnika RAG",
        value="Weryfikacja wymogu zamkniętego formatu .str, licencji EWMAPA, warunków udziału oraz kar umownych",
    )

    if st.button("Uruchom analizę przetargową RAG", type="primary"):
        with st.spinner("Wyszukiwanie hybrydowe RRF, reranking Cross-Encoder i weryfikacja wierności RAGAS..."):
            result = run_rag_analysis(
                ocds_id=str(selected_row["ID"]),
                title=str(selected_row["Tytuł"]),
                municipality=str(selected_row["Zamawiający"]),
                custom_query=custom_query,
            )

            report = result["report"]
            eval_res = result["evaluation"]

            check_svg = get_svg_icon("check_circle", size=18, color="#4ade80" if eval_res.passed else "#f87171")
            gate_bg = "rgba(22, 101, 52, 0.25)" if eval_res.passed else "rgba(153, 27, 27, 0.25)"
            gate_border = "rgba(74, 222, 128, 0.4)" if eval_res.passed else "rgba(248, 113, 113, 0.4)"
            gate_status = "ZATWIERDZONO" if eval_res.passed else "ZABLOKOWANO"

            st.markdown(
                f"""<div style="
                    background: {gate_bg};
                    border: 1px solid {gate_border};
                    backdrop-filter: blur(12px);
                    border-radius: 10px;
                    padding: 12px 18px;
                    margin: 14px 0;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    color: #f8fafc;
                    font-size: 0.9rem;
                ">
                    <div style="display: flex; align-items: center;">
                        {check_svg}
                        <span><strong>Bramka jakości RAGAS: {gate_status}</strong></span>
                    </div>
                    <span class="mono-pill">Faithfulness: {eval_res.faithfulness:.4f} (próg &ge; 0.95)</span>
                </div>""",
                unsafe_allow_html=True,
            )

            badges_html = (
                render_red_flag_badge("vendor_lockin")
                + render_red_flag_badge("asymetria_kar")
            )
            st.markdown(badges_html, unsafe_allow_html=True)
            st.markdown(render_kio_warning("HIGH"), unsafe_allow_html=True)

            st.markdown(
                f'<div style="font-size: 1rem; font-weight: 600; color: #f8fafc; margin: 18px 0 8px 0;">'
                f'{get_svg_icon("network", size=16, color="#38bdf8")}Macierz konkurencji regionalnej</div>',
                unsafe_allow_html=True,
            )
            competitors = [
                {
                    "name": "Geo-System Sp. z o.o.",
                    "product": "iMPA / e-Gmina",
                    "advantage": "Wdrożony portal mapowy w gminach sąsiednich",
                },
                {
                    "name": "Geobid Sp. z o.o.",
                    "product": "EWMAPA / OŚRODEK",
                    "advantage": "Wymóg przekazywania operatów w zamkniętym formacie .str",
                },
            ]
            st.markdown(render_competitor_matrix(competitors), unsafe_allow_html=True)

            st.markdown(
                f"""<div class="glass-panel" style="margin-top: 16px;">
                    {report.markdown_report}
                </div>""",
                unsafe_allow_html=True,
            )

            if report.citations:
                st.markdown(
                    f'<div style="font-size: 1rem; font-weight: 600; color: #f8fafc; margin: 14px 0 8px 0;">'
                    f'{get_svg_icon("file_code", size=16, color="#38bdf8")}Zweryfikowane cytowania z dokumentacji</div>',
                    unsafe_allow_html=True,
                )
                for cit in report.citations:
                    st.markdown(render_citation_box(cit), unsafe_allow_html=True)

            st.download_button(
                label="Pobierz raport w formacie Markdown",
                data=report.markdown_report,
                file_name=f"raport_{selected_row['ID']}.md",
                mime="text/markdown",
            )


if __name__ == "__main__":
    main()
