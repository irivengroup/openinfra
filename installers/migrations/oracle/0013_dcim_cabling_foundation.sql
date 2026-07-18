-- Generated deterministically from installers/migrations/postgresql/0013_dcim_cabling_foundation.sql.
-- Source SHA-256: 5b4395a50ce5be9e106f0d594609bc295566adb5db9c51b41d1dc926bbcdecdf
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE dcim_patch_panels (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    rack_code VARCHAR2(128 CHAR) NOT NULL,
    code VARCHAR2(255 CHAR) NOT NULL,
    rack_face VARCHAR2(255 CHAR) NOT NULL,
    u_position NUMBER(10) NOT NULL,
    u_height NUMBER(10) NOT NULL,
    port_count NUMBER(10) NOT NULL,
    connector VARCHAR2(255 CHAR) NOT NULL,
    medium VARCHAR2(255 CHAR) NOT NULL,
    label VARCHAR2(255 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, room_code, rack_code, code),
    CHECK (rack_face IN ('front', 'rear')),
    CHECK (u_position BETWEEN 1 AND 60),
    CHECK (u_height BETWEEN 1 AND 10),
    CHECK (port_count BETWEEN 1 AND 288),
    CHECK (connector IN ('rj45', 'lc', 'sc', 'mpo', 'sfp', 'qsfp')),
    CHECK (medium IN ('copper', 'fiber', 'dac')),
    CHECK ((connector = 'rj45' AND medium = 'copper') OR (connector IN ('lc', 'sc', 'mpo') AND medium = 'fiber') OR (connector IN ('sfp', 'qsfp') AND medium IN ('fiber', 'dac')))
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE dcim_ports (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    owner_type VARCHAR2(128 CHAR) NOT NULL,
    owner_code VARCHAR2(128 CHAR) NOT NULL,
    port_name VARCHAR2(255 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    connector VARCHAR2(255 CHAR) NOT NULL,
    medium VARCHAR2(255 CHAR) NOT NULL,
    enabled NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, owner_type, owner_code, port_name),
    CHECK (owner_type IN ('equipment', 'patch_panel')),
    CHECK (connector IN ('rj45', 'lc', 'sc', 'mpo', 'sfp', 'qsfp')),
    CHECK (medium IN ('copper', 'fiber', 'dac')),
    CHECK ((connector = 'rj45' AND medium = 'copper') OR (connector IN ('lc', 'sc', 'mpo') AND medium = 'fiber') OR (connector IN ('sfp', 'qsfp') AND medium IN ('fiber', 'dac')))
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE dcim_cables (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    cable_id VARCHAR2(128 CHAR) NOT NULL,
    a_owner_type VARCHAR2(128 CHAR) NOT NULL,
    a_owner_code VARCHAR2(128 CHAR) NOT NULL,
    a_port_name VARCHAR2(255 CHAR) NOT NULL,
    b_owner_type VARCHAR2(128 CHAR) NOT NULL,
    b_owner_code VARCHAR2(128 CHAR) NOT NULL,
    b_port_name VARCHAR2(255 CHAR) NOT NULL,
    medium VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    path_segments CLOB NOT NULL,
    length_m NUMBER(12, 3),
    label VARCHAR2(255 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, cable_id),
    CHECK (a_owner_type IN ('equipment', 'patch_panel')),
    CHECK (b_owner_type IN ('equipment', 'patch_panel')),
    CHECK (medium IN ('copper', 'fiber', 'dac')),
    CHECK (status IN ('planned', 'installed', 'retired')),
    CHECK (JSON_EXISTS(path_segments, '$?(@.type() == \"array\")')),
    CHECK (length_m IS NULL OR (length_m > 0 AND length_m <= 100000)),
    CHECK (NOT (a_owner_type = b_owner_type AND a_owner_code = b_owner_code AND a_port_name = b_port_name)),
    CONSTRAINT ck_dcim_cables_path_segments_json CHECK (path_segments IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_dcim_patch_panels_rack_units
    ON dcim_patch_panels (tenant_id, site_code, building_code, room_code, rack_code, rack_face, u_position);

CREATE INDEX idx_dcim_ports_owner_lookup
    ON dcim_ports (tenant_id, owner_type, owner_code, port_name);

CREATE INDEX idx_dcim_ports_location
    ON dcim_ports (tenant_id, site_code, building_code, room_code, owner_type, owner_code);

CREATE INDEX idx_dcim_cables_side_a_active
    ON dcim_cables (tenant_id, a_owner_type, a_owner_code, a_port_name);

CREATE INDEX idx_dcim_cables_side_b_active
    ON dcim_cables (tenant_id, b_owner_type, b_owner_code, b_port_name);

CREATE INDEX idx_audit_events_dcim_cabling
    ON audit_events (tenant_id, action, created_at DESC);
