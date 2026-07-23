-- Generated deterministically from installers/migrations/postgresql/0051_enterprise_regional_discovery_routing.sql.
-- Source SHA-256: 8ef2a79797896534d82c450fb87d70d8d8299441cfb8fdf8b107650e9b608199
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE discovery_collectors DROP CONSTRAINT discovery_collectors_kind_check;

ALTER TABLE discovery_collectors ADD CONSTRAINT discovery_collectors_kind_check CHECK (
        kind IN (
            'snmp', 'ssh', 'winrm', 'vmware', 'proxmox', 'hyperv',
            'kubernetes', 'cloud', 'site-proxy', 'network-proxy',
            'datacenter-proxy', 'generic'
        )
    );

CREATE TABLE multisite_regional_discovery_routes (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(64 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    region_code VARCHAR2(64 CHAR) NOT NULL,
    site_code VARCHAR2(64 CHAR) NOT NULL,
    vrf_code VARCHAR2(64 CHAR) NOT NULL,
    collector_id VARCHAR2(36 CHAR) NOT NULL,
    discovery_scope VARCHAR2(256 CHAR) NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    configured_by VARCHAR2(128 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    disabled_at TIMESTAMP WITH TIME ZONE NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, region_code, site_code, vrf_code),
    FOREIGN KEY (tenant_id, collector_id)
        REFERENCES discovery_collectors (tenant_id, id),
    CHECK (REGEXP_LIKE(region_code, '^[A-Z0-9][A-Z0-9_-]{1,63}$')),
    CHECK (REGEXP_LIKE(site_code, '^[A-Z0-9][A-Z0-9_-]{1,63}$')),
    CHECK (REGEXP_LIKE(vrf_code, '^[A-Z0-9][A-Z0-9_-]{1,63}$')),
    CHECK (
        discovery_scope =
            'region/' || lower(region_code) ||
            '/site/' || lower(site_code) ||
            '/vrf/' || lower(vrf_code)
    ),
    CHECK ((active AND disabled_at IS NULL) OR (NOT active AND disabled_at IS NOT NULL)),
    CONSTRAINT ck_multisite_regional_discovery_routes_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_multisite_regional_routes_lookup
    ON multisite_regional_discovery_routes (
        tenant_id, region_code, site_code, vrf_code, active
    );

CREATE INDEX idx_multisite_regional_routes_collector
    ON multisite_regional_discovery_routes (tenant_id, collector_id, active);

CREATE INDEX idx_audit_events_multisite_regional_discovery
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
