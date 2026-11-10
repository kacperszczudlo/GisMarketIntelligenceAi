import pytest
from src.parsing.table_sanitizer import TableSanitizer

EXPECTED_SINGLE_SEPARATOR_COUNT = 1


def test_should_remove_empty_table_rows_while_preserving_valid_cells() -> None:
    # Arrange
    raw_md = (
        "| Kryterium | Waga |\n"
        "|---|---|\n"
        "|   |   |\n"
        "| Cena oferty brutto | 60% |\n"
        "| | |\n"
        "| Doświadczenie kierownika | 40% |\n"
    )
    sanitizer = TableSanitizer()

    # Act
    cleaned = sanitizer.clean(raw_md)

    # Assert
    assert "|   |   |" not in cleaned
    assert "| | |" not in cleaned
    assert "| Cena oferty brutto | 60% |" in cleaned
    assert "| Doświadczenie kierownika | 40% |" in cleaned


def test_should_deduplicate_repeated_intermediate_header_separators() -> None:
    # Arrange
    raw_md = (
        "| Lp. | Wymóg |\n"
        "|---|---|\n"
        "| 1 | Baza BDOT500 |\n"
        "|---|---|\n"
        "| 2 | Format GML |\n"
        "|:---:|:---:|\n"
        "| 3 | Układ PL-2000 |\n"
    )
    sanitizer = TableSanitizer()

    # Act
    cleaned = sanitizer.clean(raw_md)

    # Assert
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    separator_count = sum(1 for line in lines if TableSanitizer._is_separator_row(line))
    assert separator_count == EXPECTED_SINGLE_SEPARATOR_COUNT
    assert "| 1 | Baza BDOT500 |" in cleaned
    assert "| 2 | Format GML |" in cleaned
    assert "| 3 | Układ PL-2000 |" in cleaned


def test_should_drop_stray_separator_appearing_before_any_table_header() -> None:
    # Arrange
    raw_md = (
        "Wstęp do rozdziału\n"
        "|---|---|\n"
        "Akapit tekstu poza tabelą.\n"
    )
    sanitizer = TableSanitizer()

    # Act
    cleaned = sanitizer.clean(raw_md)

    # Assert
    assert "|---|" not in cleaned
    assert "Wstęp do rozdziału" in cleaned
    assert "Akapit tekstu poza tabelą." in cleaned


def test_should_normalize_excessive_whitespace_inside_table_cells() -> None:
    # Arrange
    raw_md = (
        "|  Kluczowe wymagania   |   Termin realizacji   |\n"
        "|---|---|\n"
        "|   Aktualizacja GESUT   |    30 dni roboczych   |\n"
    )
    sanitizer = TableSanitizer()

    # Act
    cleaned = sanitizer.clean(raw_md)

    # Assert
    assert "| Kluczowe wymagania | Termin realizacji |" in cleaned
    assert "| Aktualizacja GESUT | 30 dni roboczych |" in cleaned


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("|---|---|", True),
        ("|:---|---:|", True),
        ("| :---: | :---: |", True),
        ("| Kryterium | Waga |", False),
        ("Zwykły tekst", False),
    ],
    ids=["plain_sep", "aligned_sep", "centered_sep", "data_row", "plain_text"],
)
def test_should_correctly_classify_markdown_table_separator_rows(
    line: str,
    expected: bool,
) -> None:
    # Arrange & Act
    is_sep = TableSanitizer._is_separator_row(line)

    # Assert
    assert is_sep is expected
