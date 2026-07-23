-- Generated deterministically from installers/migrations/postgresql/0019_import_framework.sql.
-- Source SHA-256: 5e5207bd89ee57407fc20458f51759f2ccbdb41307e292d1352068260a7cee85
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE import_jobs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    import_format VARCHAR2(255 CHAR) NOT NULL,
    dry_run NUMBER(1) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    total_rows NUMBER(19) NOT NULL,
    valid_rows NUMBER(19) NOT NULL,
    invalid_rows NUMBER(19) NOT NULL,
    mapping CLOB NOT NULL,
    impacts CLOB NOT NULL,
    dlq CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CHECK (import_format IN ('csv', 'json', 'xlsx')),
    CHECK (status IN ('queued', 'validated', 'applied', 'failed')),
    CHECK (total_rows >= 0),
    CHECK (valid_rows >= 0),
    CHECK (invalid_rows >= 0),
    CHECK (valid_rows + invalid_rows = total_rows),
    CHECK (JSON_EXISTS(mapping, '$?(@.type() == \"object\")')),
    CHECK (JSON_EXISTS(impacts, '$?(@.type() == \"array\")')),
    CHECK (JSON_EXISTS(dlq, '$?(@.type() == \"array\")')),
    CONSTRAINT ck_import_jobs_mapping_json CHECK (mapping IS JSON),
    CONSTRAINT ck_import_jobs_impacts_json CHECK (impacts IS JSON),
    CONSTRAINT ck_import_jobs_dlq_json CHECK (dlq IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_import_jobs_status_updated
    ON import_jobs (tenant_id, status, updated_at DESC);

CREATE INDEX idx_import_jobs_format_created
    ON import_jobs (tenant_id, import_format, created_at DESC);

CREATE INDEX idx_import_framework_audit_events
    ON audit_events (tenant_id, action, created_at DESC);
