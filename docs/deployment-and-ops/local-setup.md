# Konfiguracja środowiska lokalnego

## 1. Wymagania sprzętowe i systemowe

* **System operacyjny**: Windows 10/11 (z WSL2 dla Dockera), Linux (Ubuntu 22.04+) lub macOS.
* **Pamięć RAM**: minimum 16 GB.
* **Procesor**: 4 rdzenie z obsługą instrukcji AVX2 lub Apple Silicon (M1/M2/M3).
* **Narzędzia**: Python 3.12, Node.js 20+, Docker Desktop, Ollama.

---

## 2. Instrukcja instalacji

### Krok 1: Klonowanie repozytorium i utworzenie środowiska wirtualnego
```bash
git clone https://github.com/twoj-login/GisMarketIntelligenceAi.git
cd GisMarketIntelligenceAi

python -m venv .venv

# Aktywacja w systemie Windows:
.venv\Scripts\activate

# Aktywacja w systemie Linux / macOS:
source .venv/bin/activate
```

### Krok 2: Instalacja zależności Python
```bash
pip install --upgrade pip setuptools wheel
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Krok 3: Uruchomienie bazy danych
```bash
docker compose up -d
docker ps
```

### Krok 4: Pobranie modelu w Ollama
```bash
ollama pull gis-analyst
ollama list
```

### Krok 5: Budowa frontendu React (Vite) i start serwera FastAPI
```bash
cd frontend
npm install
npm run build
cd ..

python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

### Krok 5: Utworzenie pliku konfiguracyjnego `.env`
Utwórz plik `.env` w katalogu głównym:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gis_intelligence
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_secret

OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL_NAME=BAAI/bge-m3
RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3

RAW_DATA_DIR=./data_raw
PROCESSED_DATA_DIR=./data_processed
```

---

## 3. Weryfikacja instalacji

Skrypt weryfikujący połączenie z bazą PostgreSQL oraz silnikiem Ollama:

```python
import psycopg2
from llama_index.llms.ollama import Ollama

try:
  conn = psycopg2.connect(
      dbname="gis_intelligence",
      user="postgres",
      password="postgres_secret",
      host="localhost",
      port=5432,
  )
  print("PostgreSQL + pgvector: połączenie prawidłowe")
  conn.close()
except Exception as e:
  print(f"Błąd połączenia z bazą: {e}")

try:
  llm = Ollama(model="llama3.1:8b-instruct-q4_K_M")
  res = llm.complete("Napisz 'OK'.")
  print(f"Ollama: odpowiedź modelu: {res.text.strip()}")
except Exception as e:
  print(f"Błąd połączenia z Ollama: {e}")
```
