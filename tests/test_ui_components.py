import pytest
from src.inference.report_generator import TenderReportGenerator
from src.ui.app import RAG_QUESTION_TEMPLATES, extract_tender_metrics, parse_report_sections
from src.ui.components import (
    format_short_ocds_id,
    get_glassmorphism_stylesheet,
    get_svg_icon,
    highlight_domain_terms,
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
    render_tender_card,
    render_top_utility_bar,
)

SAMPLE_BUDGET_PLN = 320000.0
MIN_TEMPLATE_COUNT = 8


@pytest.mark.parametrize(
    ("flag_type", "expected_label"),
    [
        ("vendor_lockin", "Vendor Lock-in"),
        ("asymetria_kar", "Asymetria"),
        ("custom_unknown", "Ryzyko SWZ: custom_unknown"),
    ],
    ids=["vendor_lockin_badge", "penalty_asymmetry_badge", "fallback_badge"],
)
def test_should_render_red_flag_badge_with_svg_icon(
    flag_type: str,
    expected_label: str,
) -> None:
    # Arrange & Act
    badge = render_red_flag_badge(flag_type)

    # Assert
    assert expected_label in badge
    assert "<svg" in badge
    assert "background-color" in badge


def test_should_render_citation_box_and_escape_html_entities() -> None:
    # Arrange & Act
    box = render_citation_box("SWZ Rozdział II, s. 14 <script>")

    # Assert
    assert "SWZ Rozdział II, s. 14 &lt;script&gt;" in box
    assert "<svg" in box
    assert "źródło" in box.lower() or "dowod" in box.lower()


def test_should_render_competitor_matrix_cards() -> None:
    # Arrange
    competitors = [
        {"name": "Geo-System Sp. z o.o.", "product": "iMPA / e-Gmina", "advantage": "Zainstalowana baza w gminie"},
        {"name": "Systherm Info", "product": "GEO-INFO", "advantage": "Wymóg zgodności z formatem .giv"},
    ]

    # Act
    html = render_competitor_matrix(competitors)

    # Assert
    assert "Geo-System" in html
    assert "Systherm Info" in html
    assert "iMPA" in html


@pytest.mark.parametrize(
    ("risk_level", "expected_text"),
    [
        ("HIGH", "WYSOKIE"),
        ("MEDIUM", "ŚREDNIE"),
        ("LOW", "NISKIE"),
    ],
    ids=["high_kio_risk", "medium_kio_risk", "low_kio_risk"],
)
def test_should_render_kio_warning_banner_for_each_severity_level(
    risk_level: str,
    expected_text: str,
) -> None:
    # Arrange & Act
    warning = render_kio_warning(risk_level)

    # Assert
    assert "Ryzyko odwołania do KIO" in warning
    assert expected_text in warning.upper()
    assert "<svg" in warning


def test_should_render_tender_card_and_glassmorphism_stylesheet() -> None:
    # Arrange & Act
    css = get_glassmorphism_stylesheet()
    card = render_tender_card(
        ocds_id="ocds-148610-niepolomice",
        title="Modernizacja BDOT500",
        municipality="Gmina Niepołomice",
        voivodeship="Małopolskie",
        budget_pln=SAMPLE_BUDGET_PLN,
        status="ACTIVE",
        is_selected=True,
    )
    svg = get_svg_icon("layers", size=20, color="#38bdf8")
    fallback_svg = get_svg_icon("unknown-icon", size=999)

    # Assert
    assert "backdrop-filter: blur" in css
    assert "glass-layer-1" in css
    assert "ocds-148610-niepolomice" in card
    assert "320 000 PLN" in card
    assert "glass-layer-3" in card
    assert "<svg" in svg
    assert 'width="20"' in fallback_svg


def test_should_format_short_ocds_id_and_highlight_domain_terms() -> None:
    # Arrange & Act
    short_id = format_short_ocds_id("ocds-148610-99c11721-d670-46ad-9d0d-e59e1d31ccbe")
    highlighted = highlight_domain_terms("Wymóg formatu .str w EWMAPA narusza art. 16 PZP [Załącznik SWZ].")
    section_html = render_insight_section_card(
        title="1. Zakres i przedmiot zamówienia",
        body="Modernizacja bazy BDOT500 o wartości 320 000,00 PLN.",
        icon_name="layers",
    )

    # Assert
    assert short_id == "ocds-148610-99c11721"
    assert "highlight-term" in highlighted
    assert "EWMAPA" in highlighted
    assert "1. Zakres i przedmiot zamówienia" in section_html
    assert "BDOT500" in section_html


def test_should_answer_template_questions_and_render_direct_answer_card(
    sample_swz_markdown: str,
) -> None:
    # Arrange & Act
    ans_penalty = TenderReportGenerator.answer_specific_question(
        RAG_QUESTION_TEMPLATES["2. Kary umowne za zwłokę i limit kar (art. 436 PZP)"],
        sample_swz_markdown,
    )
    ans_wadium = TenderReportGenerator.answer_specific_question(
        RAG_QUESTION_TEMPLATES["4. Wadium i zabezpieczenie należytego wykonania umowy"],
        sample_swz_markdown,
    )
    card_html = render_direct_answer_card(
        question="Jakie kary umowne przewidziano?",
        answer=ans_penalty,
        top_chunks=[{"section_title": "Rozdział III", "rerank_score": 0.96, "content": "Kary 2%"}],
    )

    # Assert
    assert len(RAG_QUESTION_TEMPLATES) >= MIN_TEMPLATE_COUNT
    assert "2%" in ans_penalty
    assert "9 000,00 PLN" in ans_wadium
    assert "Odpowiedź na zadane pytanie z dokumentacji SWZ / OPZ" in card_html
    assert "Rozdział III" in card_html


def test_should_render_dashboard_navigation_kpi_risk_and_table_components() -> None:
    # Arrange & Act
    sidebar_hdr = render_brand_sidebar_header()
    top_bar = render_top_utility_bar(
        municipality="Gmina Niepołomice",
        voivodeship="Małopolskie",
        ollama_ok=True,
        total_tenders=4,
        has_lockin=True,
    )
    kpi = render_kpi_stat_card(
        value="320 tys. PLN",
        label="Szacowany budżet",
        sublabel="Gmina Niepołomice",
        icon_name="wallet",
        color_hex="#3b82f6",
        ring_bg="rgba(59, 130, 246, 0.14)",
    )
    risk_panel = render_risk_profile_panel(has_lockin=True, has_penalties=True, faithfulness=1.0)
    table_html = render_procurements_table(
        rows=[
            {
                "ID": "ocds-148610-niepolomice",
                "Zamawiający": "Gmina Niepołomice",
                "Tytuł": "Modernizacja BDOT500",
                "Województwo": "Małopolskie",
                "Budżet PLN": SAMPLE_BUDGET_PLN,
            }
        ],
        selected_id="ocds-148610-niepolomice",
    )

    # Assert
    assert "GisMarket" in sidebar_hdr
    assert "Gmina Niepołomice" in top_bar
    assert "4 SWZ" in top_bar
    assert "320 tys. PLN" in kpi
    assert "Profil ryzyka SWZ" in risk_panel
    assert "Zindeksowane postępowania przetargowe" in table_html
    assert "Wybrane" in table_html


def test_should_extract_tender_metrics_and_parse_report_sections(
    sample_swz_markdown: str,
) -> None:
    # Arrange
    raw_report = (
        "### 1. Podsumowanie postępowania\n"
        "Przedmiotem zamówienia jest modernizacja bazy danych BDOT500 w gminie Niepołomice.\n\n"
        "### 2. Zidentyfikowane zastrzeżenia formalno-prawne\n"
        "Wymóg przekazania danych w zamkniętym formacie .str programu EWMAPA.\n\n"
        "### 3. Zestawienie rozwiązań konkurencyjnych\n"
        "Geobid Sp. z o.o. oraz Geo-System Sp. z o.o. posiadają wdrożone systemy.\n\n"
        "### 5. Rekomendacje dla zarządu\n"
        "Złożyć odwołanie do KIO w zakresie dopuszczenia formatu GML."
    )

    # Act
    metrics = extract_tender_metrics(sample_swz_markdown, budget_pln=SAMPLE_BUDGET_PLN)
    sections = parse_report_sections(raw_report)

    # Assert
    assert metrics["kio_level"] == "HIGH"
    assert metrics["has_lockin"] is True
    assert metrics["has_penalties"] is True
    assert metrics["wadium_str"] == "9 000,00 PLN"
    assert "BDOT500" in sections["summary"]
    assert ".str" in sections["legal_barriers"]
    assert "Geo-System" in sections["competitors"]
    assert "KIO" in sections["recommendations"]
