import pytest
from src.inference.prompts import (
    build_competitor_matrix_prompt,
    build_grounded_prompt,
    build_historical_risk_prompt,
    build_kio_appeal_prompt,
    build_vendor_lockin_prompt,
)


def test_build_grounded_prompt_contains_strict_directives():
    context = "Kierownik projektu: min. 3 lata doświadczenia."
    query = "Jakie doświadczenie musi mieć kierownik?"
    prompt = build_grounded_prompt(query, context)

    assert "Odpowiadaj wyłącznie na podstawie" in prompt
    assert "Brak informacji w dostarczonej dokumentacji przetargowej" in prompt
    assert "Kierownik projektu: min. 3 lata doświadczenia." in prompt
    assert "Jakie doświadczenie musi mieć kierownik?" in prompt


def test_vendor_lockin_prompt_contains_rules():
    p = build_vendor_lockin_prompt(
        context="Wymóg przekazania bazy w plikach .str do programu EWMAPA.",
        municipality="Gmina Niepołomice",
    )
    assert "Gmina Niepołomice" in p
    assert "Vendor Lock-in" in p or "barier" in p or "konkurencji" in p
    assert ".str" in p
    assert "EWMAPA" in p
    assert "numer strony" in p or "źródło" in p


def test_kio_appeal_prompt():
    p = build_kio_appeal_prompt(context="Zapis o plikach wsadowych .str.")
    assert "KIO" in p
    assert "art. 16" in p
    assert "art. 99 ust. 4" in p
    assert "GML" in p


def test_competitor_matrix_prompt():
    p = build_competitor_matrix_prompt(context="Punktacja za moduł ankiet przestrzennych.")
    assert "Geo-System" in p
    assert "GIAP" in p
    assert "kryteria oceny" in p or "kryteriów" in p


def test_historical_risk_prompt():
    p = build_historical_risk_prompt(context="Stawka 250 PLN/ha, termin 6 miesięcy.", voivodeship="Małopolskie")
    assert "Małopolskie" in p
    assert "budżet" in p or "stawek" in p or "termin" in p
