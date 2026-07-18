-- Generated deterministically from installers/migrations/postgresql/0037_discovery_integration_profiles.sql.
-- Source SHA-256: c905d062dd977c0f64bcf80d73d4fdc119c40036cc4d9a6cc8ff5394bc946511
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE discovery_integration_profiles (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR2(255 CHAR) NOT NULL,
    kind VARCHAR2(255 CHAR) NOT NULL,
    scope VARCHAR2(255 CHAR) NOT NULL,
    endpoint_url VARCHAR2(1000 CHAR) NULL,
    credential_secret_ref VARCHAR2(255 CHAR) NOT NULL,
    verify_tls NUMBER(1) DEFAULT 1 NOT NULL,
    inventory_enabled NUMBER(1) DEFAULT 1 NOT NULL,
    max_concurrency NUMBER(10) NOT NULL,
    rate_limit_per_minute NUMBER(10) NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    disabled_reason VARCHAR2(1000 CHAR) NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT discovery_integration_profiles_name_not_blank CHECK (length(trim(name)) >= 2),
    CONSTRAINT discovery_integration_profiles_kind_valid CHECK (
        kind IN ('vmware', 'proxmox', 'hyperv', 'kubernetes', 'aws', 'azure', 'gcp', 'openstack')
    ),
    CONSTRAINT discovery_integration_profiles_scope_valid CHECK (
        REGEXP_LIKE(scope, '^[a-z0-9][a-z0-9_.:/-]{1,127}$')
    ),
    CONSTRAINT discovery_integration_profiles_endpoint_https CHECK (
        endpoint_url IS NULL OR REGEXP_LIKE(endpoint_url, '^https://[^[:space:]]{3,255}$')
    ),
    CONSTRAINT discovery_integration_profiles_endpoint_required CHECK (
        kind IN ('aws', 'azure', 'gcp') OR endpoint_url IS NOT NULL
    ),
    CONSTRAINT discovery_integration_profiles_secret_ref_valid CHECK (
        REGEXP_LIKE(credential_secret_ref, '^vault://[A-Za-z0-9][A-Za-z0-9_./:-]{2,255}$')
    ),
    CONSTRAINT discovery_integration_profiles_concurrency_valid CHECK (
        max_concurrency BETWEEN 1 AND 64
    ),
    CONSTRAINT discovery_integration_profiles_rate_limit_valid CHECK (
        rate_limit_per_minute BETWEEN 1 AND 10000
    ),
    CONSTRAINT discovery_integration_profiles_status_valid CHECK (status IN ('active', 'disabled')),
    CONSTRAINT discovery_integration_profiles_actor_not_blank CHECK (length(trim(created_by)) >= 1)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_discovery_integration_profiles_active
    ON discovery_integration_profiles (tenant_id, kind, scope, id);

CREATE INDEX idx_discovery_integration_profiles_rate_limit
    ON discovery_integration_profiles (tenant_id, kind, rate_limit_per_minute, max_concurrency);

CREATE INDEX idx_audit_events_discovery_integration_profiles
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
