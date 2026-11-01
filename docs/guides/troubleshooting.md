# Rozwiązywanie problemów operacyjnych

## 1. Komunikacja z API e-Zamówienia

### Błąd HTTP 403 Forbidden
* **Przyczyna**: Przekroczenie limitu 30 zapytań w 60 sekund z jednego adresu IP.
* **Rozwiązanie**:
  1. Zmniejsz limit w klasie `EZamowieniaRateLimiter` do 20 zapytań na minutę.
  2. Dodaj opóźnienie 1 sekundy pomiędzy kolejnymi pobraniami załączników.
  3. Odczekaj 15 minut na odblokowanie adresu IP przez serwery platformy.

---

## 2. Pamięć operacyjna i wydajność

### Błąd braku pamięci (CUDA out of memory lub Out of Memory w systemie)
* **Przyczyna**: Jednoczesne parsowanie dużego pliku PDF przez Docling oraz wnioskowanie modelu Llama 3.1 w Ollamie.
* **Rozwiązanie**:
  1. Rozdziel parsowanie dokumentów i odpytywanie modelu na osobne procesy.
  2. Zmniejsz rozmiar paczki stron przetwarzanych przez Docling.
  3. Wymuś czyszczenie pamięci po zakończeniu ekstrakcji:
     ```python
     import gc, torch

     gc.collect()
     if torch.cuda.is_available():
       torch.cuda.empty_cache()
```

### Długi czas rerankingu na procesorze CPU
* **Przyczyna**: Cross-Encoder wykonuje operację pełnej atencji dla każdego kandydata z osobna.
* **Rozwiązanie**:
  1. Ogranicz liczbę kandydatów przekazywanych z RRF do rerankera z 50 do 25.
  2. Ustaw liczbę wątków PyTorch odpowiadającą fizycznym rdzeniom procesora:
     ```python
     import torch

     torch.set_num_threads(4)
```

---

## 3. Środowisko Docker i baza danych

### Błąd połączenia z bazą (Connection refused na porcie 5432)
* **Przyczyna**: Kontener nie został uruchomiony lub port 5432 jest zajęty przez lokalną instalację PostgreSQL w systemie Windows.
* **Rozwiązanie**:
  1. Sprawdź stan kontenera: `docker ps`.
  2. Jeśli port 5432 jest zajęty, zmień mapowanie portów w `docker-compose.yml` na `5433:5432` oraz ustaw `POSTGRES_PORT=5433` w pliku `.env`.

### Błąd braku rozszerzenia vector w PostgreSQL
* **Przyczyna**: Zastosowano bazowy obraz postgres zamiast obrazu z pgvector.
* **Rozwiązanie**: W pliku `docker-compose.yml` użyj obrazu `pgvector/pgvector:pg16` i uruchom ponownie kontener:
  ```bash
  docker compose pull
  docker compose up -d --force-recreate
```

---

## 4. Model językowy w Ollama

### Błąd przekroczenia limitu czasu (ReadTimeoutException)
* **Przyczyna**: Wczytywanie modelu z dysku do pamięci RAM przy pierwszym zapytaniu trwa dłużej niż domyślny timeout klienta HTTP.
* **Rozwiązanie**:
  1. Utrzymuj model w pamięci poleceniem:
     ```bash
     ollama run llama3.1:8b-instruct-q4_K_M --keepalive -1
```
  2. Zwiększ parametr `request_timeout` w kliencie Ollama do 300 sekund:
     ```python
     llm = Ollama(model="llama3.1:8b-instruct-q4_K_M", request_timeout=300.0)
```
