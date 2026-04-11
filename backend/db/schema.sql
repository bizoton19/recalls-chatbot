-- =============================================================================
-- Recalls Chatbot — Database Schema
-- PostgreSQL 16 + pgvector
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Agencies
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agencies (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(20)  NOT NULL UNIQUE,  -- CPSC, NHTSA, FDA, USDA, EPA, USCG
    name        VARCHAR(255) NOT NULL,
    url         VARCHAR(500),
    api_url     VARCHAR(500),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

INSERT INTO agencies (code, name, url, api_url) VALUES
    ('CPSC', 'Consumer Product Safety Commission', 'https://www.cpsc.gov', 'https://www.saferproducts.gov/RestWebServices/Recall')
ON CONFLICT (code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Recalls
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recalls (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agency_code         VARCHAR(20) NOT NULL REFERENCES agencies(code),
    external_id         VARCHAR(500),          -- original ID from source agency
    recall_number       VARCHAR(100),
    title               TEXT        NOT NULL,
    description         TEXT,
    hazard              TEXT,
    remedy              TEXT,
    recall_date         DATE,
    units_affected      BIGINT,
    url                 VARCHAR(1000),

    -- Product details
    product_name        TEXT,
    product_description TEXT,
    product_type        VARCHAR(255),          -- Vehicle, Food, Consumer Product, etc.
    brand_name          TEXT,
    manufacturer        TEXT,
    model_numbers       TEXT[],

    -- Vehicle-specific (NHTSA)
    vehicle_make        VARCHAR(255),
    vehicle_model       VARCHAR(255),
    vehicle_year_from   SMALLINT,
    vehicle_year_to     SMALLINT,
    component           VARCHAR(500),

    -- Food/Drug-specific (FDA, USDA)
    product_quantity    TEXT,
    distribution_pattern TEXT,
    reason_for_recall   TEXT,
    classification      VARCHAR(50),           -- Class I, II, III

    -- Indexing
    is_indexed          BOOLEAN     NOT NULL DEFAULT FALSE,
    raw_data            JSONB,

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (agency_code, external_id)
);

CREATE INDEX IF NOT EXISTS idx_recalls_agency      ON recalls (agency_code);
CREATE INDEX IF NOT EXISTS idx_recalls_date        ON recalls (recall_date DESC);
CREATE INDEX IF NOT EXISTS idx_recalls_product_type ON recalls (product_type);
CREATE INDEX IF NOT EXISTS idx_recalls_is_indexed  ON recalls (is_indexed) WHERE is_indexed = FALSE;
CREATE INDEX IF NOT EXISTS idx_recalls_raw_data    ON recalls USING GIN (raw_data);

-- ---------------------------------------------------------------------------
-- Recall Embeddings (pgvector)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recall_embeddings (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    recall_id   UUID        NOT NULL REFERENCES recalls(id) ON DELETE CASCADE,
    chunk_index SMALLINT    NOT NULL DEFAULT 0,   -- for multi-chunk recalls
    chunk_text  TEXT        NOT NULL,              -- the text that was embedded
    embedding   vector(1536),                      -- text-embedding-3-small = 1536 dims
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (recall_id, chunk_index)
);

-- IVFFlat index for approximate nearest-neighbor search
-- (Switch to HNSW for production: CREATE INDEX ... USING hnsw)
CREATE INDEX IF NOT EXISTS idx_recall_embeddings_ivfflat
    ON recall_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- Chat Sessions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_token   VARCHAR(255) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_token      ON chat_sessions (session_token);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_active ON chat_sessions (last_active_at);

-- ---------------------------------------------------------------------------
-- Chat Messages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID        NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT        NOT NULL,
    sources     JSONB,       -- recall IDs cited in assistant response
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages (session_id, created_at);

-- ---------------------------------------------------------------------------
-- Ingestion Jobs (audit trail)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agency_code     VARCHAR(20) REFERENCES agencies(code),
    status          VARCHAR(20) NOT NULL DEFAULT 'running'
                                CHECK (status IN ('running', 'completed', 'failed')),
    recalls_fetched INT         NOT NULL DEFAULT 0,
    recalls_new     INT         NOT NULL DEFAULT 0,
    recalls_updated INT         NOT NULL DEFAULT 0,
    embeddings_created INT      NOT NULL DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    metadata        JSONB
);

-- ---------------------------------------------------------------------------
-- Updated-at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_recalls_updated_at
    BEFORE UPDATE ON recalls
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_agencies_updated_at
    BEFORE UPDATE ON agencies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
