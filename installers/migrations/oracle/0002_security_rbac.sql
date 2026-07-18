-- Generated deterministically from installers/migrations/postgresql/0002_security_rbac.sql.
-- Source SHA-256: 6c2ec4b7827e569b19697bccfb3500f625418b1b2a5c62fd1f1d885b670b857d
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE api_tokens (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    subject VARCHAR2(255 CHAR) NOT NULL,
    token_hash CHAR(64 CHAR) NOT NULL,
    token_prefix VARCHAR2(255 CHAR) NOT NULL,
    roles CLOB NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (tenant_id, token_hash),
    CHECK (REGEXP_LIKE(subject, '^[a-z0-9][a-z0-9_.@:-]{1,126}[a-z0-9]$')),
    CHECK (REGEXP_LIKE(token_hash, '^[a-f0-9]{64}$')),
    CHECK (REGEXP_LIKE(token_prefix, '^[A-Za-z0-9_-]{8,16}$')),
    CHECK (JSON_EXISTS(roles, '$[0]')),
    CONSTRAINT ck_api_tokens_roles_json CHECK (roles IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_api_tokens_subject ON api_tokens (tenant_id, subject);

CREATE INDEX idx_api_tokens_active ON api_tokens (tenant_id, active, subject);

CREATE INDEX idx_audit_events_security_actor ON audit_events (tenant_id, actor, created_at DESC);
