BEGIN;

CREATE TABLE IF NOT EXISTS identity_team_sync_sources (
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id text NOT NULL,
    provider text NOT NULL CHECK (provider IN ('ldap', 'oauth', 'auth_proxy', 'okta')),
    fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    captured_at timestamptz NOT NULL,
    users text[] NOT NULL DEFAULT '{}',
    owned_users text[] NOT NULL DEFAULT '{}',
    groups text[] NOT NULL DEFAULT '{}',
    memberships text[] NOT NULL DEFAULT '{}',
    last_result jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, source_id)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS identity_team_sync_runs (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id text NOT NULL,
    provider text NOT NULL CHECK (provider IN ('ldap', 'oauth', 'auth_proxy', 'okta')),
    fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS federated_identity_links (
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider text NOT NULL CHECK (provider IN ('saml', 'ldap', 'ipa', 'oauth', 'auth_proxy', 'okta')),
    external_subject text NOT NULL,
    local_subject text NOT NULL,
    external_groups_digest text NOT NULL CHECK (external_groups_digest ~ '^[0-9a-f]{64}$'),
    last_authenticated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, provider, external_subject),
    FOREIGN KEY (tenant_id, local_subject)
        REFERENCES identity_users(tenant_id, username) ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

DO $$
DECLARE
    partition_index integer;
    partition_suffix text;
BEGIN
    FOR partition_index IN 0..31 LOOP
        partition_suffix := lpad(partition_index::text, 2, '0');
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I '
            'PARTITION OF identity_team_sync_sources FOR VALUES WITH (MODULUS 32, REMAINDER %s)',
            'identity_team_sync_sources_p' || partition_suffix,
            partition_index
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I '
            'PARTITION OF identity_team_sync_runs FOR VALUES WITH (MODULUS 32, REMAINDER %s)',
            'identity_team_sync_runs_p' || partition_suffix,
            partition_index
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I '
            'PARTITION OF federated_identity_links FOR VALUES WITH (MODULUS 32, REMAINDER %s)',
            'federated_identity_links_p' || partition_suffix,
            partition_index
        );
    END LOOP;
END
$$;

CREATE INDEX IF NOT EXISTS idx_identity_team_sync_sources_provider
ON identity_team_sync_sources (tenant_id, provider, source_id);

CREATE INDEX IF NOT EXISTS idx_identity_team_sync_runs_created
ON identity_team_sync_runs (tenant_id, source_id, created_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_federated_identity_links_local
ON federated_identity_links (tenant_id, local_subject, provider);

CREATE INDEX IF NOT EXISTS idx_audit_events_federated_identity
ON audit_events (tenant_id, action, created_at DESC)
WHERE action LIKE 'auth.saml.%' OR action LIKE 'identity.team_sync.%';

COMMIT;
