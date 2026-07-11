-- OpenInfra 0.29.103 / EPIC-1702: Enterprise regional discovery routing.
BEGIN;

ALTER TABLE discovery_collectors
    DROP CONSTRAINT IF EXISTS discovery_collectors_kind_check;
ALTER TABLE discovery_collectors
    ADD CONSTRAINT discovery_collectors_kind_check CHECK (
        kind IN (
            'snmp', 'ssh', 'winrm', 'vmware', 'proxmox', 'hyperv',
            'kubernetes', 'cloud', 'site-proxy', 'network-proxy',
            'datacenter-proxy', 'generic'
        )
    );

CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes (
    id uuid NOT NULL,
    tenant_id varchar(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    region_code varchar(64) NOT NULL,
    site_code varchar(64) NOT NULL,
    vrf_code varchar(64) NOT NULL,
    collector_id uuid NOT NULL,
    discovery_scope varchar(256) NOT NULL,
    active boolean NOT NULL DEFAULT TRUE,
    configured_by varchar(128) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    disabled_at timestamptz NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, region_code, site_code, vrf_code),
    FOREIGN KEY (tenant_id, collector_id)
        REFERENCES discovery_collectors (tenant_id, id) ON DELETE RESTRICT,
    CHECK (region_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
    CHECK (site_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
    CHECK (vrf_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
    CHECK (
        discovery_scope =
            'region/' || lower(region_code) ||
            '/site/' || lower(site_code) ||
            '/vrf/' || lower(vrf_code)
    ),
    CHECK ((active AND disabled_at IS NULL) OR (NOT active AND disabled_at IS NOT NULL))
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p0
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p1
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p2
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p3
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p4
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p5
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p6
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes_p7
    PARTITION OF multisite_regional_discovery_routes FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_multisite_regional_routes_lookup
    ON multisite_regional_discovery_routes (
        tenant_id, region_code, site_code, vrf_code, active
    );
CREATE INDEX IF NOT EXISTS idx_multisite_regional_routes_collector
    ON multisite_regional_discovery_routes (tenant_id, collector_id, active);
CREATE INDEX IF NOT EXISTS idx_audit_events_multisite_regional_discovery
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('regional_discovery_route', 'discovery_job');

COMMIT;
