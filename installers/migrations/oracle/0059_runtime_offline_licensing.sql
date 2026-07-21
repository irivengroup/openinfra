-- Generated deterministically from installers/migrations/postgresql/0059_runtime_offline_licensing.sql.
-- Source SHA-256: 7dd9409851b05d43b845f3c27c3a8154ecbce85994aeced47643d7fa54bb2745
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE runtime_license_state (
    state_key VARCHAR2(128 CHAR) NOT NULL,
    identity CLOB NOT NULL,
    entitlement CLOB,
    activated_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (state_key),
    CONSTRAINT ck_runtime_license_state_identity_json CHECK (identity IS JSON),
    CONSTRAINT ck_runtime_license_state_entitlement_json CHECK (entitlement IS JSON)
)
PARTITION BY HASH (state_key) PARTITIONS 4;

CREATE INDEX idx_runtime_license_state_updated
    ON runtime_license_state (updated_at DESC);

CREATE INDEX idx_audit_events_runtime_license
    ON audit_events (tenant_id, target_type, created_at DESC);
