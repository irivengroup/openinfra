-- Generated deterministically from installers/migrations/postgresql/0049_rag_governed_assistant.sql.
-- Source SHA-256: 6e5d7becd2e85a33c22e8eb3e7e17772187dc716a7e762389b0e35c016cfe869
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE rag_documents (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type VARCHAR2(128 CHAR) NOT NULL,
    source_ref VARCHAR2(255 CHAR) NOT NULL,
    version NUMBER(10) NOT NULL,
    active NUMBER(1) NOT NULL,
    checksum CHAR(64 CHAR) NOT NULL,
    required_permissions CLOB NOT NULL,
    indexed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, source_type, source_ref, version),
    CONSTRAINT rag_document_source_type_valid CHECK (
        source_type IN ('rsot','runbook','policy','documentation','other')
    ),
    CONSTRAINT rag_document_version_valid CHECK (version > 0),
    CONSTRAINT rag_document_checksum_valid CHECK (REGEXP_LIKE(checksum, '^[a-f0-9]{64}$')),
    CONSTRAINT rag_document_permissions_array CHECK (JSON_EXISTS(required_permissions, '$?(@.type() == \"array\")')),
    CONSTRAINT rag_document_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_rag_documents_required_permissions_json CHECK (required_permissions IS JSON),
    CONSTRAINT ck_rag_documents_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE rag_chunks (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id VARCHAR2(36 CHAR) NOT NULL,
    ordinal NUMBER(10) NOT NULL,
    title VARCHAR2(255 CHAR) NOT NULL,
    content CLOB NOT NULL,
    required_permissions CLOB NOT NULL,
    payload CLOB NOT NULL,
    search_vector CLOB,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, document_id, ordinal),
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES rag_documents(tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT rag_chunk_ordinal_valid CHECK (ordinal >= 0),
    CONSTRAINT rag_chunk_permissions_array CHECK (JSON_EXISTS(required_permissions, '$?(@.type() == \"array\")')),
    CONSTRAINT rag_chunk_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_rag_chunks_required_permissions_json CHECK (required_permissions IS JSON),
    CONSTRAINT ck_rag_chunks_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE rag_answers (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    question_hash CHAR(64 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    confidence NUMBER(5,4) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT rag_answer_hash_valid CHECK (REGEXP_LIKE(question_hash, '^[a-f0-9]{64}$')),
    CONSTRAINT rag_answer_status_valid CHECK (status IN ('answered','insufficient-context')),
    CONSTRAINT rag_answer_confidence_valid CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT rag_answer_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_rag_answers_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE rag_jobs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    kind VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    input_digest CHAR(64 CHAR) NOT NULL,
    processed_count NUMBER(10) NOT NULL,
    total_count NUMBER(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT rag_job_kind_valid CHECK (kind IN ('document-import','answer-export')),
    CONSTRAINT rag_job_status_valid CHECK (status IN ('queued','running','completed','failed')),
    CONSTRAINT rag_job_digest_valid CHECK (REGEXP_LIKE(input_digest, '^[a-f0-9]{64}$')),
    CONSTRAINT rag_job_progress_valid CHECK (
        processed_count >= 0 AND total_count >= 0 AND processed_count <= total_count
    ),
    CONSTRAINT rag_job_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_rag_jobs_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE rag_artifacts (
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    job_id VARCHAR2(36 CHAR) NOT NULL,
    filename VARCHAR2(255 CHAR) NOT NULL,
    content_type VARCHAR2(128 CHAR) NOT NULL,
    content BLOB NOT NULL,
    sha256 CHAR(64 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, job_id),
    FOREIGN KEY (tenant_id, job_id) REFERENCES rag_jobs(tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT rag_artifact_sha256_valid CHECK (REGEXP_LIKE(sha256, '^[a-f0-9]{64}$'))
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE rag_event_outbox (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id VARCHAR2(36 CHAR) NOT NULL,
    event_name VARCHAR2(255 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    attempt_count NUMBER(10) DEFAULT 0 NOT NULL,
    last_error VARCHAR2(255 CHAR),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT rag_event_name_valid CHECK (REGEXP_LIKE(event_name, '^[a-z][a-z0-9_.-]{2,120}$')),
    CONSTRAINT rag_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT rag_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_rag_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE UNIQUE INDEX uq_rag_documents_active_source
    ON rag_documents (CASE WHEN active = 1 THEN tenant_id END, CASE WHEN active = 1 THEN source_type END, CASE WHEN active = 1 THEN source_ref END);

CREATE INDEX idx_rag_documents_listing
    ON rag_documents (tenant_id, source_type, active, indexed_at DESC, id DESC);

CREATE INDEX idx_rag_chunks_document
    ON rag_chunks (tenant_id, document_id, ordinal, id);

CREATE INDEX idx_rag_answers_listing
    ON rag_answers (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_rag_answers_question_hash
    ON rag_answers (tenant_id, question_hash, generated_at DESC);

CREATE INDEX idx_rag_jobs_listing
    ON rag_jobs (tenant_id, status, kind, created_at DESC, id DESC);

CREATE INDEX idx_rag_event_outbox_pending
    ON rag_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_rag
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
