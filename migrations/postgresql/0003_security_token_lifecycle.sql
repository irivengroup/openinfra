BEGIN;

ALTER TABLE api_tokens
    ADD COLUMN IF NOT EXISTS expires_at timestamptz,
    ADD COLUMN IF NOT EXISTS revoked_at timestamptz,
    ADD COLUMN IF NOT EXISTS revoked_by text,
    ADD COLUMN IF NOT EXISTS use_count bigint NOT NULL DEFAULT 0;

ALTER TABLE api_tokens
    ADD CONSTRAINT chk_api_tokens_use_count_non_negative CHECK (use_count >= 0) NOT VALID;

CREATE INDEX IF NOT EXISTS idx_api_tokens_lifecycle_active
    ON api_tokens (tenant_id, active, expires_at, revoked_at, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_tokens_revoked
    ON api_tokens (tenant_id, revoked_at DESC, revoked_by)
    WHERE revoked_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_events_security_token_lifecycle
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action IN ('security.token.revoke', 'security.token.rotate', 'security.token.list');

COMMIT;
