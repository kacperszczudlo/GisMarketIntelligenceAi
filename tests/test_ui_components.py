import pytest
from src.ui.components import (
    render_citation_box,
    render_competitor_matrix,
    render_kio_warning,
    render_red_flag_badge,
)


def test_render_red_flag_badge_vendor_lockin():
    badge = render_red_flag_badge("vendor_lockin")
    assert "Vendor Lock-in" in badge
    assert "#e53e3e" in badge or "background-color" in badge or "badge" in badge.lower()


def test_render_red_flag_badge_asymetria_kar():
    badge = render_red_flag_badge("asymetria_kar")
    assert "Kary umowne" in badge or "Asymetria" in badge


def test_render_citation_box():
    box = render_citation_box("SWZ Rozdział II, s. 14")
    assert "SWZ Rozdział II, s. 14" in box
    assert "dowód" in box.lower() or "źródło" in box.lower() or "cytat" in box.lower()


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
