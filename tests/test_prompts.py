from src.inference.prompts import (
    STRICT_GROUNDING_SYSTEM_PROMPT,
    build_competitor_matrix_prompt,
    build_grounded_prompt,
    build_historical_risk_prompt,
    build_kio_appeal_prompt,
    build_vendor_lockin_prompt,
)


def test_should_include_strict_grounding_rules_in_system_prompt() -> None:
    # Arrange & Act
    system_prompt = STRICT_GROUNDING_SYSTEM_PROMPT

    # Assert
    assert "Odpowiadaj wyłącznie na podstawie" in system_prompt
    assert "[Załącznik, Strona, Rozdział]" in system_prompt
    assert "Brak informacji w dostarczonej dokumentacji przetargowej." in system_prompt


def test_should_build_grounded_prompt_with_context_and_refusal_directive() -> None:
    # Arrange
    context = "Kierownik projektu: min. 3 lata doświadczenia."
    query = "Jakie doświadczenie musi mieć kierownik?"

    # Act
    prompt = build_grounded_prompt(query=query, context=context)

    # Assert
    assert "Odpowiadaj wyłącznie na podstawie" in prompt
    assert "Brak informacji w dostarczonej dokumentacji przetargowej." in prompt
    assert context in prompt
    assert query in prompt


def test_should_build_vendor_lockin_prompt_targeting_proprietary_formats() -> None:
    # Arrange
    context = "Wymóg przekazania bazy w plikach .str do programu EWMAPA."
    municipality = "Gmina Niepołomice"

    # Act
    prompt = build_vendor_lockin_prompt(context=context, municipality=municipality)

    # Assert
    assert municipality in prompt
    assert "Vendor Lock-in" in prompt
    assert ".str" in prompt
    assert "EWMAPA" in prompt
    assert "GML" in prompt


def test_should_build_kio_appeal_prompt_with_default_and_custom_precedents() -> None:
    # Arrange
    context = "Zapis o plikach wsadowych .str."
    custom_precedent = "Wyrok KIO 999/25 dotyczący interoperacyjności GML."

    # Act
    default_prompt = build_kio_appeal_prompt(context=context)
    custom_prompt = build_kio_appeal_prompt(context=context, kio_precedents=custom_precedent)

    # Assert
    assert "art. 16" in default_prompt
    assert "art. 99 ust. 4" in default_prompt
    assert "KIO 1592/24" in default_prompt
    assert custom_precedent in custom_prompt


def test_should_build_competitor_matrix_prompt_with_market_profiles() -> None:
    # Arrange
    context = "Punktacja za moduł ankiet przestrzennych."

    # Act
    prompt = build_competitor_matrix_prompt(context=context)

    # Assert
    assert "Geo-System" in prompt
    assert "GIAP" in prompt
    assert context in prompt


def test_should_build_historical_risk_prompt_with_voivodeship_benchmark() -> None:
    # Arrange
    context = "Stawka 250 PLN/ha, termin 6 miesięcy."
    voivodeship = "Małopolskie"

    # Act
    prompt = build_historical_risk_prompt(context=context, voivodeship=voivodeship)

    # Assert
    assert voivodeship in prompt
    assert "350 PLN/ha" in prompt
    assert context in prompt
