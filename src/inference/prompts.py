"""Strict grounding system prompts and tender analysis user story templates."""

from typing import Optional

STRICT_GROUNDING_SYSTEM_PROMPT = """
Jesteś analitykiem zamówień publicznych w branży geodezji, kartografii i systemów informacji przestrzennej (SIP).
Twoim zadaniem jest analiza Specyfikacji Warunków Zamówienia (SWZ) pod kątem wymagań formalnych, kryteriów oceny oraz potencjalnych barier konkurencyjnych.

Zasady generowania odpowiedzi:
1. Odpowiadaj wyłącznie na podstawie dostarczonych fragmentów dokumentacji SWZ.
2. Przy każdym przytoczonym fakcie, kwocie, terminie lub wymogu podaj źródło w formacie: [Załącznik, Strona, Rozdział].
3. Nie uzupełniaj brakujących informacji domysłami.
4. W przypadku braku danych w dostarczonym kontekście napisz wprost: "Brak informacji w dostarczonej dokumentacji przetargowej."
5. Używaj terminologii zgodnej z Prawem Zamówień Publicznych oraz Prawem geodezyjnym i kartograficznym.
""".strip()


def build_grounded_prompt(query: str, context: str) -> str:
    """Wraps query and retrieved context with strict grounding directives."""
    return f"""
Fragmenty dokumentacji przetargowej:
---------------------
{context}
---------------------
Instrukcje:
1. Odpowiadaj wyłącznie na podstawie powyższych fragmentów dokumentacji.
2. Przy każdym fakcie lub wymogu podaj dokładne źródło w formacie [Załącznik, Strona, Rozdział].
3. Jeżeli w dostarczonym kontekście brak odpowiedzi na zadane pytanie, Twoja odpowiedź MUSI brzmieć dokładnie: "Brak informacji w dostarczonej dokumentacji przetargowej."

Pytanie: {query}
Odpowiedź:
""".strip()


def build_vendor_lockin_prompt(context: str, municipality: str) -> str:
    """User Story 1: Vendor lock-in, proprietary format .str and discriminatory personnel requirement analysis."""
    return f"""
Kontekst przetargowy ({municipality}):
---------------------
{context}
---------------------
Zadanie analityczne (Analiza barier i Vendor Lock-in):
Przeanalizuj powyższe fragmenty pod kątem ograniczeń uczciwej konkurencji w gminie {municipality}.
1. Sprawdź, czy dokumentacja wymaga korzystania z zamkniętych formatów danych (w szczególności plików wsadowych .str środowiska EWMAPA lub bezpośredniej bazy OŚRODEK) bez dopuszczenia otwartego standardu GML.
2. Zweryfikuj warunki udziału pod kątem ograniczeń personelu (w tym potencjalnie dyskryminujących zakazów zatrudniania osób z orzeczoną niepełnosprawnością lub nadmiernych wymogów doświadczenia).
3. Dla każdego wymogu podaj numer strony, rozdziału i załącznika. Wskaż poziom ryzyka Vendor Lock-in (Wysoki / Średni / Niski).
""".strip()


def build_kio_appeal_prompt(context: str, kio_precedents: Optional[str] = None) -> str:
    """User Story 2: Legal appeal drafting under art. 16 and art. 99 ust. 4 PZP based on KIO precedents."""
    precedents_section = kio_precedents or "Precedensy KIO: wyroki KIO 1592/24, KIO 2944/21 dotyczące zakazu narzucania formatów zamkniętych."
    return f"""
Kontekst SWZ:
---------------------
{context}
---------------------
Baza orzecznictwa:
{precedents_section}
---------------------
Zadanie:
Na podstawie art. 16 i art. 99 ust. 4 PZP oraz orzecznictwa KIO przygotuj projekt wniosku o zmianę treści SWZ.
Uzasadnij konieczność wykreślenia wymogu plików .str i dopuszczenie otwartego standardu GML zgodnego z przepisami rozporządzenia w sprawie baz BDOT500 i GESUT.
Wskaż konkretne akapity z dokumentacji, których dotyczy modyfikacja.
""".strip()


def build_competitor_matrix_prompt(context: str, competitor_profiles: Optional[str] = None) -> str:
    """User Story 3: Evaluation criteria analysis and competitor positioning (Geo-System, GIAP)."""
    profiles = competitor_profiles or "Profile: Geo-System (e-mapa, integracja e-mapa.net), GIAP (portale miejskie, portale 3D)."
    return f"""
Tabela kryteriów oceny ofert i wymagań funkcjonalnych:
---------------------
{context}
---------------------
Profile rynkowe konkurencji:
{profiles}
---------------------
Zadanie:
Przeanalizuj kryteria oceny ofert pod kątem przewag rynkowych.
1. Zestaw punktowane wymagania z możliwościami rozwiązań Geo-System oraz GIAP.
2. Wskaż kryteria pozacenowe (np. moduły partycypacji, ankiety przestrzenne, obsługa rejestru urbanistycznego), które decydują o przewadze punktowej.
3. Podaj cytowania z tabeli oceny ofert dla każdego punktowanego elementu.
""".strip()


def build_historical_risk_prompt(context: str, voivodeship: str) -> str:
    """User Story 4: Historical pricing and timeline benchmarking."""
    return f"""
Dane postępowania ({voivodeship}):
---------------------
{context}
---------------------
Zadanie:
Porównaj warunki aktualnego postępowania w województwie {voivodeship} ze średnimi stawkami rynkowymi za modernizację baz BDOT500/GESUT (średnia referencyjna: ~350 PLN/ha brutto).
1. Oceń, czy założony budżet i termin realizacji nie stwarzają ryzyka rażąco niskiej ceny lub nierealności harmonogramu.
2. Wskaż rozbieżności względem standardowych terminów rynkowych w regionie.
""".strip()
