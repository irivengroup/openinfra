-- OpenInfra PostgreSQL migration 0017
-- P05 / EPIC-0503 - VLAN/VXLAN/ASN/BGP foundation.

BEGIN;

CREATE TABLE IF NOT EXISTS ipam_vlan_groups (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name text NOT NULL,
    scope text,
    description text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_vlan_groups_name_not_blank CHECK (length(trim(name)) > 0),
    CONSTRAINT ipam_vlan_groups_scope_safe CHECK (scope IS NULL OR scope ~ '^[A-Z0-9][A-Z0-9_.:-]{0,63}$'),
    UNIQUE (tenant_id, name)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p00 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p01 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p02 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p03 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p04 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p05 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p06 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p07 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p08 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p09 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p10 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p11 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p12 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p13 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p14 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS ipam_vlan_groups_p15 PARTITION OF ipam_vlan_groups FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vni integer NOT NULL,
    name text NOT NULL,
    vrf_name text NOT NULL,
    route_targets_import text[] NOT NULL DEFAULT ARRAY[]::text[],
    route_targets_export text[] NOT NULL DEFAULT ARRAY[]::text[],
    description text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_vxlan_vnis_range CHECK (vni BETWEEN 1 AND 16777215),
    CONSTRAINT ipam_vxlan_vnis_name_not_blank CHECK (length(trim(name)) > 0),
    CONSTRAINT ipam_vxlan_vnis_vrf_not_blank CHECK (length(trim(vrf_name)) > 0),
    UNIQUE (tenant_id, vni)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p00 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p01 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p02 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p03 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p04 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p05 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p06 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p07 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p08 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p09 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p10 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p11 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p12 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p13 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p14 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS ipam_vxlan_vnis_p15 PARTITION OF ipam_vxlan_vnis FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_ipam_vxlan_vnis_vrf
    ON ipam_vxlan_vnis (tenant_id, vrf_name, vni);

CREATE TABLE IF NOT EXISTS ipam_vlans (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    group_name text NOT NULL,
    vlan_id integer NOT NULL,
    name text NOT NULL,
    vrf_name text,
    vni integer,
    description text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_vlans_id_range CHECK (vlan_id BETWEEN 1 AND 4094),
    CONSTRAINT ipam_vlans_vni_range CHECK (vni IS NULL OR vni BETWEEN 1 AND 16777215),
    CONSTRAINT ipam_vlans_group_not_blank CHECK (length(trim(group_name)) > 0),
    CONSTRAINT ipam_vlans_name_not_blank CHECK (length(trim(name)) > 0),
    CONSTRAINT ipam_vlans_vni_requires_vrf CHECK (vni IS NULL OR vrf_name IS NOT NULL),
    UNIQUE (tenant_id, group_name, vlan_id)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS ipam_vlans_p00 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS ipam_vlans_p01 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS ipam_vlans_p02 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS ipam_vlans_p03 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS ipam_vlans_p04 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS ipam_vlans_p05 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS ipam_vlans_p06 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS ipam_vlans_p07 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS ipam_vlans_p08 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS ipam_vlans_p09 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS ipam_vlans_p10 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS ipam_vlans_p11 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS ipam_vlans_p12 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS ipam_vlans_p13 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS ipam_vlans_p14 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS ipam_vlans_p15 PARTITION OF ipam_vlans FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_ipam_vlans_vrf
    ON ipam_vlans (tenant_id, vrf_name, vlan_id);

CREATE INDEX IF NOT EXISTS idx_ipam_vlans_vni
    ON ipam_vlans (tenant_id, vni)
    WHERE vni IS NOT NULL;

CREATE TABLE IF NOT EXISTS ipam_autonomous_systems (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asn bigint NOT NULL,
    name text NOT NULL,
    description text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ipam_autonomous_systems_range CHECK (asn BETWEEN 1 AND 4294967295),
    CONSTRAINT ipam_autonomous_systems_name_not_blank CHECK (length(trim(name)) > 0),
    UNIQUE (tenant_id, asn)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p00 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p01 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p02 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p03 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p04 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p05 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p06 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p07 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p08 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p09 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p10 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p11 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p12 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p13 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p14 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS ipam_autonomous_systems_p15 PARTITION OF ipam_autonomous_systems FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE TABLE IF NOT EXISTS ipam_bgp_peers (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vrf_name text NOT NULL,
    local_asn bigint NOT NULL,
    remote_asn bigint NOT NULL,
    peer_address inet NOT NULL,
    address_family text NOT NULL,
    route_targets_import text[] NOT NULL DEFAULT ARRAY[]::text[],
    route_targets_export text[] NOT NULL DEFAULT ARRAY[]::text[],
    description text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
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
    UNIQUE (tenant_id, vrf_name, local_asn, peer_address)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p00 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p01 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p02 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p03 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p04 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p05 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p06 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p07 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p08 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p09 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p10 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p11 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p12 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p13 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p14 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS ipam_bgp_peers_p15 PARTITION OF ipam_bgp_peers FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_ipam_bgp_peers_vrf
    ON ipam_bgp_peers (tenant_id, vrf_name, local_asn, remote_asn);

CREATE INDEX IF NOT EXISTS idx_ipam_bgp_peers_remote_asn
    ON ipam_bgp_peers (tenant_id, remote_asn);

CREATE INDEX IF NOT EXISTS idx_ipam_networking_audit_events
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action LIKE 'ipam.%';

COMMIT;
