-- Generated deterministically from installers/migrations/postgresql/0001_bootstrap.sql.
-- Source SHA-256: a9507fb1755c88e287cffeafd2f751ff0756f4894b4041a866552f92d446ae0f
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE openinfra_document_state (
    state_key VARCHAR2(64 CHAR) PRIMARY KEY,
    payload CLOB NOT NULL,
    version NUMBER(19) DEFAULT 0 NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT ck_openinfra_state_payload CHECK (payload IS JSON)
);

MERGE INTO openinfra_document_state target
USING (SELECT 'global' AS state_key, '{}' AS payload FROM dual) source
ON (target.state_key = source.state_key)
WHEN NOT MATCHED THEN INSERT (state_key, payload, version) VALUES (source.state_key, source.payload, 0);

CREATE TABLE tenants (
    id VARCHAR2(255 CHAR) PRIMARY KEY,
    display_name VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CHECK (REGEXP_LIKE(id, '^[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]$'))
);

CREATE TABLE sites (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    code VARCHAR2(255 CHAR) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    country CHAR(2 CHAR) NOT NULL,
    city VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE buildings (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    site_code VARCHAR2(128 CHAR) NOT NULL,
    code VARCHAR2(255 CHAR) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, code)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE TABLE rooms (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    code VARCHAR2(255 CHAR) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    "ROWS" CLOB NOT NULL,
    columns CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, code),
    CHECK (JSON_EXISTS("ROWS", '$[0]')),
    CHECK (JSON_EXISTS(columns, '$[0]')),
    CONSTRAINT ck_rooms_rows_json CHECK ("ROWS" IS JSON),
    CONSTRAINT ck_rooms_columns_json CHECK (columns IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE TABLE racks (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    code VARCHAR2(255 CHAR) NOT NULL,
    row_code VARCHAR2(128 CHAR) NOT NULL,
    column_code VARCHAR2(128 CHAR) NOT NULL,
    units NUMBER(10) NOT NULL,
    coordinate_x NUMBER(12, 3),
    coordinate_y NUMBER(12, 3),
    coordinate_z NUMBER(12, 3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, room_code, code),
    CHECK (units BETWEEN 1 AND 60),
    CHECK ((coordinate_x IS NULL AND coordinate_y IS NULL AND coordinate_z IS NULL)
        OR (coordinate_x IS NOT NULL AND coordinate_y IS NOT NULL AND coordinate_z IS NOT NULL))
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE equipment (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    asset_tag VARCHAR2(255 CHAR) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    row_code VARCHAR2(128 CHAR) NOT NULL,
    column_code VARCHAR2(128 CHAR) NOT NULL,
    rack_code VARCHAR2(128 CHAR),
    u_position NUMBER(10),
    coordinate_x NUMBER(12, 3),
    coordinate_y NUMBER(12, 3),
    coordinate_z NUMBER(12, 3),
    version NUMBER(19) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, asset_tag),
    CHECK (u_position IS NULL OR u_position BETWEEN 1 AND 60),
    CHECK ((rack_code IS NULL AND u_position IS NULL) OR rack_code IS NOT NULL),
    CHECK ((coordinate_x IS NULL AND coordinate_y IS NULL AND coordinate_z IS NULL)
        OR (coordinate_x IS NOT NULL AND coordinate_y IS NOT NULL AND coordinate_z IS NOT NULL))
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE vrfs (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    name VARCHAR2(255 CHAR) NOT NULL,
    route_distinguisher VARCHAR2(255 CHAR),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, name)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE TABLE prefixes (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    cidr VARCHAR2(64 CHAR) NOT NULL,
    first_usable VARCHAR2(64 CHAR) NOT NULL,
    last_usable VARCHAR2(64 CHAR) NOT NULL,
    description VARCHAR2(1000 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, vrf_name, cidr)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE ip_reservations (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    vrf_name VARCHAR2(255 CHAR) NOT NULL,
    prefix_cidr VARCHAR2(64 CHAR) NOT NULL,
    address VARCHAR2(64 CHAR) NOT NULL,
    hostname VARCHAR2(255 CHAR) NOT NULL,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, vrf_name, idempotency_key),
    UNIQUE (tenant_id, vrf_name, address)
)
PARTITION BY HASH (tenant_id) PARTITIONS 64;

CREATE TABLE audit_events (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    actor VARCHAR2(255 CHAR) NOT NULL,
    action VARCHAR2(255 CHAR) NOT NULL,
    target_type VARCHAR2(128 CHAR) NOT NULL,
    target_id VARCHAR2(128 CHAR) NOT NULL,
    severity VARCHAR2(255 CHAR) NOT NULL,
    metadata CLOB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, created_at, id),
    CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    CONSTRAINT ck_audit_events_metadata_json CHECK (metadata IS JSON)
);

CREATE INDEX idx_sites_tenant_code ON sites (tenant_id, code);

CREATE INDEX idx_rooms_location ON rooms (tenant_id, site_code, building_code, code);

CREATE INDEX idx_racks_location ON racks (tenant_id, site_code, building_code, room_code, row_code, column_code);

CREATE INDEX idx_equipment_location ON equipment (tenant_id, site_code, building_code, room_code, row_code, column_code);

CREATE INDEX idx_equipment_asset_tag ON equipment (tenant_id, asset_tag);

CREATE INDEX idx_prefixes_lookup ON prefixes (tenant_id, vrf_name, cidr);

CREATE INDEX idx_ip_reservations_lookup ON ip_reservations (tenant_id, vrf_name, prefix_cidr, address);

CREATE INDEX idx_ip_reservations_idempotency ON ip_reservations (tenant_id, vrf_name, idempotency_key);

CREATE INDEX idx_audit_events_target ON audit_events (tenant_id, target_type, target_id, created_at DESC);

CREATE INDEX idx_audit_events_action ON audit_events (tenant_id, action, created_at DESC);
