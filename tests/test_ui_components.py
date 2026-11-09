from src.ui.components import (
    get_glassmorphism_stylesheet,
    get_svg_icon,
    render_citation_box,
    render_competitor_matrix,
    render_kio_warning,
    render_red_flag_badge,
    render_tender_card,
)


def test_render_red_flag_badge_vendor_lockin():
    badge = render_red_flag_badge("vendor_lockin")
    assert "Vendor Lock-in" in badge
    assert "<svg" in badge
    assert "#e53e3e" in badge or "background-color" in badge


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
    card = render_tender_card(
        ocds_id="ocds-148610-niepolomice",
        title="Modernizacja BDOT500",
        municipality="Gmina Niepołomice",
        voivodeship="Małopolskie",
        budget_pln=320000.0,
        status="ACTIVE",
    )
    assert "ocds-148610-niepolomice" in card
    assert "Modernizacja BDOT500" in card
    assert "320 000 PLN" in card
    svg = get_svg_icon("layers", size=20, color="#38bdf8")
    assert "<svg" in svg
