"""Strict grounding system prompts and tender analysis user story templates."""

from typing import Dict, List, Optional

CONVERSATIONAL_SWZ_SYSTEM_PROMPT = """
Jesteś starszym analitykiem zamówień publicznych w branży geodezji, kartografii i systemów informacji przestrzennej (SIP).
Rozmawiasz z użytkownikiem o konkretnej dokumentacji przetargowej (SWZ / OPZ).

Zasady:
1. Opieraj się wyłącznie na dostarczonych fragmentach dokumentacji SWZ/OPZ — nie zmyślaj kwot, dat, wymogów ani sygnatur.
2. Jeśli pytanie jest ogólne, potoczne lub nieprecyzyjne (np. "czy są haczyki?", "na co uważać?", "o co tu chodzi?"), NIE odpowiadaj od razu "Brak informacji", lecz podsumuj najistotniejsze powiązane fakty, ryzyka lub wymagania widoczne w dostarczonych fragmentach i wskaż, co warto doprecyzować.
3. Traktuj bieżące pytanie jako główne — odwołuj się do poprzedniej wymiany zdań tylko wtedy, gdy bieżące pytanie wyraźnie do niej nawiązuje (np. "a ile?", "a co z terminem?").
4. Stosuj poprawne rozwinięcia skrótów: KIO = Krajowa Izba Odwoławcza, PZP = Prawo zamówień publicznych, SWZ = Specyfikacja Warunków Zamówienia, OPZ = Opis Przedmiotu Zamówienia. Nigdy nie wymyślaj innych rozwinięć skrótu KIO.
5. Rozróżniaj warunki udziału w postępowaniu (oceniane zero-jedynkowo: spełnia/nie spełnia, np. doświadczenie firmy, uprawnienia kierownika) od kryteriów oceny ofert (punktowanych procentowo, np. cena, gwarancja/rękojmia).
6. Podawaj źródła w nawiasach kwadratowych, jeśli są widoczne w tekście (np. [SWZ, Rozdział IV]).
7. Dopiero gdy dostarczone fragmenty w ogóle nie zawierają żadnych informacji związanych z pytaniem, napisz wprost czego brakuje w dokumentacji.
8. Pisz naturalnie, konkretnie i zrozumiale po polsku, używając poprawnej terminologii PZP i geodezyjnej.
""".strip()


def build_chat_prompt(
    question: str,
    context: str,
    response_format: str = "Standard (SWZ)",
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Builds an interactive Q&A prompt with format guidance and optional conversation history."""
    format_hint = {
        "Zwięzły (Punkty)": "Odpowiedz zwięźle w krótkich, czytelnych punktach.",
        "Audyt PZP / KIO": "Oceń zapisy pod kątem zgodności z PZP, barier konkurencyjnych i ryzyka KIO.",
    }.get(response_format, "Odpowiedz rzeczowo i przystępnie na podstawie dokumentacji SWZ.")

    history_block = ""
    if history:
        recent = history[-4:]
        lines = []
        for msg in recent:
            role_label = "Użytkownik" if msg.get("role") == "user" else "Analityk"
            content = (msg.get("content") or "").strip()
            if content:
                lines.append(f"{role_label}: {content[:500]}")
        if lines:
            history_block = "Poprzednia wymiana zdań:\n" + "\n".join(lines) + "\n\n"

    return (
        f"{format_hint}\n\n"
        f"{history_block}"
        f"Pytanie użytkownika: {question}\n\n"
        f"Fragmenty dokumentacji SWZ/OPZ:\n"
        f"---------------------\n"
        f"{context}\n"
        f"---------------------\n"
        f"Odpowiedź:"
    )

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


def build_universal_report_prompt(context: str, title: str, municipality: str) -> str:
    """Builds a domain-agnostic PZP audit report prompt grounded in the actual tender context."""
    return f"""
Zamawiający: {municipality}
Przedmiot zamówienia: {title}

Fragmenty dokumentacji (SWZ / OPZ / Ogłoszenie BZP):
---------------------
{context}
---------------------
Przygotuj zwięzły raport analityczny w języku polskim dokładnie w poniższej strukturze 5 nagłówków Markdown (nie wymyślaj wymagań GIS ani formatu .str, jeśli nie występują w powyższym tekście):

### 1. Podsumowanie postępowania
Opisz krótko przedmiot zamówienia, budżet/wartość, termin realizacji i tryb postępowania.

### 2. Zidentyfikowane zastrzeżenia formalno-prawne
Wskaż kryteria oceny ofert, warunki udziału, wadium, kary umowne lub ewentualne bariery konkurencyjne (np. wymogi jednego producenta, brak limitu kar, wysokie progi).

### 3. Zestawienie rozwiązań konkurencyjnych
Wymień wymagane systemy, standardy, certyfikaty lub przedmiotowe środki dowodowe (jeśli brak danych o konkretnych dostawcach, napisz to wprost).

### 4. Źródła danych
Wypisz w punktach wyłącznie sekcje/rozdziały widoczne w dostarczonym tekście.

### 5. Rekomendacje dla zarządu
Podaj 2-3 praktyczne wnioski (na co zwrócić uwagę przed złożeniem oferty lub czy są podstawy do pytań do SWZ / odwołania do KIO).
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
