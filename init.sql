-- Inicjalizacja bazy danych GIS-Market Intelligence AI
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Tabela Postępowań Przetargowych
CREATE TABLE IF NOT EXISTS procurements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ocds_id VARCHAR(100) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    municipality_name VARCHAR(255) NOT NULL,
    voivodeship VARCHAR(100) NOT NULL,
    estimated_budget_pln NUMERIC(12, 2),
    cpv_codes TEXT[] NOT NULL DEFAULT '{}',
    date_published TIMESTAMPTZ NOT NULL,
    date_deadline TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_procurements_ocds ON procurements(ocds_id);
CREATE INDEX IF NOT EXISTS idx_procurements_voivodeship ON procurements(voivodeship);
CREATE INDEX IF NOT EXISTS idx_procurements_date_deadline ON procurements(date_deadline);
CREATE INDEX IF NOT EXISTS idx_procurements_cpv ON procurements USING GIN(cpv_codes);

-- 2. Tabela Załączników (SWZ, OPZ)
CREATE TABLE IF NOT EXISTS attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procurement_id UUID NOT NULL REFERENCES procurements(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    sha256_hash CHAR(64) NOT NULL,
    raw_markdown TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabela Węzłów Nadrzędnych (Parent Nodes)
CREATE TABLE IF NOT EXISTS parent_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attachment_id UUID NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
    section_title TEXT,
    token_count INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabela Węzłów Podrzędnych i Wektorów (Child Nodes)
CREATE TABLE IF NOT EXISTS chunk_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID NOT NULL REFERENCES parent_nodes(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    content_tsvector TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    metadata_payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw ON chunk_vectors 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_chunks_tsvector ON chunk_vectors USING GIN(content_tsvector);
CREATE INDEX IF NOT EXISTS idx_chunks_payload ON chunk_vectors USING GIN(metadata_payload);

-- 5. Tabela Użytkowników (Logowanie i role admin/user)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
