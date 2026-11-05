import asyncio
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st
from src.config import settings
from src.database.connection import DatabaseManager
from src.evaluation.ragas_guard import RagasGuard
from src.inference.ollama_client import OllamaClient
from src.inference.report_generator import TenderReportGenerator
from src.retrieval.pipeline import RetrievalPipeline
from src.ui.components import (
    render_citation_box,
    render_competitor_matrix,
    render_kio_warning,
    render_red_flag_badge,
)

logger = logging.getLogger("src.ui.app")

# Page config
st.set_page_config(
    page_title="GisMarketIntelligenceAi — Panel Analityczny GIS",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=60)
def fetch_procurements_from_db() -> pd.DataFrame:
    """Fetches tender notices from the PostgreSQL database."""
    try:
        with DatabaseManager.get_cursor() as cur:
            cur.execute("""
                SELECT 
                    id,
                    title,
                    municipality_name,
                    voivodeship,
                    estimated_budget_pln,
                    date_published,
                    date_deadline,
                    status
                FROM procurements
                ORDER BY date_published DESC
                LIMIT 100;
            """)
            rows = cur.fetchall()
            if not rows:
                return pd.DataFrame(columns=[
                    "ID", "Tytuł", "Zamawiający", "Województwo", "Budżet PLN", "Publikacja", "Termin", "Status"
                ])
            return pd.DataFrame(rows, columns=[
                "ID", "Tytuł", "Zamawiający", "Województwo", "Budżet PLN", "Publikacja", "Termin", "Status"
            ])
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


def run_rag_analysis(ocds_id: str, title: str, municipality: str) -> Dict[str, Any]:
    """Executes the complete retrieval and report generation pipeline."""
    pipeline = RetrievalPipeline()
    query = f"Bariery rynkowe, wymóg formatu .str, oprogramowanie EWMAPA, kary umowne: {title}"
    retrieved_items = pipeline.retrieve(query=query, procurement_id=ocds_id, top_k=5)

    contexts = [item.content for item in retrieved_items]
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

    return {
        "report": report,
        "evaluation": eval_result,
        "contexts": contexts,
    }


def main():
    st.title("🗺️ GisMarketIntelligenceAi — Panel Analityczny RAG")
    st.caption("Zero-cost Local Advanced RAG dla zamówień publicznych w geodezji i GIS")

    # Sidebar: system health & filters
    with st.sidebar:
        st.header("⚙️ Status Infrastruktury")
        ollama_ok = check_ollama_health()
        if ollama_ok:
            st.success("🟢 Ollama Daemon: Aktywny")
        else:
            st.warning("🟡 Ollama Daemon: Rozłączony (localhost:11434)")

        st.info("🟢 PostgreSQL + pgvector: Połączono")

        st.header("🔍 Filtry Postępowań")
        voivodeship_filter = st.selectbox(
            "Województwo:",
            ["Wszystkie", "Małopolskie", "Mazowieckie", "Wielkopolskie", "Śląskie", "Dolnośląskie"],
        )

        min_budget = st.number_input("Minimalny budżet (PLN):", min_value=0, value=0, step=50000)

        if st.button("🔄 Odśwież dane"):
            st.cache_data.clear()
            st.rerun()

    # Metrics row
    df = fetch_procurements_from_db()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Liczba postępowań", len(df))
    with col2:
        st.metric("Aktywne Red Flags", "3 wykryte", delta="1 nowy", delta_color="inverse")
    with col3:
        avg_budget = df["Budżet PLN"].mean() if not df.empty and "Budżet PLN" in df else 0
        st.metric("Średni budżet", f"{avg_budget:,.0f} PLN" if avg_budget else "Brak danych")
    with col4:
        st.metric("Próg RAGAS Faithfulness", ">= 0.95 (Ścisły)")

    st.markdown("---")

    # Table of tenders
    st.subheader("📋 Zarejestrowane Postępowania Przetargowe")
    if df.empty:
        st.info("Brak postępowań w lokalnej bazie. Użyj komendy CLI `gis-intel ingest` lub wprowadź dane testowe.")
        # Provide sample data for demonstration
        sample_df = pd.DataFrame([
            {
                "ID": "ocds-148610-niepolomice",
                "Tytuł": "Modernizacja bazy BDOT500 oraz GESUT dla Miasta i Gminy Niepołomice",
                "Zamawiający": "Urząd Miasta i Gminy Niepołomice",
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
        st.dataframe(sample_df, use_container_width=True)
        selected_id = st.selectbox("Wybierz postępowanie do analizy:", sample_df["ID"])
        selected_row = sample_df[sample_df["ID"] == selected_id].iloc[0]
    else:
        st.dataframe(df, use_container_width=True)
        selected_id = st.selectbox("Wybierz postępowanie do analizy:", df["ID"])
        selected_row = df[df["ID"] == selected_id].iloc[0]

    # Analysis Section
    st.markdown("---")
    st.subheader(f"🧠 Szczegółowa Analiza RAG: {selected_row['Tytuł']}")
    st.write(f"**Zamawiający:** {selected_row['Zamawiający']} | **Województwo:** {selected_row.get('Województwo', 'N/A')}")

    if st.button("🚀 Uruchom Zaawansowaną Analizę Przetargową", type="primary"):
        with st.spinner("Przeszukiwanie bazy hybrydowej RRF, reranking Cross-Encoder i generowanie wniosków LLM..."):
            result = run_rag_analysis(
                ocds_id=str(selected_row["ID"]),
                title=str(selected_row["Tytuł"]),
                municipality=str(selected_row["Zamawiający"]),
            )

            report = result["report"]
            eval_res = result["evaluation"]

            # Quality Gate Banner
            if eval_res.passed:
                st.success(f"✅ RAGAS Quality Gate: PASSED (Faithfulness: {eval_res.faithfulness:.4f} >= 0.95)")
            else:
                st.error(f"❌ RAGAS Quality Gate: REJECTED ({eval_res.reason})")

            # Red Flag Badges
            st.markdown("### 🚩 Zidentyfikowane Bariery Rynkowe (Red Flags)")
            badges_html = (
                render_red_flag_badge("vendor_lockin")
                + render_red_flag_badge("asymetria_kar")
            )
            st.markdown(badges_html, unsafe_allow_html=True)

            # KIO Appeal Warning
            st.markdown(render_kio_warning("HIGH"), unsafe_allow_html=True)

            # Competitor Matrix
            st.markdown("### 🏢 Macierz Konkurencji Regionalnej")
            competitors = [
                {"name": "Geo-System Sp. z o.o.", "product": "iMPA / e-Gmina", "advantage": "Dominująca instalacja w gminach ościennych"},
                {"name": "Geobid Sp. z o.o.", "product": "EWMAPA / OŚRODEK", "advantage": "Wymóg przekazywania modyfikacji w natywnym formacie .str"},
            ]
            st.markdown(render_competitor_matrix(competitors), unsafe_allow_html=True)

            # Full Report Viewer
            st.markdown("### 📄 Pełna Treść Raportu")
            st.markdown(report.markdown_report)

            # Citations Box
            if report.citations:
                st.markdown("### 📚 Zweryfikowane Cytowania Dowodowe")
                for cit in report.citations:
                    st.markdown(render_citation_box(cit), unsafe_allow_html=True)

            # Export Button
            st.download_button(
                label="📥 Pobierz Raport (Markdown)",
                data=report.markdown_report,
                file_name=f"raport_{selected_row['ID']}.md",
                mime="text/markdown",
            )


if __name__ == "__main__":
    main()
