-- Generated deterministically from installers/migrations/postgresql/0020_bulk_import_framework.sql.
-- Source SHA-256: eaa4b680e52681d29343295e725ac06bf79061aa457c69490a76c40c04e2da11
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE bulk_import_jobs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    import_format VARCHAR2(255 CHAR) NOT NULL,
    dry_run NUMBER(1) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    total_rows NUMBER(19) NOT NULL,
    valid_rows NUMBER(19) NOT NULL,
    invalid_rows NUMBER(19) NOT NULL,
    create_count NUMBER(19) NOT NULL,
    update_count NUMBER(19) NOT NULL,
    mapping CLOB NOT NULL,
    metrics CLOB NOT NULL,
    checkpoint CLOB NOT NULL,
    impact_sample CLOB NOT NULL,
    dlq_sample CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CHECK (import_format IN ('csv', 'json', 'xlsx')),
    CHECK (status IN ('queued', 'validated', 'applied', 'failed')),
    CHECK (total_rows >= 0),
    CHECK (valid_rows >= 0),
    CHECK (invalid_rows >= 0),
    CHECK (valid_rows + invalid_rows = total_rows),
    CHECK (create_count >= 0),
    CHECK (update_count >= 0),
    CHECK (create_count + update_count <= valid_rows),
    CHECK (JSON_EXISTS(mapping, '$?(@.type() == \"object\")')),
    CHECK (JSON_EXISTS(metrics, '$?(@.type() == \"object\")')),
    CHECK (JSON_EXISTS(checkpoint, '$?(@.type() == \"object\")')),
    CHECK (JSON_EXISTS(impact_sample, '$?(@.type() == \"array\")')),
    CHECK (JSON_EXISTS(dlq_sample, '$?(@.type() == \"array\")')),
    CONSTRAINT ck_bulk_import_jobs_mapping_json CHECK (mapping IS JSON),
    CONSTRAINT ck_bulk_import_jobs_metrics_json CHECK (metrics IS JSON),
    CONSTRAINT ck_bulk_import_jobs_checkpoint_json CHECK (checkpoint IS JSON),
    CONSTRAINT ck_bulk_import_jobs_impact_sample_json CHECK (impact_sample IS JSON),
    CONSTRAINT ck_bulk_import_jobs_dlq_sample_json CHECK (dlq_sample IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE bulk_import_checkpoints (
    job_id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    next_row_number NUMBER(19) NOT NULL,
    total_rows NUMBER(19) NOT NULL,
    valid_rows NUMBER(19) NOT NULL,
    invalid_rows NUMBER(19) NOT NULL,
    create_count NUMBER(19) NOT NULL,
    update_count NUMBER(19) NOT NULL,
    batches_completed NUMBER(19) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, job_id),
    CHECK (next_row_number >= 1),
    CHECK (total_rows >= 0),
    CHECK (valid_rows >= 0),
    CHECK (invalid_rows >= 0),
    CHECK (valid_rows + invalid_rows = total_rows),
    CHECK (create_count >= 0),
    CHECK (update_count >= 0),
    CHECK (create_count + update_count <= valid_rows),
    CHECK (batches_completed >= 0),
    CHECK (status IN ('queued', 'validated', 'applied', 'failed'))
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_bulk_import_jobs_status_updated
    ON bulk_import_jobs (tenant_id, status, updated_at DESC);

CREATE INDEX idx_bulk_import_checkpoints_status_updated
    ON bulk_import_checkpoints (tenant_id, status, updated_at DESC);

CREATE INDEX idx_bulk_import_audit_events
    ON audit_events (tenant_id, action, created_at DESC);
