# Zarządzanie usługami w Docker Compose

## 1. Konfiguracja kontenera bazy danych

Usługa bazy danych bazuje na oficjalnym obrazie `pgvector/pgvector:pg16`.

Zawartość pliku `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: gis_pgvector
    restart: always
    environment:
      POSTGRES_DB: gis_intelligence
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres_secret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    deploy:
      resources:
        limits:
          memory: 2048M
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d gis_intelligence"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
    driver: local
```

---

## 2. Podstawowe operacje

```bash
# Uruchomienie kontenera w tle
docker compose up -d

# Podgląd logów bazy danych
docker compose logs -f postgres

# Połączenie z konsolą bazy danych
docker exec -it gis_pgvector psql -U postgres -d gis_intelligence

# Zatrzymanie kontenera z zachowaniem danych
docker compose down

# Zatrzymanie kontenera i usunięcie wolumenu danych
docker compose down -v
```
