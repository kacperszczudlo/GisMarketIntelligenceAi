"""Domain-aware query expansion for mapping colloquial/vague questions to formal SWZ/PZP/GIS terminology."""

from typing import List, Tuple

_INTENT_EXPANSIONS: List[Tuple[Tuple[str, ...], str]] = [
    (
        ("haczyk", "ryzyk", "pułapk", "pulapk", "uważać", "uwazac", "problem", "barier", "podejrzan", "nieuczciw", "lock"),
        "vendor lock-in format .str EWMAPA OŚRODEK ograniczenie konkurencji kary umowne wykluczenie",
    ),
    (
        ("punkt", "ocen", "kryteri", "jakość", "jakosc", "wygrać", "wygrac", "przewag", "konkurenc"),
        "kryteria oceny ofert waga punktowa cena gwarancja rękojmia kryteria pozacenowe",
    ),
    (
        ("kas", "pieniądz", "pieniadz", "koszt", "cen", "budżet", "budzet", "wartoś", "wartos", "płac", "plac", "wadium"),
        "szacunkowa wartość zamówienia budżet brutto netto wadium zabezpieczenie należytego wykonania",
    ),
    (
        ("czas", "termin", "kiedy", "ile dni", "jak długo", "jak dlugo", "harmonogram", "opóźn", "opozn", "zwłok", "zwlok"),
        "termin wykonania zamówienia okres realizacji dni miesiące etapy harmonogram kary za zwłokę",
    ),
    (
        ("ludzi", "ekip", "zespół", "zespol", "osob", "osób", "pracown", "kogo", "kwalifik", "uprawnien", "doświadczen", "doswiadczen"),
        "warunki udziału zdolność zawodowa kierownik prac uprawnienia geodezyjne doświadczenie referencje",
    ),
    (
        ("system", "program", "oprogram", "format", "plik", "baz", "dane", "danych", "standard", "integrac"),
        "OPZ wymagania techniczne format GML .str BDOT500 GESUT EWMAPA e-mapa GIAP integracja",
    ),
    (
        ("ogóln", "ogoln", "podsum", "o czym", "o co", "co to za", "streszcz", "najważniej", "najwazniej"),
        "przedmiot zamówienia zakres BDOT500 GESUT wartość termin kryteria oceny warunki udziału",
    ),
]


def expand_swz_query(query: str) -> str:
    """Appends formal SWZ/PZP/GIS terms when a user query is colloquial, broad, or under-specified."""
    q_clean = query.strip()
    if not q_clean:
        return query

    q_lower = q_clean.lower()
    additions: List[str] = []
    for triggers, expansion in _INTENT_EXPANSIONS:
        if any(t in q_lower for t in triggers):
            additions.append(expansion)

    # If the question is very short/vague (<= 5 words) and matched no specific intent, add broad SWZ anchors
    if not additions and len(q_clean.split()) <= 5:
        additions.append("przedmiot zamówienia wymagania kryteria oceny warunki udziału termin kary")

    if not additions:
        return q_clean

    return f"{q_clean} {' '.join(additions)}"
