CREATE TABLE IF NOT EXISTS ipam_ddi_executions (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    execution_idempotency_key text NOT NULL,
    request_fingerprint text NOT NULL,
    status text NOT NULL,
    reconciliation_required boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, execution_idempotency_key),
    UNIQUE (tenant_id, id),
    CONSTRAINT ck_ipam_ddi_execution_key_nonempty CHECK (btrim(execution_idempotency_key) <> ''),
    CONSTRAINT ck_ipam_ddi_fingerprint_sha256 CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
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
    CONSTRAINT ck_ipam_ddi_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS ipam_ddi_executions_p00 PARTITION OF ipam_ddi_executions
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE IF NOT EXISTS ipam_ddi_executions_p01 PARTITION OF ipam_ddi_executions
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE IF NOT EXISTS ipam_ddi_executions_p02 PARTITION OF ipam_ddi_executions
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE IF NOT EXISTS ipam_ddi_executions_p03 PARTITION OF ipam_ddi_executions
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

CREATE INDEX idx_ipam_ddi_executions_status_updated
    ON ipam_ddi_executions (tenant_id, status, updated_at DESC);

CREATE INDEX idx_ipam_ddi_executions_reconciliation
    ON ipam_ddi_executions (tenant_id, reconciliation_required, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_ipam_ddi_execution
    ON audit_events (tenant_id, target_type, created_at DESC);
