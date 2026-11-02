# Scenariusze testowe i weryfikacja poprawności

## 1. Zakres testów

Specyfikacje warunków zamówienia charakteryzują się nieregularną strukturą (skany dokumentów papierowych, tabele bez wyraźnych linii podziału). Poniższe scenariusze sprawdzają odporność potoku na typowe błędy ekstrakcji i wyszukiwania.

---

## 2. Scenariusze testowe

### TC-01: Ekstrakcja wielostronicowej tabeli kryteriów oceny ofert
* **Opis**: Tabela kryteriów rozpoczyna się na stronie 18 i kończy na stronie 20 dokumentu SWZ.
* **Cel**: Sprawdzenie, czy model TableFormer połączył części tabeli i zachował spójność wierszy z nagłówkami kolumn.
* **Kryterium akceptacji**:
  * Wszystkie wiersze z podkryteriami gwarancji i kar umownych zostały wyekstrahowane.
  * Tabela została poprawnie sformatowana w składni Markdown.
  * Wskaźnik Context Recall w RAGAS wynosi co najmniej 0.95.

---

### TC-02: Wyszukiwanie w tekście o obniżonej jakości OCR
* **Opis**: Skan załącznika technicznego w rozdzielczości 150 DPI z częściowo uszkodzonymi znakami diakrytycznymi (np. "zamowienie" zamiast "zamówienie").
* **Cel**: Weryfikacja, czy model BGE-M3 powiąże zniekształcony fragment z pytaniem zapisanym poprawną polszczyzną.
* **Kryterium akceptacji**:
  * Podobieństwo kosinusowe dla fragmentu wynosi minimum 0.72.
  * Fragment trafia do puli pierwszych 20 wyników przed rerankingiem.

---

### TC-03: Wyszukiwanie dokładnych identyfikatorów i sygnatur
* **Opis**: Zapytanie o rozszerzenie pliku `ewmapa.str` lub sygnaturę `KIO 1592/24`.
* **Cel**: Sprawdzenie skuteczności wyszukiwania rzadkiego (BM25) w kompensowaniu ograniczeń wyszukiwania semantycznego.
* **Kryterium akceptacji**:
  * Wyszukiwanie wektorowe gęste plasuje dokument na dalszej pozycji ze względu na rzadkość tokenu.
  * Wyszukiwanie leksykalne umieszcza dokument na pierwszej pozycji.
  * Fuzja RRF wynosi dokument do pierwszych 3 pozycji przekazywanych do Cross-Encodera.

---

### TC-04: Test uziemienia promptu i braku halucynacji
* **Opis**: Pytanie o nieistniejący w SWZ wymóg (np. "Czy wymagana jest licencja pilota drona kategorii NSTS-01?").
* **Cel**: Weryfikacja, czy model nie wygeneruje odpowiedzi twierdzącej w oparciu o wiedzę ogólną.
* **Kryterium akceptacji**:
  * Model odpowiada: "Brak informacji w dostarczonej dokumentacji przetargowej."
  * Wskaźnik Faithfulness wynosi 1.00.

---

### TC-05: Rozwiązanie kontekstu węzła nadrzędnego (Parent-Child)
* **Opis**: Dopasowanie zapytania do krótkiego fragmentu w węźle podrzędnym: "...w terminie 3 dni roboczych od dnia wezwania...".
* **Cel**: Sprawdzenie, czy potok pobierze z bazy danych cały rozdział SWZ wyjaśniający okoliczności wezwania.
* **Kryterium akceptacji**:
  * Do promptu modelu wstrzykiwana jest pełna treść rozdziału nadrzędnego.
