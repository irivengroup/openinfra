-- OpenInfra PostgreSQL migration 0018
-- EPIC-0504: IPAM conflict detection observations and scan evidence.

CREATE TABLE IF NOT EXISTS ipam_dns_observations (
    id uuid NOT NULL,
    tenant_id text NOT NULL,
    vrf_name text NOT NULL,
    hostname text NOT NULL,
    address inet NOT NULL,
    ptr_hostname text NULL,
    source text NOT NULL,
    observed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, vrf_name, hostname, address)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS ipam_dhcp_leases (
    id uuid NOT NULL,
    tenant_id text NOT NULL,
    vrf_name text NOT NULL,
    prefix_cidr cidr NOT NULL,
    address inet NOT NULL,
    mac_address text NOT NULL,
    hostname text NOT NULL,
    source text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    observed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, vrf_name, prefix_cidr, address, mac_address)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS ipam_conflict_scan_events (
    id uuid NOT NULL,
    tenant_id text NOT NULL,
    vrf_name text NULL,
    conflict_count integer NOT NULL,
    by_severity jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
) PARTITION BY HASH (tenant_id);

DO $$
DECLARE
    partition_index integer;
BEGIN
    FOR partition_index IN 0..15 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS ipam_dns_observations_p%s PARTITION OF ipam_dns_observations FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
            partition_index,
            partition_index
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS ipam_dhcp_leases_p%s PARTITION OF ipam_dhcp_leases FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
            partition_index,
            partition_index
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS ipam_conflict_scan_events_p%s PARTITION OF ipam_conflict_scan_events FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
            partition_index,
            partition_index
        );
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS idx_ipam_dns_observations_address
    ON ipam_dns_observations (tenant_id, vrf_name, address);

CREATE INDEX IF NOT EXISTS idx_ipam_dns_observations_ptr
    ON ipam_dns_observations (tenant_id, vrf_name, ptr_hostname)
    WHERE ptr_hostname IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ipam_dhcp_leases_address_active
    ON ipam_dhcp_leases (tenant_id, vrf_name, address)
    WHERE active = true;

CREATE INDEX IF NOT EXISTS idx_ipam_conflict_scan_events_created
    ON ipam_conflict_scan_events (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ipam_conflict_audit_events
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action IN (
        'ipam.dns_observation.recorded',
        'ipam.dhcp_lease.observed',
        'ipam.conflicts.detected'
    );
