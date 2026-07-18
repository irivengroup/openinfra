-- Generated deterministically from installers/migrations/postgresql/0021_export_framework.sql.
-- Source SHA-256: 3b209753aad4f0c0a3a4ba457dde47207f4ec1b0cb849b192dbc74d37ced4630
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE export_jobs (
    id VARCHAR2(255 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    "RESOURCE" VARCHAR2(255 CHAR) NOT NULL,
    export_format VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    filter CLOB NOT NULL,
    requested_by VARCHAR2(255 CHAR) NOT NULL,
    total_rows NUMBER(19) DEFAULT 0 NOT NULL,
    artifact CLOB,
    error CLOB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT export_jobs_resource_check CHECK ("RESOURCE" IN ('source_objects')),
    CONSTRAINT export_jobs_format_check CHECK (export_format IN ('csv', 'json', 'xlsx')),
    CONSTRAINT export_jobs_status_check CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    CONSTRAINT export_jobs_total_rows_check CHECK (total_rows >= 0),
    CONSTRAINT ck_export_jobs_filter_json CHECK (filter IS JSON),
    CONSTRAINT ck_export_jobs_artifact_json CHECK (artifact IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_export_jobs_queue
    ON export_jobs (tenant_id, status, created_at, id);

CREATE TABLE export_artifacts (
    job_id VARCHAR2(128 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    content BLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, job_id),
    FOREIGN KEY (tenant_id, job_id) REFERENCES export_jobs(tenant_id, id) ON DELETE CASCADE
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE TABLE export_signing_keys (
    id VARCHAR2(255 CHAR) PRIMARY KEY,
    secret_hex VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT export_signing_keys_secret_hex_check CHECK (REGEXP_LIKE(secret_hex, '^[a-f0-9]{64}$'))
);

CREATE INDEX idx_audit_events_exports
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
