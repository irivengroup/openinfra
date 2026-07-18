-- Generated deterministically from installers/migrations/postgresql/0023_discovery_collector_registry.sql.
-- Source SHA-256: 8ae324b5562be65fbd04a72b67e5e7d5b00cf52504a9cf857c692b6fd5fa958d
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE discovery_collectors (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR2(255 CHAR) NOT NULL,
    kind VARCHAR2(255 CHAR) NOT NULL,
    certificate_fingerprint VARCHAR2(255 CHAR) NOT NULL,
    vault_secret_ref VARCHAR2(255 CHAR) NULL,
    scopes CLOB NOT NULL,
    version VARCHAR2(255 CHAR) NOT NULL,
    endpoint_url VARCHAR2(1000 CHAR) NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    registered_by VARCHAR2(255 CHAR) NOT NULL,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    last_heartbeat_at TIMESTAMP WITH TIME ZONE NULL,
    last_heartbeat_status VARCHAR2(128 CHAR) NULL,
    last_seen_version VARCHAR2(255 CHAR) NULL,
    disabled_reason VARCHAR2(1000 CHAR) NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT discovery_collectors_name_not_blank CHECK (length(trim(name)) >= 2),
    CONSTRAINT discovery_collectors_kind_check CHECK (
        kind IN ('snmp', 'ssh', 'winrm', 'vmware', 'proxmox', 'hyperv', 'kubernetes', 'cloud', 'generic')
    ),
    CONSTRAINT discovery_collectors_fingerprint_check CHECK (REGEXP_LIKE(certificate_fingerprint, '^[a-f0-9]{64}$')),
    CONSTRAINT discovery_collectors_vault_ref_check CHECK (
        vault_secret_ref IS NULL OR REGEXP_LIKE(vault_secret_ref, '^vault://[A-Za-z0-9][A-Za-z0-9_./:-]{2,255}$')
    ),
    CONSTRAINT discovery_collectors_scopes_check CHECK (JSON_EXISTS(scopes, '$?(@.type() == \"array\")') AND JSON_EXISTS(scopes, '$[0]')),
    CONSTRAINT discovery_collectors_status_check CHECK (status IN ('active', 'disabled', 'stale')),
    CONSTRAINT discovery_collectors_heartbeat_status_check CHECK (
        last_heartbeat_status IS NULL OR last_heartbeat_status IN ('ok', 'degraded', 'maintenance')
    ),
    CONSTRAINT ck_discovery_collectors_scopes_json CHECK (scopes IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE UNIQUE INDEX idx_discovery_collectors_fingerprint_tenant
    ON discovery_collectors (tenant_id, certificate_fingerprint);

CREATE INDEX idx_discovery_collectors_status_kind
    ON discovery_collectors (tenant_id, status, kind);

CREATE INDEX idx_discovery_collectors_heartbeat
    ON discovery_collectors (tenant_id, last_heartbeat_at DESC);

CREATE INDEX idx_audit_events_discovery_collectors
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
