-- Generated deterministically from installers/migrations/postgresql/0003_security_token_lifecycle.sql.
-- Source SHA-256: ecab1386fb587558a71e06a6972c8f09890a2f0830d26ebddb781e470a867c1e
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE api_tokens ADD (expires_at TIMESTAMP WITH TIME ZONE);

ALTER TABLE api_tokens ADD (revoked_at TIMESTAMP WITH TIME ZONE);

ALTER TABLE api_tokens ADD (revoked_by VARCHAR2(255 CHAR));

ALTER TABLE api_tokens ADD (use_count NUMBER(19) DEFAULT 0 NOT NULL);

ALTER TABLE api_tokens ADD CONSTRAINT chk_api_tokens_use_count_non_negative CHECK (use_count >= 0);

CREATE INDEX idx_api_tokens_lifecycle_active
    ON api_tokens (tenant_id, active, expires_at, revoked_at, created_at DESC);

CREATE INDEX idx_api_tokens_revoked
    ON api_tokens (tenant_id, revoked_at DESC, revoked_by);

CREATE INDEX idx_audit_events_security_token_lifecycle
    ON audit_events (tenant_id, action, created_at DESC);
