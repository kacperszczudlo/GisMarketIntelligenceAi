# GisMarketIntelligenceAi

Lokalny system RAG do analizy specyfikacji warunków zamówienia (SWZ), weryfikacji barier rynkowych i analizy konkurencji w polskich przetargach geodezyjnych oraz systemach informacji przestrzennej (SIP).

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61DAFB.svg)](https://react.dev/)
[![Vector DB](https://img.shields.io/badge/Vector_DB-PostgreSQL_%2B_pgvector-blue.svg)](https://github.com/pgvector/pgvector)
[![LLM Engine](https://img.shields.io/badge/LLM_Engine-Ollama_%28gis--analyst%29-black.svg)](https://ollama.com/)
[![Evaluation](https://img.shields.io/badge/Evaluation-RAGAS-green.svg)](https://github.com/explodinggradients/ragas)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Cel projektu

Dokumentacja przetargowa (SWZ i OPZ) w administracji samorządowej w obszarze geodezji i systemów informacji przestrzennej zawiera:
* Macierze punktacji i kryteria oceny ofert,
* Wymagania techniczne dotyczące baz BDOT500 oraz GESUT,
* Wymogi transformacji danych między układami współrzędnych (np. układ 1965 do PL-2000),
* Zapisy ograniczające konkurencję (vendor lock-in na rzecz dostawców takich jak Geo-System, GIAP, Geobid).

System automatyzuje ekstrakcję danych z wielostronicowych plików PDF, indeksuje treść z zachowaniem kontekstu tabel i generuje raporty techniczno-prawne dla zespołów przetargowych.

---

## Architektura systemu

Potok przetwarzania wykorzystuje dwuetapowe wyszukiwanie oraz hierarchiczny podział tekstu:

```mermaid
flowchart TD
    subgraph Ingestion [Ingestion i parsowanie]
        A[Pliki PDF z e-Zamowienia] --> B[IBM Docling Parser]
        B --> C[Markdown ze strukturą tabel]
        C --> D[Podział Parent-Child]
    end

    subgraph Storage [Baza danych]
        D --> E[(PostgreSQL: metadane i węzły nadrzędne)]
        D --> F[Model BGE-M3]
        F --> G[(PostgreSQL pgvector: wektory węzłów podrzędnych)]
    end

    subgraph Retrieval [Wyszukiwanie hybrydowe i reranking]
        H[Zapytanie użytkownika] --> I[Wyszukiwanie wektorowe gęste]
        H --> J[Wyszukiwanie leksykalne BM25]
        I --> K[Fuzja RRF k=60]
        J --> K
        K --> L[Cross-Encoder bge-reranker-v2-m3]
        L --> M[Pobranie węzła nadrzędnego Parent]
        M --> N[Przeindeksowanie kontekstu]
    end

    subgraph Generation [Generowanie, ewaluacja i aplikacja webowa]
        N --> O[Ollama: gis-analyst]
        O --> P[Raport przetargowy i eksport PDF]
        P --> Q[Ewaluacja RAGAS: wierność >= 0.95]
        Q --> R[FastAPI REST + SSE Streaming]
        R --> S[React 18 + Vite SPA]
    end
```

---

## Komponenty technologiczne

| Warstwa | Technologia | Zastosowanie |
| :--- | :--- | :--- |
| Backend API | FastAPI + Uvicorn (ASGI) | REST API (`/api/*`), streaming odpowiedzi czatu (SSE), serwowanie SPA oraz eksport PDF. |
| Frontend UI | React 18 + Vite | Szybka aplikacja SPA (Cartographic Daylight UI), lokalny cache przetargów i historia czatu. |
| Bezpieczeństwo | Argon2id + HMAC-SHA256 | Haszowanie haseł użytkowników, zarządzanie kontami pracowników i bezstanowe tokeny sesji. |
| Parsowanie PDF | IBM Docling | Ekstrakcja tabel wielostronicowych do formatu Markdown z wykorzystaniem modeli DocLayNet i TableFormer. |
| Baza danych | PostgreSQL 16 z rozszerzeniem pgvector | Przechowywanie relacyjnych metadanych postępowań, kont użytkowników oraz indeksów wektorowych HNSW. |
| Model embeddingu | BAAI/BGE-M3 | Generowanie wektorów gęstych (1024 wymiary) i rzadkich (wagi leksykalne). |
| Reranking | bge-reranker-v2-m3 | Cross-encoder filtrujący kandydatów do wąskiego kontekstu dla modelu LLM. |
| Model językowy | Ollama (`gis-analyst`) | Generowanie raportów, ustrukturyzowanych metryk JSON oraz strumieniowych odpowiedzi z uziemieniem w SWZ. |
| Ewaluacja | RAGAS | Weryfikacja wskaźników wierności faktograficznej (faithfulness ≥ 0.95) i trafności odpowiedzi. |
| Eksport raportów | `fpdf2` | Generowanie wielostronicowych raportów audytu PZP/KIO do formatu `.pdf`. |

---

## Struktura dokumentacji

Specyfikacja techniczna projektu znajduje się w katalogu `docs/`:

### Architektura i koncepcje
* [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md): Ogólna architektura systemu, role komponentów i separacja warstw.
* [`docs/architecture/rag-strategy.md`](docs/architecture/rag-strategy.md): Wyszukiwanie hybrydowe, formuła RRF, reranking, podział Parent-Child, GraphRAG, Pre-Retrieval i redukcja halucynacji.
* [`docs/architecture/tech-stack.md`](docs/architecture/tech-stack.md): Porównanie stosu lokalnego i alternatyw chmurowych.
* [`docs/architecture/data-flow.md`](docs/architecture/data-flow.md): Przepływ danych od pobrania SWZ do wygenerowania raportu.

### Domena GovTech i rynek GIS w Polsce
* [`docs/domain-govtech/market-analysis.md`](docs/domain-govtech/market-analysis.md): Analiza rozwiązań Geo-System (e-mapa), GIAP oraz Geobid (EWMAPA, OŚRODEK).
* [`docs/domain-govtech/kio-vendor-lockin.md`](docs/domain-govtech/kio-vendor-lockin.md): Analiza barier rynkowych, formatu .str oraz wyroków Krajowej Izby Odwoławczej.
* [`docs/domain-govtech/gis-standards.md`](docs/domain-govtech/gis-standards.md): Standardy baz BDOT500, GESUT, Rejestru Urbanistycznego i układów współrzędnych (PL-2000, układ 1965).

### Pipeline danych
* [`docs/data-pipeline/ingestion-ezamowienia.md`](docs/data-pipeline/ingestion-ezamowienia.md): Integracja z API e-Zamówienia, limity zapytań i kody CPV.
* [`docs/data-pipeline/parsing-docling.md`](docs/data-pipeline/parsing-docling.md): Konfiguracja parsera Docling do konwersji tabel SWZ do Markdown.
* [`docs/data-pipeline/metadata-schema.md`](docs/data-pipeline/metadata-schema.md): Schemat tabel relacyjnych, struktura payloadu JSONB i indeksy bazy danych.

### Modele i szablony zapytań
* [`docs/models-and-prompts/embeddings-bge-m3.md`](docs/models-and-prompts/embeddings-bge-m3.md): Konfiguracja modelu BGE-M3 i rerankera.
* [`docs/models-and-prompts/llm-ollama.md`](docs/models-and-prompts/llm-ollama.md): Konfiguracja Ollama, parametry kwantyzacji i prompt systemowy.
* [`docs/models-and-prompts/expert-prompts.md`](docs/models-and-prompts/expert-prompts.md): Zestaw zapytań analitycznych oraz format wyjściowy raportu przetargowego.

### Ewaluacja
* [`docs/evaluation/ragas-metrics.md`](docs/evaluation/ragas-metrics.md): Pomiar wierności i trafności odpowiedzi z użyciem biblioteki RAGAS.

### Wdrożenie i uruchomienie
* [`docs/deployment-and-ops/local-setup.md`](docs/deployment-and-ops/local-setup.md): Instrukcja instalacji środowiska lokalnego.
* [`docs/deployment-and-ops/hardware-16gb-ram.md`](docs/deployment-and-ops/hardware-16gb-ram.md): Zarządzanie alokacją pamięci na konfiguracji z 16 GB RAM.
* [`docs/deployment-and-ops/docker-compose.md`](docs/deployment-and-ops/docker-compose.md): Zarządzanie kontenerem bazy danych.

### Przewodniki
* [`docs/guides/test-cases.md`](docs/guides/test-cases.md): Scenariusze testowe dla trudnych przypadków dokumentacji.
* [`docs/guides/troubleshooting.md`](docs/guides/troubleshooting.md): Rozwiązywanie typowych problemów operacyjnych.

---

## Uruchomienie lokalne

### Wymagania
* System operacyjny: Windows 10/11 / Linux / macOS,
* Pamięć RAM: minimum 16 GB,
* Zainstalowane środowiska: Python 3.12, Node.js 20+, Docker, Ollama.

```bash
# 1. Klonowanie repozytorium
git clone https://github.com/kacperszczudlo/GisMarketIntelligenceAi.git
cd GisMarketIntelligenceAi

# 2. Uruchomienie bazy danych PostgreSQL + pgvector
docker compose up -d

# 3. Pobranie modelu językowego
ollama pull gis-analyst

# 4. Utworzenie środowiska wirtualnego i instalacja zależności Python
python -m venv .venv
.venv\Scripts\activate  # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 5. Instalacja i zbudowanie frontendu React (Vite)
cd frontend
npm install
npm run build
cd ..

# 6. Uruchomienie aplikacji (FastAPI + React SPA na jednym porcie)
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
# Aplikacja dostępna pod http://127.0.0.1:8000

# 7. Uruchomienie testów
run_tests.bat  # lub: pytest
```

---

## Licencja

Projekt udostępniany na warunkach licencji [MIT](LICENSE).
