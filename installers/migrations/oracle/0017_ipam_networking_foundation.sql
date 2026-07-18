-- Generated deterministically from installers/migrations/postgresql/0017_ipam_networking_foundation.sql.
-- Source SHA-256: b687d12754e1e43245eb39e838cc60ef4dcd09206d680ea499c59807443ea6c8
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE ipam_vlan_groups (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR2(255 CHAR) NOT NULL,
    scope VARCHAR2(255 CHAR),
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_vlan_groups_name_not_blank CHECK (length(trim(name)) > 0),
    CONSTRAINT ipam_vlan_groups_scope_safe CHECK (scope IS NULL OR REGEXP_LIKE(scope, '^[A-Z0-9][A-Z0-9_.:-]{0,63}$')),
    UNIQUE (tenant_id, name)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE ipam_vxlan_vnis (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vni NUMBER(10) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    route_targets_import CLOB DEFAULT '[]' NOT NULL,
    route_targets_export CLOB DEFAULT '[]' NOT NULL,
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_vxlan_vnis_range CHECK (vni BETWEEN 1 AND 16777215),
    CONSTRAINT ipam_vxlan_vnis_name_not_blank CHECK (length(trim(name)) > 0),
    CONSTRAINT ipam_vxlan_vnis_vrf_not_blank CHECK (length(trim(vrf_name)) > 0),
    UNIQUE (tenant_id, vni),
    CONSTRAINT ck_ipam_vxlan_vnis_route_targets_import_json CHECK (route_targets_import IS JSON),
    CONSTRAINT ck_ipam_vxlan_vnis_route_targets_export_json CHECK (route_targets_export IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_ipam_vxlan_vnis_vrf
    ON ipam_vxlan_vnis (tenant_id, vrf_name, vni);

CREATE TABLE ipam_vlans (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    group_name VARCHAR2(255 CHAR) NOT NULL,
    vlan_id NUMBER(10) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    vrf_name VARCHAR2(255 CHAR),
    vni NUMBER(10),
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_vlans_id_range CHECK (vlan_id BETWEEN 1 AND 4094),
    CONSTRAINT ipam_vlans_vni_range CHECK (vni IS NULL OR vni BETWEEN 1 AND 16777215),
    CONSTRAINT ipam_vlans_group_not_blank CHECK (length(trim(group_name)) > 0),
    CONSTRAINT ipam_vlans_name_not_blank CHECK (length(trim(name)) > 0),
    CONSTRAINT ipam_vlans_vni_requires_vrf CHECK (vni IS NULL OR vrf_name IS NOT NULL),
    UNIQUE (tenant_id, group_name, vlan_id)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_ipam_vlans_vrf
    ON ipam_vlans (tenant_id, vrf_name, vlan_id);

CREATE INDEX idx_ipam_vlans_vni
    ON ipam_vlans (tenant_id, vni);

CREATE TABLE ipam_autonomous_systems (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asn NUMBER(19) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_autonomous_systems_range CHECK (asn BETWEEN 1 AND 4294967295),
    CONSTRAINT ipam_autonomous_systems_name_not_blank CHECK (length(trim(name)) > 0),
    UNIQUE (tenant_id, asn)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE ipam_bgp_peers (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    local_asn NUMBER(19) NOT NULL,
    remote_asn NUMBER(19) NOT NULL,
    peer_address VARCHAR2(64 CHAR) NOT NULL,
    address_family VARCHAR2(255 CHAR) NOT NULL,
    route_targets_import CLOB DEFAULT '[]' NOT NULL,
    route_targets_export CLOB DEFAULT '[]' NOT NULL,
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_bgp_peers_vrf_not_blank CHECK (length(trim(vrf_name)) > 0),
    CONSTRAINT ipam_bgp_peers_local_asn_range CHECK (local_asn BETWEEN 1 AND 4294967295),
    CONSTRAINT ipam_bgp_peers_remote_asn_range CHECK (remote_asn BETWEEN 1 AND 4294967295),
    CONSTRAINT ipam_bgp_peers_distinct_asn CHECK (local_asn <> remote_asn),
    CONSTRAINT ipam_bgp_peers_family CHECK (address_family IN ('ipv4', 'ipv6')),
    CONSTRAINT ipam_bgp_peers_family_matches_address CHECK (
        (address_family = 'ipv4' AND pg_catalog.family(peer_address) = 4)
        OR (address_family = 'ipv6' AND pg_catalog.family(peer_address) = 6)
    ),
    UNIQUE (tenant_id, vrf_name, local_asn, peer_address),
    CONSTRAINT ck_ipam_bgp_peers_route_targets_import_json CHECK (route_targets_import IS JSON),
    CONSTRAINT ck_ipam_bgp_peers_route_targets_export_json CHECK (route_targets_export IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_ipam_bgp_peers_vrf
    ON ipam_bgp_peers (tenant_id, vrf_name, local_asn, remote_asn);

CREATE INDEX idx_ipam_bgp_peers_remote_asn
    ON ipam_bgp_peers (tenant_id, remote_asn);

CREATE INDEX idx_ipam_networking_audit_events
    ON audit_events (tenant_id, action, created_at DESC);
