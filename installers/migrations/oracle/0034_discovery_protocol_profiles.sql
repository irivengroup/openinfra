-- Generated deterministically from installers/migrations/postgresql/0034_discovery_protocol_profiles.sql.
-- Source SHA-256: 1db8f975bb1262067e119c86a97f7787f72b4140350d8e5b6a08326a379fa558
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE discovery_protocol_profiles (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR2(255 CHAR) NOT NULL,
    protocol VARCHAR2(255 CHAR) NOT NULL,
    scope VARCHAR2(255 CHAR) NOT NULL,
    credential_secret_ref VARCHAR2(255 CHAR) NOT NULL,
    port NUMBER(10) NOT NULL,
    timeout_seconds NUMBER(10) NOT NULL,
    max_concurrency NUMBER(10) NOT NULL,
    rate_limit_per_minute NUMBER(10) NOT NULL,
    retry_count NUMBER(10) NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    disabled_reason VARCHAR2(1000 CHAR) NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT discovery_protocol_profiles_name_not_blank CHECK (length(trim(name)) >= 2),
    CONSTRAINT discovery_protocol_profiles_protocol_valid CHECK (protocol IN ('snmp', 'ssh', 'winrm')),
    CONSTRAINT discovery_protocol_profiles_scope_valid CHECK (REGEXP_LIKE(scope, '^[a-z0-9][a-z0-9_.:/-]{1,127}$')),
    CONSTRAINT discovery_protocol_profiles_secret_ref_valid CHECK (
        REGEXP_LIKE(credential_secret_ref, '^vault://[A-Za-z0-9][A-Za-z0-9_./:-]{2,255}$')
    ),
    CONSTRAINT discovery_protocol_profiles_port_valid CHECK (port BETWEEN 1 AND 65535),
    CONSTRAINT discovery_protocol_profiles_winrm_https CHECK (protocol <> 'winrm' OR port <> 5985),
    CONSTRAINT discovery_protocol_profiles_timeout_valid CHECK (timeout_seconds BETWEEN 1 AND 300),
    CONSTRAINT discovery_protocol_profiles_concurrency_valid CHECK (max_concurrency BETWEEN 1 AND 64),
    CONSTRAINT discovery_protocol_profiles_rate_limit_valid CHECK (rate_limit_per_minute BETWEEN 1 AND 10000),
    CONSTRAINT discovery_protocol_profiles_retry_valid CHECK (retry_count BETWEEN 0 AND 5),
    CONSTRAINT discovery_protocol_profiles_status_valid CHECK (status IN ('active', 'disabled')),
    CONSTRAINT discovery_protocol_profiles_actor_not_blank CHECK (length(trim(created_by)) >= 1)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_discovery_protocol_profiles_active
    ON discovery_protocol_profiles (tenant_id, protocol, scope, id);

CREATE INDEX idx_discovery_protocol_profiles_rate_limit
    ON discovery_protocol_profiles (tenant_id, protocol, rate_limit_per_minute, max_concurrency);

CREATE INDEX idx_audit_events_discovery_protocol_profiles
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
