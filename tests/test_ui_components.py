from src.ui.components import (
    format_short_ocds_id,
    get_glassmorphism_stylesheet,
    get_svg_icon,
    highlight_domain_terms,
    render_citation_box,
    render_competitor_matrix,
    render_insight_section_card,
    render_kio_warning,
    render_red_flag_badge,
    render_tender_card,
)


def test_render_red_flag_badge_vendor_lockin():
    badge = render_red_flag_badge("vendor_lockin")
    assert "Vendor Lock-in" in badge
    assert "<svg" in badge
    assert "background-color" in badge


def test_render_red_flag_badge_asymetria_kar():
    badge = render_red_flag_badge("asymetria_kar")
    assert "Asymetria" in badge or "kar" in badge
    assert "<svg" in badge


def test_render_citation_box():
    box = render_citation_box("SWZ Rozdział II, s. 14")
    assert "SWZ Rozdział II, s. 14" in box
    assert "<svg" in box
    assert "źródło" in box.lower() or "dowod" in box.lower()


def test_render_competitor_matrix():
    competitors = [
        {"name": "Geo-System Sp. z o.o.", "product": "iMPA / e-Gmina", "advantage": "Zainstalowana baza w gminie"},
        {"name": "Systherm Info", "product": "GEO-INFO", "advantage": "Wymóg zgodności z formatem .giv"},
    ]
    html = render_competitor_matrix(competitors)
    assert "Geo-System" in html
    assert "Systherm Info" in html
    assert "iMPA" in html


def test_render_kio_warning():
    warning = render_kio_warning("HIGH")
    assert "Ryzyko odwołania do KIO" in warning
    assert "WYSOKIE" in warning.upper()
    assert "<svg" in warning


def test_render_tender_card_and_glass_styles():
    css = get_glassmorphism_stylesheet()
    assert "backdrop-filter: blur" in css
    assert "glass-layer-1" in css
    assert "glass-layer-2" in css
    assert "glass-layer-3" in css

    card = render_tender_card(
        ocds_id="ocds-148610-niepolomice",
        title="Modernizacja BDOT500",
        municipality="Gmina Niepołomice",
        voivodeship="Małopolskie",
        budget_pln=320000.0,
        status="ACTIVE",
        is_selected=True,
    )
    assert "ocds-148610-niepolomice" in card
    assert "Modernizacja BDOT500" in card
    assert "320 000 PLN" in card
    assert "glass-layer-3" in card
    svg = get_svg_icon("layers", size=20, color="#38bdf8")
    assert "<svg" in svg


def test_render_insight_section_card_and_short_id():
    short_id = format_short_ocds_id("ocds-148610-99c11721-d670-46ad-9d0d-e59e1d31ccbe")
    assert short_id == "ocds-148610-99c11721"

    highlighted = highlight_domain_terms("Wymóg formatu .str w EWMAPA narusza art. 16 PZP [Załącznik SWZ].")
    assert "highlight-term" in highlighted
    assert "EWMAPA" in highlighted

    section_html = render_insight_section_card(
        title="1. Zakres i przedmiot zamówienia",
        body="Modernizacja bazy BDOT500 o wartości 320 000,00 PLN.",
        icon_name="layers",
    )
    assert "1. Zakres i przedmiot zamówienia" in section_html
    assert "BDOT500" in section_html
