-- Generated deterministically from installers/migrations/postgresql/0009_dcim_physical_model.sql.
-- Source SHA-256: ae8ab86f4f19b636acf3ee182385aee4d7c7d8ef425a636ea002e001a4deadf7
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE sites ADD (region VARCHAR2(255 CHAR) DEFAULT ' ' NOT NULL);

CREATE TABLE floors (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    code VARCHAR2(255 CHAR) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    level_index NUMBER(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, code),
    CHECK (level_index BETWEEN -20 AND 300)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

ALTER TABLE rooms ADD (floor_code VARCHAR2(128 CHAR));

ALTER TABLE rooms ADD (zone_codes CLOB DEFAULT '{}' NOT NULL);

ALTER TABLE rooms ADD (coordinate_x NUMBER(12, 3));

ALTER TABLE rooms ADD (coordinate_y NUMBER(12, 3));

ALTER TABLE rooms ADD (coordinate_z NUMBER(12, 3));

ALTER TABLE rooms DROP CONSTRAINT rooms_coordinates_all_or_nothing;

ALTER TABLE rooms ADD CONSTRAINT rooms_coordinates_all_or_nothing CHECK (
    (coordinate_x IS NULL AND coordinate_y IS NULL AND coordinate_z IS NULL)
    OR (coordinate_x IS NOT NULL AND coordinate_y IS NOT NULL AND coordinate_z IS NOT NULL)
);

CREATE TABLE room_zones (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    floor_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    code VARCHAR2(255 CHAR) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    "ROWS" CLOB NOT NULL,
    columns CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, room_code, code),
    CHECK (JSON_EXISTS("ROWS", '$[0]')),
    CHECK (JSON_EXISTS(columns, '$[0]')),
    CONSTRAINT ck_room_zones_rows_json CHECK ("ROWS" IS JSON),
    CONSTRAINT ck_room_zones_columns_json CHECK (columns IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

ALTER TABLE racks ADD (floor_code VARCHAR2(128 CHAR));

ALTER TABLE racks ADD (zone_code VARCHAR2(128 CHAR));

ALTER TABLE equipment ADD (floor_code VARCHAR2(128 CHAR));

ALTER TABLE equipment ADD (zone_code VARCHAR2(128 CHAR));

CREATE INDEX idx_sites_tenant_region_city ON sites (tenant_id, region, city);

CREATE INDEX idx_floors_location ON floors (tenant_id, site_code, building_code, code);

CREATE INDEX idx_rooms_physical_path ON rooms (tenant_id, site_code, building_code, floor_code, code);

CREATE INDEX idx_room_zones_grid ON room_zones (tenant_id, site_code, building_code, room_code, code);

CREATE INDEX idx_equipment_physical_lookup
    ON equipment (tenant_id, site_code, building_code, floor_code, room_code, row_code, column_code);

CREATE INDEX idx_audit_dcim_physical ON audit_events (tenant_id, action, created_at);
