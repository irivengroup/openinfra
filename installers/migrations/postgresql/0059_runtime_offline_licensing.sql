CREATE TABLE IF NOT EXISTS runtime_license_state (
    state_key text NOT NULL,
    identity jsonb NOT NULL,
    entitlement jsonb,
    activated_at timestamptz,
    last_seen_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (state_key)
) PARTITION BY HASH (state_key);

CREATE TABLE IF NOT EXISTS runtime_license_state_p00 PARTITION OF runtime_license_state
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE IF NOT EXISTS runtime_license_state_p01 PARTITION OF runtime_license_state
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE IF NOT EXISTS runtime_license_state_p02 PARTITION OF runtime_license_state
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE IF NOT EXISTS runtime_license_state_p03 PARTITION OF runtime_license_state
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

CREATE INDEX idx_runtime_license_state_updated
    ON runtime_license_state (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_runtime_license
    ON audit_events (tenant_id, target_type, created_at DESC);
