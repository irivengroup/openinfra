-- Generated deterministically from installers/migrations/postgresql/0060_ipam_ddi_execution_journal.sql.
-- Source SHA-256: 3d14d634eb2d9266fdb977015d17936debff4bb372cf082b185bad99c831854d
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE ipam_ddi_executions (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    execution_idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    request_fingerprint VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    reconciliation_required NUMBER(1) DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, execution_idempotency_key),
    UNIQUE (tenant_id, id),
    CONSTRAINT ck_ipam_ddi_execution_key_nonempty CHECK (TRIM(execution_idempotency_key) IS NOT NULL),
    CONSTRAINT ck_ipam_ddi_fingerprint_sha256 CHECK (REGEXP_LIKE(request_fingerprint, '^[0-9a-f]{64}$')),
    CONSTRAINT ck_ipam_ddi_status CHECK (
        status IN (
            'pending',
            'running',
            'succeeded',
            'failed',
            'compensating',
            'compensated',
            'compensation_failed'
        )
    ),
    CONSTRAINT ck_ipam_ddi_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_ipam_ddi_executions_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 4;

CREATE INDEX idx_ipam_ddi_executions_status_updated
    ON ipam_ddi_executions (tenant_id, status, updated_at DESC);

CREATE INDEX idx_ipam_ddi_executions_reconciliation
    ON ipam_ddi_executions (tenant_id, reconciliation_required, updated_at DESC);

CREATE INDEX idx_audit_events_ipam_ddi_execution
    ON audit_events (tenant_id, target_type, created_at DESC);
