BEGIN;

ALTER TABLE audit_events
    ADD COLUMN IF NOT EXISTS previous_hash text NOT NULL DEFAULT repeat('0', 64),
    ADD COLUMN IF NOT EXISTS record_hash text NOT NULL DEFAULT repeat('0', 64);

ALTER TABLE audit_events
    ADD CONSTRAINT audit_events_previous_hash_sha256
    CHECK (previous_hash ~ '^[a-f0-9]{64}$') NOT VALID;

ALTER TABLE audit_events
    ADD CONSTRAINT audit_events_record_hash_sha256
    CHECK (record_hash ~ '^[a-f0-9]{64}$') NOT VALID;

CREATE INDEX IF NOT EXISTS idx_audit_events_actor_action
    ON audit_events (tenant_id, actor, action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_severity_time
    ON audit_events (tenant_id, severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_integrity_chain
    ON audit_events (tenant_id, previous_hash, record_hash, created_at DESC);

COMMIT;
