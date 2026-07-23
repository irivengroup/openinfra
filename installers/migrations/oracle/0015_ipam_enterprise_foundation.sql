-- Generated deterministically from installers/migrations/postgresql/0015_ipam_enterprise_foundation.sql.
-- Source SHA-256: c8c3239524b61976da45443c7caf330668ad3e2596142248606ed90554fce416
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE prefixes ADD (family NUMBER(5));

UPDATE prefixes SET family = CASE WHEN INSTR(prefixes.cidr, ':') > 0 THEN 6 ELSE 4 END WHERE prefixes.family IS NULL;

ALTER TABLE prefixes MODIFY (family NOT NULL);

ALTER TABLE prefixes ADD CONSTRAINT prefixes_family_check CHECK (family IN (4, 6));

ALTER TABLE prefixes ENABLE VALIDATE CONSTRAINT prefixes_family_check;

CREATE TABLE ip_aggregates (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    cidr VARCHAR2(64 CHAR) NOT NULL,
    family NUMBER(5) NOT NULL,
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, vrf_name, cidr),
    CHECK (family IN (4, 6))
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE ip_ranges (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    prefix_cidr VARCHAR2(64 CHAR) NOT NULL,
    start_address VARCHAR2(64 CHAR) NOT NULL,
    end_address VARCHAR2(64 CHAR) NOT NULL,
    purpose VARCHAR2(255 CHAR) NOT NULL,
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, vrf_name, prefix_cidr, start_address, end_address),
    CHECK (purpose IN ('allocation', 'reservation', 'exclusion')),
    CHECK (pg_catalog.family(start_address) = pg_catalog.family(end_address)),
    CHECK (start_address <= end_address)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE ip_address_records (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    prefix_cidr VARCHAR2(64 CHAR) NOT NULL,
    address VARCHAR2(64 CHAR) NOT NULL,
    hostname VARCHAR2(255 CHAR) NOT NULL,
    interface_name VARCHAR2(255 CHAR),
    status VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, vrf_name, address),
    CHECK (status IN ('planned', 'reserved', 'active', 'deprecated'))
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE INDEX idx_ip_aggregates_vrf_family ON ip_aggregates (tenant_id, vrf_name, family, cidr);

CREATE INDEX idx_prefixes_vrf_family ON prefixes (tenant_id, vrf_name, family, cidr);

CREATE INDEX idx_ip_ranges_lookup ON ip_ranges (tenant_id, vrf_name, prefix_cidr, start_address, end_address);

CREATE INDEX idx_ip_address_records_lookup ON ip_address_records (tenant_id, vrf_name, prefix_cidr, address);

CREATE INDEX idx_ipam_audit_events ON audit_events (tenant_id, action, created_at DESC);
