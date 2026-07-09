-- OpenInfra v0.29.81 - P14 / EPIC-1404 virtualization, Kubernetes and cloud discovery profiles

BEGIN;

CREATE TABLE IF NOT EXISTS discovery_integration_profiles (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name text NOT NULL,
    kind text NOT NULL,
    scope text NOT NULL,
    endpoint_url text NULL,
    credential_secret_ref text NOT NULL,
    verify_tls boolean NOT NULL DEFAULT true,
    inventory_enabled boolean NOT NULL DEFAULT true,
    max_concurrency integer NOT NULL,
    rate_limit_per_minute integer NOT NULL,
    status text NOT NULL DEFAULT 'active',
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    disabled_reason text NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT discovery_integration_profiles_name_not_blank CHECK (length(trim(name)) >= 2),
    CONSTRAINT discovery_integration_profiles_kind_valid CHECK (
        kind IN ('vmware', 'proxmox', 'hyperv', 'kubernetes', 'aws', 'azure', 'gcp', 'openstack')
    ),
    CONSTRAINT discovery_integration_profiles_scope_valid CHECK (
        scope ~ '^[a-z0-9][a-z0-9_.:/-]{1,127}$'
    ),
    CONSTRAINT discovery_integration_profiles_endpoint_https CHECK (
        endpoint_url IS NULL OR endpoint_url ~ '^https://[^[:space:]]{3,255}$'
    ),
    CONSTRAINT discovery_integration_profiles_endpoint_required CHECK (
        kind IN ('aws', 'azure', 'gcp') OR endpoint_url IS NOT NULL
    ),
    CONSTRAINT discovery_integration_profiles_secret_ref_valid CHECK (
        credential_secret_ref ~ '^vault://[A-Za-z0-9][A-Za-z0-9_./:-]{2,255}$'
    ),
    CONSTRAINT discovery_integration_profiles_concurrency_valid CHECK (
        max_concurrency BETWEEN 1 AND 64
    ),
    CONSTRAINT discovery_integration_profiles_rate_limit_valid CHECK (
        rate_limit_per_minute BETWEEN 1 AND 10000
    ),
    CONSTRAINT discovery_integration_profiles_status_valid CHECK (status IN ('active', 'disabled')),
    CONSTRAINT discovery_integration_profiles_actor_not_blank CHECK (length(trim(created_by)) >= 1)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p00 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p01 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p02 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p03 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p04 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p05 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p06 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p07 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p08 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p09 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p10 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p11 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p12 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p13 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p14 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS discovery_integration_profiles_p15 PARTITION OF discovery_integration_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_discovery_integration_profiles_active
    ON discovery_integration_profiles (tenant_id, kind, scope, id)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_discovery_integration_profiles_rate_limit
    ON discovery_integration_profiles (tenant_id, kind, rate_limit_per_minute, max_concurrency)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_audit_events_discovery_integration_profiles
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'discovery_integration_profile';

COMMIT;
