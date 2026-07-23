BEGIN;

CREATE TABLE IF NOT EXISTS api_tokens (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    subject text NOT NULL,
    token_hash char(64) NOT NULL,
    token_prefix text NOT NULL,
    roles text[] NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_used_at timestamptz,
    PRIMARY KEY (tenant_id, token_hash),
    CHECK (subject ~ '^[a-z0-9][a-z0-9_.@:-]{1,126}[a-z0-9]$'),
    CHECK (token_hash ~ '^[a-f0-9]{64}$'),
    CHECK (token_prefix ~ '^[A-Za-z0-9_-]{8,16}$'),
    CHECK (array_length(roles, 1) >= 1)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS api_tokens_p00 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS api_tokens_p01 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS api_tokens_p02 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS api_tokens_p03 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS api_tokens_p04 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS api_tokens_p05 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS api_tokens_p06 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS api_tokens_p07 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS api_tokens_p08 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS api_tokens_p09 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS api_tokens_p10 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS api_tokens_p11 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS api_tokens_p12 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS api_tokens_p13 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS api_tokens_p14 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS api_tokens_p15 PARTITION OF api_tokens FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_api_tokens_subject ON api_tokens (tenant_id, subject);
CREATE INDEX IF NOT EXISTS idx_api_tokens_active ON api_tokens (tenant_id, active, subject);
CREATE INDEX IF NOT EXISTS idx_api_tokens_roles ON api_tokens USING gin (roles);
CREATE INDEX IF NOT EXISTS idx_audit_events_security_actor ON audit_events (tenant_id, actor, created_at DESC);

COMMIT;
