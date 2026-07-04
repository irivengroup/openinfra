-- OpenInfra v0.28.0 - P07 / EPIC-0701 Discovery collector registry and strong identity

CREATE TABLE IF NOT EXISTS discovery_collectors (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name text NOT NULL,
    kind text NOT NULL,
    certificate_fingerprint text NOT NULL,
    vault_secret_ref text NULL,
    scopes jsonb NOT NULL,
    version text NOT NULL,
    endpoint_url text NULL,
    status text NOT NULL,
    registered_by text NOT NULL,
    registered_at timestamptz NOT NULL DEFAULT now(),
    last_heartbeat_at timestamptz NULL,
    last_heartbeat_status text NULL,
    last_seen_version text NULL,
    disabled_reason text NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT discovery_collectors_name_not_blank CHECK (length(trim(name)) >= 2),
    CONSTRAINT discovery_collectors_kind_check CHECK (
        kind IN ('snmp', 'ssh', 'winrm', 'vmware', 'proxmox', 'hyperv', 'kubernetes', 'cloud', 'generic')
    ),
    CONSTRAINT discovery_collectors_fingerprint_check CHECK (certificate_fingerprint ~ '^[a-f0-9]{64}$'),
    CONSTRAINT discovery_collectors_vault_ref_check CHECK (
        vault_secret_ref IS NULL OR vault_secret_ref ~ '^vault://[A-Za-z0-9][A-Za-z0-9_./:-]{2,255}$'
    ),
    CONSTRAINT discovery_collectors_scopes_check CHECK (jsonb_typeof(scopes) = 'array' AND jsonb_array_length(scopes) >= 1),
    CONSTRAINT discovery_collectors_status_check CHECK (status IN ('active', 'disabled', 'stale')),
    CONSTRAINT discovery_collectors_heartbeat_status_check CHECK (
        last_heartbeat_status IS NULL OR last_heartbeat_status IN ('ok', 'degraded', 'maintenance')
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS discovery_collectors_p00 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS discovery_collectors_p01 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS discovery_collectors_p02 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS discovery_collectors_p03 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS discovery_collectors_p04 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS discovery_collectors_p05 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS discovery_collectors_p06 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS discovery_collectors_p07 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS discovery_collectors_p08 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS discovery_collectors_p09 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS discovery_collectors_p10 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS discovery_collectors_p11 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS discovery_collectors_p12 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS discovery_collectors_p13 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS discovery_collectors_p14 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS discovery_collectors_p15 PARTITION OF discovery_collectors
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE UNIQUE INDEX IF NOT EXISTS idx_discovery_collectors_fingerprint_tenant
    ON discovery_collectors (tenant_id, certificate_fingerprint);
CREATE INDEX IF NOT EXISTS idx_discovery_collectors_status_kind
    ON discovery_collectors (tenant_id, status, kind);
CREATE INDEX IF NOT EXISTS idx_discovery_collectors_scopes_gin
    ON discovery_collectors USING gin (scopes);
CREATE INDEX IF NOT EXISTS idx_discovery_collectors_heartbeat
    ON discovery_collectors (tenant_id, last_heartbeat_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_discovery_collectors
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('discovery_collector', 'discovery_job');
