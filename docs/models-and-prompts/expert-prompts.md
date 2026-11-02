# Szablony zapytań analitycznych i format raportu przetargowego

## 1. Zastosowanie zapytań analitycznych

System obsługuje zapytania analityków ds. przetargów oraz radców prawnych przygotowujących oferty i środki ochrony prawnej.

Poniżej zestawiono 4 scenariusze zapytań oraz format wynikowy raportu przetargowego.

---

## 2. Szablony zapytań (User Stories)

### Scenariusz 1: Weryfikacja barier technologicznych i formalnych
* **Cel**: Wykrycie zapisów faworyzujących dotychczasowego dostawcę oprogramowania oraz nieuzasadnionych ograniczeń kadrowych.
* **Treść zapytania**:
```text
Przeanalizuj załączniki techniczne oraz SWZ przetargu z gminy [Nazwa Gminy] pod kątem ograniczeń uczciwej konkurencji.

Sprawdź, czy dokumentacja wymaga korzystania z zamkniętych formatów danych, w szczególności plików wsadowych .str środowiska EWMAPA lub bezpośredniej integracji z bazą OŚRODEK bez dopuszczenia standardu GML.

Zweryfikuj sekcję warunków udziału pod kątem ograniczeń dotyczących personelu, w tym zakazu zatrudniania osób z orzeczoną niepełnosprawnością.

Dla każdego zidentyfikowanego wymogu podaj numer strony, rozdziału i załącznika.
```

---

### Scenariusz 2: Przygotowanie wniosku o modyfikację SWZ na podstawie KIO
* **Cel**: Sformułowanie argumentacji prawnej do wniosku o zmianę treści SWZ.
* **Treść zapytania**:
```text
Wyszukaj w bazie orzeczeń Krajowej Izby Odwoławczej wyroki dotyczące naruszenia zasady konkurencyjności poprzez narzucenie formatów zamkniętych (np. KIO 1592/24, KIO 2944/21).

Na podstawie art. 16 i art. 99 ust. 4 PZP przygotuj projekt wniosku do zamawiającego o wykreślenie wymogu plików .str i dopuszczenie otwartego standardu GML zgodnego z przepisami rozporządzenia w sprawie BDOT500 i GESUT.
```

---

### Scenariusz 3: Analiza kryteriów oceny ofert
* **Cel**: Identyfikacja kryteriów pozacenowych i zestawienie ich z możliwościami systemów konkurencyjnych.
* **Treść zapytania**:
```text
Przeanalizuj tabelę kryteriów oceny ofert z nowego postępowania.

Porównaj wymagane funkcjonalności z profilami rozwiązań Geo-System (e-mapa) oraz GIAP.

Wskaż funkcjonalności (np. moduły partycypacji społecznej, ankiety przestrzenne, obsługa rejestru urbanistycznego), które stanowią kryteria punktowane i mogą zadecydować o przewadze punktowej naszej oferty.
```

---

### Scenariusz 4: Porównanie stawek i terminów z danymi historycznymi
* **Cel**: Weryfikacja ryzyka rażąco niskiej ceny oraz realności terminów realizacji.
* **Treść zapytania**:
```text
Wyszukaj w bazie trzy zakończone postępowania z województwa [Nazwa Województwa] z ostatnich dwóch lat dotyczące modernizacji baz BDOT500 i GESUT.

Zestaw średni koszt prac w przeliczeniu na 1 hektar oraz czas realizacji, a następnie porównaj te wartości z warunkami aktualnego postępowania OCDS-[Identyfikator].

Wskaż, czy założony przez zamawiającego budżet lub termin odbiega od średnich stawek rynkowych w regionie.
```

---

## 3. Format wyjściowy raportu przetargowego

```markdown
# Raport przetargowy: OCDS-987654-2026
**Zamawiający:** Urząd Miasta i Gminy Niepołomice  
**Przedmiot zamówienia:** Utworzenie bazy BDOT500/GESUT oraz portalu SIP  
**Weryfikacja jakościowa:** Zgodność potwierdzona (RAGAS Faithfulness: 0.98)

---

### 1. Podsumowanie postępowania
* **Zakres prac:** Digitalizacja rejestrów, transformacja układu 1965 do PL-2000 (strefa 7), inwentaryzacja sieci GESUT dla 1200 ha.
* **Szacunkowy budżet:** ~420 000 PLN brutto (średnia w regionie: ~350 PLN/ha).
* **Termin na pytania do SWZ:** 5 dni roboczych.

---

### 2. Zidentyfikowane zastrzeżenia formalno-prawne

#### Zastrzeżenie 1: Wymóg zamkniętego formatu danych
* **Lokalizacja:** Załącznik nr 2 (OPZ), strona 14, tabela wymagań.
* **Cytat:** "Wykonawca przekaże bazę BDOT500 w plikach o strukturze wsadowej .str importowalnych do programu EWMAPA."
* **Kwalifikacja prawna:** Naruszenie art. 16 i art. 99 ust. 4 PZP.
* **Rekomendowane działanie:** Wniosek o zmianę SWZ z przywołaniem wyroków KIO 1592/24 oraz KIO 2944/21.

#### Zastrzeżenie 2: Asymetria kar umownych
* **Lokalizacja:** Wzór umowy (Załącznik nr 5), § 11 ust. 2, strona 8.
* **Opis:** Kara umowna 0.5% wartości zamówienia za każdy dzień zwłoki wykonawcy przy braku terminu odbioru po stronie urzędu.

---

### 3. Zestawienie rozwiązań konkurencyjnych

| Dostawca | Prawdopodobieństwo startu | Silne strony oferty | Obszary do zakwestionowania |
| :--- | :--- | :--- | :--- |
| Geo-System (e-mapa) | Wysokie | Powszechność w powiecie, integracja z e-mapa.net | Mniejsza liczba dedykowanych modułów partycypacji społecznej |
| GIAP Sp. z o.o. | Średnie | Doświadczenie w portalach miejskich | Zależność od wydajności środowisk 3D |

---

### 4. Źródła danych
* `Zalacznik_2_OPZ.pdf` (Parent ID: `f5a4c9...`, strona 14).
* `Wzor_Umowy.pdf` (Parent ID: `b7e2d1...`, strona 8).
* `Orzecznictwo_KIO.txt` (Wyrok KIO 1592/24).
```
