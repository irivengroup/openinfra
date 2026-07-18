-- Generated deterministically from installers/migrations/postgresql/0057_federated_identity_team_sync.sql.
-- Source SHA-256: 370eeba1599ee9737b6546da6096029a0e1f72590befd82712a3bee00c2d93af
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE identity_team_sync_sources (
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id VARCHAR2(128 CHAR) NOT NULL,
    provider VARCHAR2(255 CHAR) NOT NULL CHECK (provider IN ('ldap', 'oauth', 'auth_proxy', 'okta')),
    fingerprint VARCHAR2(255 CHAR) NOT NULL CHECK (REGEXP_LIKE(fingerprint, '^[0-9a-f]{64}$')),
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    users CLOB DEFAULT '[]' NOT NULL,
    owned_users CLOB DEFAULT '[]' NOT NULL,
    groups CLOB DEFAULT '[]' NOT NULL,
    memberships CLOB DEFAULT '[]' NOT NULL,
    last_result CLOB DEFAULT '{}' NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, source_id),
    CONSTRAINT ck_identity_team_sync_sources_users_json CHECK (users IS JSON),
    CONSTRAINT ck_identity_team_sync_sources_owned_users_json CHECK (owned_users IS JSON),
    CONSTRAINT ck_identity_team_sync_sources_groups_json CHECK (groups IS JSON),
    CONSTRAINT ck_identity_team_sync_sources_memberships_json CHECK (memberships IS JSON),
    CONSTRAINT ck_identity_team_sync_sources_last_result_json CHECK (last_result IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE identity_team_sync_runs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id VARCHAR2(128 CHAR) NOT NULL,
    provider VARCHAR2(255 CHAR) NOT NULL CHECK (provider IN ('ldap', 'oauth', 'auth_proxy', 'okta')),
    fingerprint VARCHAR2(255 CHAR) NOT NULL CHECK (REGEXP_LIKE(fingerprint, '^[0-9a-f]{64}$')),
    result CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ck_identity_team_sync_runs_result_json CHECK (result IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE federated_identity_links (
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider VARCHAR2(255 CHAR) NOT NULL CHECK (provider IN ('saml', 'ldap', 'ipa', 'oauth', 'auth_proxy', 'okta')),
    external_subject VARCHAR2(255 CHAR) NOT NULL,
    local_subject VARCHAR2(255 CHAR) NOT NULL,
    external_groups_digest VARCHAR2(255 CHAR) NOT NULL CHECK (REGEXP_LIKE(external_groups_digest, '^[0-9a-f]{64}$')),
    last_authenticated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, provider, external_subject),
    FOREIGN KEY (tenant_id, local_subject)
        REFERENCES identity_users(tenant_id, username) ON DELETE CASCADE
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE INDEX idx_identity_team_sync_sources_provider
ON identity_team_sync_sources (tenant_id, provider, source_id);

CREATE INDEX idx_identity_team_sync_runs_created
ON identity_team_sync_runs (tenant_id, source_id, created_at DESC, id);

CREATE INDEX idx_federated_identity_links_local
ON federated_identity_links (tenant_id, local_subject, provider);

CREATE INDEX idx_audit_events_federated_identity
ON audit_events (tenant_id, action, created_at DESC);
