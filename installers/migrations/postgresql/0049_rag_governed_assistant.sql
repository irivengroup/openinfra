-- OpenInfra v0.29.101 - P16 / EPIC-1606 governed RAG assistant
BEGIN;

CREATE TABLE IF NOT EXISTS rag_documents (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type text NOT NULL,
    source_ref text NOT NULL,
    version integer NOT NULL,
    active boolean NOT NULL,
    checksum char(64) NOT NULL,
    required_permissions jsonb NOT NULL,
    indexed_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, source_type, source_ref, version),
    CONSTRAINT rag_document_source_type_valid CHECK (
        source_type IN ('rsot','runbook','policy','documentation','other')
    ),
    CONSTRAINT rag_document_version_valid CHECK (version > 0),
    CONSTRAINT rag_document_checksum_valid CHECK (checksum ~ '^[a-f0-9]{64}$'),
    CONSTRAINT rag_document_permissions_array CHECK (jsonb_typeof(required_permissions) = 'array'),
    CONSTRAINT rag_document_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id uuid NOT NULL,
    ordinal integer NOT NULL,
    title text NOT NULL,
    content text NOT NULL,
    required_permissions jsonb NOT NULL,
    payload jsonb NOT NULL,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(content, '')), 'B')
    ) STORED,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, document_id, ordinal),
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES rag_documents(tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT rag_chunk_ordinal_valid CHECK (ordinal >= 0),
    CONSTRAINT rag_chunk_permissions_array CHECK (jsonb_typeof(required_permissions) = 'array'),
    CONSTRAINT rag_chunk_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS rag_answers (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    question_hash char(64) NOT NULL,
    status text NOT NULL,
    confidence numeric(5,4) NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT rag_answer_hash_valid CHECK (question_hash ~ '^[a-f0-9]{64}$'),
    CONSTRAINT rag_answer_status_valid CHECK (status IN ('answered','insufficient-context')),
    CONSTRAINT rag_answer_confidence_valid CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT rag_answer_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS rag_jobs (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    kind text NOT NULL,
    status text NOT NULL,
    idempotency_key text NOT NULL,
    input_digest char(64) NOT NULL,
    processed_count integer NOT NULL,
    total_count integer NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT rag_job_kind_valid CHECK (kind IN ('document-import','answer-export')),
    CONSTRAINT rag_job_status_valid CHECK (status IN ('queued','running','completed','failed')),
    CONSTRAINT rag_job_digest_valid CHECK (input_digest ~ '^[a-f0-9]{64}$'),
    CONSTRAINT rag_job_progress_valid CHECK (
        processed_count >= 0 AND total_count >= 0 AND processed_count <= total_count
    ),
    CONSTRAINT rag_job_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS rag_artifacts (
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    job_id uuid NOT NULL,
    filename text NOT NULL,
    content_type text NOT NULL,
    content bytea NOT NULL,
    sha256 char(64) NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, job_id),
    FOREIGN KEY (tenant_id, job_id) REFERENCES rag_jobs(tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT rag_artifact_sha256_valid CHECK (sha256 ~ '^[a-f0-9]{64}$')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS rag_event_outbox (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id uuid NOT NULL,
    event_name text NOT NULL,
    payload jsonb NOT NULL,
    occurred_at timestamptz NOT NULL,
    published_at timestamptz,
    attempt_count integer NOT NULL DEFAULT 0,
    last_error text,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT rag_event_name_valid CHECK (event_name ~ '^[a-z][a-z0-9_.-]{2,120}$'),
    CONSTRAINT rag_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT rag_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

DO $partitioning$
DECLARE
    table_name text;
    partition_index integer;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'rag_documents',
        'rag_chunks',
        'rag_answers',
        'rag_jobs',
        'rag_artifacts',
        'rag_event_outbox'
    ]
    LOOP
        FOR partition_index IN 0..15 LOOP
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
                table_name || '_p' || lpad(partition_index::text, 2, '0'),
                table_name,
                partition_index
            );
        END LOOP;
    END LOOP;
END
$partitioning$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_rag_documents_active_source
    ON rag_documents (tenant_id, source_type, source_ref) WHERE active;
CREATE INDEX IF NOT EXISTS idx_rag_documents_listing
    ON rag_documents (tenant_id, source_type, active, indexed_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_rag_documents_permissions
    ON rag_documents USING gin (required_permissions jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_document
    ON rag_chunks (tenant_id, document_id, ordinal, id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_search
    ON rag_chunks USING gin (search_vector);
CREATE INDEX IF NOT EXISTS idx_rag_answers_listing
    ON rag_answers (tenant_id, generated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_rag_answers_question_hash
    ON rag_answers (tenant_id, question_hash, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_rag_jobs_listing
    ON rag_jobs (tenant_id, status, kind, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_rag_event_outbox_pending
    ON rag_event_outbox (tenant_id, occurred_at, id) WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_rag_event_outbox_occurred_brin
    ON rag_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_audit_events_rag
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('rag_document','rag_answer','rag_job','rag_index');

COMMIT;
