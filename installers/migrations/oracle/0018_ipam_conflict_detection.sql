-- Generated deterministically from installers/migrations/postgresql/0018_ipam_conflict_detection.sql.
-- Source SHA-256: 9c53e14dbba4fdbce76830910b1cb1079db95d731cf9732ae42c0a5a681339bd
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE ipam_dns_observations (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    hostname VARCHAR2(255 CHAR) NOT NULL,
    address VARCHAR2(64 CHAR) NOT NULL,
    ptr_hostname VARCHAR2(255 CHAR) NULL,
    source VARCHAR2(255 CHAR) NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, vrf_name, hostname, address)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE ipam_dhcp_leases (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    prefix_cidr VARCHAR2(64 CHAR) NOT NULL,
    address VARCHAR2(64 CHAR) NOT NULL,
    mac_address VARCHAR2(255 CHAR) NOT NULL,
    hostname VARCHAR2(255 CHAR) NOT NULL,
    source VARCHAR2(255 CHAR) NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, vrf_name, prefix_cidr, address, mac_address)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE ipam_conflict_scan_events (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    vrf_name VARCHAR2(255 CHAR) NULL,
    conflict_count NUMBER(10) NOT NULL,
    by_severity CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ck_ipam_conflict_scan_events_by_severity_json CHECK (by_severity IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_ipam_dns_observations_address
    ON ipam_dns_observations (tenant_id, vrf_name, address);

CREATE INDEX idx_ipam_dns_observations_ptr
    ON ipam_dns_observations (tenant_id, vrf_name, ptr_hostname);

CREATE INDEX idx_ipam_dhcp_leases_address_active
    ON ipam_dhcp_leases (tenant_id, vrf_name, address);

CREATE INDEX idx_ipam_conflict_scan_events_created
    ON ipam_conflict_scan_events (tenant_id, created_at DESC);

CREATE INDEX idx_ipam_conflict_audit_events
    ON audit_events (tenant_id, action, created_at DESC);
