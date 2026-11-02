# Konfiguracja silnika LLM: Ollama z modelem Llama-3.1-8B

## 1. Wybór modelu

Do generowania raportów i odpowiedzi wykorzystywany jest model Llama-3.1-8B-Instruct uruchamiany w środowisku Ollama.

### Parametry konfiguracyjne:
* **Format kwantyzacji**: Q4_K_M (4-bitowa kwantyzacja wag).
* **Zapotrzebowanie na pamięć**: około 4.7 GB RAM.
* **Wydajność na CPU**: od 8 do 15 tokenów na sekundę przy obsłudze instrukcji AVX2.
* **Prywatność**: Model działa lokalnie, bez transmisji danych poza infrastrukturę firmy.

---

## 2. Przygotowanie modelu w Ollama

### 2.1. Pobranie obrazu modelu
```bash
ollama pull llama3.1:8b-instruct-q4_K_M
ollama list
```

### 2.2. Plik Modelfile z promptem uziemiającym

```dockerfile
FROM llama3.1:8b-instruct-q4_K_M

PARAMETER temperature 0.0
PARAMETER top_p 0.9
PARAMETER num_ctx 8192

SYSTEM """
Jesteś analitykiem zamówień publicznych w branży geodezji, kartografii i systemów informacji przestrzennej (SIP).
Twoim zadaniem jest analiza Specyfikacji Warunków Zamówienia (SWZ) pod kątem wymagań formalnych, kryteriów oceny oraz potencjalnych barier konkurencyjnych.

Zasady generowania odpowiedzi:
1. Odpowiadaj wyłącznie na podstawie dostarczonych fragmentów dokumentacji SWZ.
2. Przy każdym przytoczonym fakcie, kwocie, terminie lub wymogu podaj źródło w formacie: [Załącznik, Strona, Rozdział].
3. Nie uzupełniaj brakujących informacji domysłami.
4. W przypadku braku danych w dostarczonym kontekście napisz wprost: "Brak informacji w dostarczonej dokumentacji przetargowej."
5. Używaj terminologii zgodnej z Prawem Zamówień Publicznych oraz Prawem geodezyjnym i kartograficznym.
"""
```

Tworzenie dedykowanego modelu:
```bash
ollama create gis-analyst -f Modelfile
```

---

## 3. Integracja z LlamaIndex

```python
from llama_index.core import PromptTemplate
from llama_index.llms.ollama import Ollama

llm = Ollama(
    model="gis-analyst",
    request_timeout=300.0,
    temperature=0.0,
    additional_kwargs={"num_ctx": 8192},
)

QA_PROMPT_TEMPLATE = PromptTemplate(
    "Fragmenty dokumentacji przetargowej:\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Na podstawie powyższych informacji odpowiedz na pytanie:\n"
    "Pytanie: {query_str}\n"
    "Odpowiedź ze wskazaniem stron i załączników:"
)
```

---

## 4. Opcjonalne przełączenie na zewnętrzne API

W przypadku przetwarzania wsadowego dużych pakietów dokumentacji istnieje możliwość przełączenia potoku na darmowe plany chmurowe:
* **Google Gemini API**: darmowy dostęp w ramach określonych limitów minutowych z dużym oknem kontekstowym.
* **Groq API**: darmowy plan dla modeli Llama 3 o wysokiej prędkości generowania tokenów.
