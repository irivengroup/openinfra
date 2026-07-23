-- Generated deterministically from installers/migrations/postgresql/0006_audit_trail_integrity.sql.
-- Source SHA-256: d61cecc0ad35ec595d0cb9d2067f0020891af1dab5dbf5cbef4dd12721eec27c
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE audit_events ADD (previous_hash VARCHAR2(255 CHAR) DEFAULT RPAD('0', 64, '0') NOT NULL);

ALTER TABLE audit_events ADD (record_hash VARCHAR2(255 CHAR) DEFAULT RPAD('0', 64, '0') NOT NULL);

ALTER TABLE audit_events ADD CONSTRAINT audit_events_previous_hash_sha256
    CHECK (REGEXP_LIKE(previous_hash, '^[a-f0-9]{64}$'));

ALTER TABLE audit_events ADD CONSTRAINT audit_events_record_hash_sha256
    CHECK (REGEXP_LIKE(record_hash, '^[a-f0-9]{64}$'));

CREATE INDEX idx_audit_events_actor_action
    ON audit_events (tenant_id, actor, action, created_at DESC);

CREATE INDEX idx_audit_events_severity_time
    ON audit_events (tenant_id, severity, created_at DESC);

CREATE INDEX idx_audit_events_integrity_chain
    ON audit_events (tenant_id, previous_hash, record_hash, created_at DESC);
