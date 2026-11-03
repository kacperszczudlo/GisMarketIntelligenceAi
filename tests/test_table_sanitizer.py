import pytest
from src.parsing.table_sanitizer import TableSanitizer


def test_table_sanitizer_removes_empty_rows():
    raw_md = (
        "| Kryterium | Waga |\n"
        "|---|---|\n"
        "|   |   |\n"
        "| Cena oferty brutto | 60% |\n"
        "| | |\n"
        "| Doświadczenie kierownika | 40% |\n"
    )
    sanitizer = TableSanitizer()
    cleaned = sanitizer.clean(raw_md)

    assert "|   |   |" not in cleaned
    assert "| | |" not in cleaned
    assert "| Cena oferty brutto | 60% |" in cleaned
    assert "| Doświadczenie kierownika | 40% |" in cleaned


def test_table_sanitizer_deduplicates_intermediate_separators():
    raw_md = (
        "| Lp. | Wymóg |\n"
        "|---|---|\n"
        "| 1 | Baza BDOT500 |\n"
        "|---|---|\n"
        "| 2 | Format GML |\n"
    )
    sanitizer = TableSanitizer()
    cleaned = sanitizer.clean(raw_md)

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    separator_count = sum(1 for line in lines if line.replace("-", "").replace("|", "").replace(":", "").strip() == "")
    assert separator_count == 1
    assert "| 1 | Baza BDOT500 |" in cleaned
    assert "| 2 | Format GML |" in cleaned


def test_table_sanitizer_normalizes_cell_whitespace():
    raw_md = (
        "|  Kluczowe wymagania   |   Termin realizacji   |\n"
        "|---|---|\n"
        "|   Aktualizacja GESUT   |    30 dni roboczych   |\n"
    )
    sanitizer = TableSanitizer()
    cleaned = sanitizer.clean(raw_md)

    assert "| Kluczowe wymagania | Termin realizacji |" in cleaned
    assert "| Aktualizacja GESUT | 30 dni roboczych |" in cleaned
