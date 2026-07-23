BEGIN;

ALTER TABLE sites ADD COLUMN IF NOT EXISTS region text NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS floors (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    site_code text NOT NULL,
    building_code text NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    level_index integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, code),
    CHECK (level_index BETWEEN -20 AND 300)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS floors_p00 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS floors_p01 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS floors_p02 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS floors_p03 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS floors_p04 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS floors_p05 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS floors_p06 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS floors_p07 PARTITION OF floors FOR VALUES WITH (MODULUS 8, REMAINDER 7);

ALTER TABLE rooms ADD COLUMN IF NOT EXISTS floor_code text;
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS zone_codes text[] NOT NULL DEFAULT '{}';
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS coordinate_x numeric(12, 3);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS coordinate_y numeric(12, 3);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS coordinate_z numeric(12, 3);
ALTER TABLE rooms DROP CONSTRAINT IF EXISTS rooms_coordinates_all_or_nothing;
ALTER TABLE rooms ADD CONSTRAINT rooms_coordinates_all_or_nothing CHECK (
    (coordinate_x IS NULL AND coordinate_y IS NULL AND coordinate_z IS NULL)
    OR (coordinate_x IS NOT NULL AND coordinate_y IS NOT NULL AND coordinate_z IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS room_zones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    site_code text NOT NULL,
    building_code text NOT NULL,
    floor_code text NOT NULL,
    room_code text NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    rows text[] NOT NULL,
    columns text[] NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, room_code, code),
    CHECK (array_length(rows, 1) >= 1),
    CHECK (array_length(columns, 1) >= 1)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS room_zones_p00 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS room_zones_p01 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS room_zones_p02 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS room_zones_p03 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS room_zones_p04 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS room_zones_p05 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS room_zones_p06 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS room_zones_p07 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS room_zones_p08 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS room_zones_p09 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS room_zones_p10 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS room_zones_p11 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS room_zones_p12 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS room_zones_p13 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS room_zones_p14 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS room_zones_p15 PARTITION OF room_zones FOR VALUES WITH (MODULUS 16, REMAINDER 15);

ALTER TABLE racks ADD COLUMN IF NOT EXISTS floor_code text;
ALTER TABLE racks ADD COLUMN IF NOT EXISTS zone_code text;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS floor_code text;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS zone_code text;

CREATE INDEX IF NOT EXISTS idx_sites_tenant_region_city ON sites (tenant_id, region, city);
CREATE INDEX IF NOT EXISTS idx_floors_location ON floors (tenant_id, site_code, building_code, code);
CREATE INDEX IF NOT EXISTS idx_rooms_physical_path ON rooms (tenant_id, site_code, building_code, floor_code, code);
CREATE INDEX IF NOT EXISTS idx_rooms_zone_codes_gin ON rooms USING gin (zone_codes);
CREATE INDEX IF NOT EXISTS idx_room_zones_grid ON room_zones (tenant_id, site_code, building_code, room_code, code);
CREATE INDEX IF NOT EXISTS idx_equipment_physical_lookup
    ON equipment (tenant_id, site_code, building_code, floor_code, room_code, row_code, column_code);
CREATE INDEX IF NOT EXISTS idx_audit_dcim_physical ON audit_events (tenant_id, action, created_at)
    WHERE action LIKE 'dcim.%';

COMMIT;
