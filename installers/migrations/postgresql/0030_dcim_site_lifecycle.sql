BEGIN;

ALTER TABLE sites ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE buildings ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE floors ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE room_zones ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';

ALTER TABLE sites DROP CONSTRAINT IF EXISTS sites_status_valid;
ALTER TABLE sites DROP CONSTRAINT IF EXISTS ck_sites_status;
ALTER TABLE sites ADD CONSTRAINT ck_sites_status CHECK (status IN ('active', 'suspended', 'retired'));
ALTER TABLE buildings DROP CONSTRAINT IF EXISTS buildings_status_valid;
ALTER TABLE buildings DROP CONSTRAINT IF EXISTS ck_buildings_status;
ALTER TABLE buildings ADD CONSTRAINT ck_buildings_status CHECK (status IN ('active', 'suspended', 'retired'));
ALTER TABLE floors DROP CONSTRAINT IF EXISTS floors_status_valid;
ALTER TABLE floors DROP CONSTRAINT IF EXISTS ck_floors_status;
ALTER TABLE floors ADD CONSTRAINT ck_floors_status CHECK (status IN ('active', 'suspended', 'retired'));
ALTER TABLE rooms DROP CONSTRAINT IF EXISTS rooms_status_valid;
ALTER TABLE rooms DROP CONSTRAINT IF EXISTS ck_rooms_status;
ALTER TABLE rooms ADD CONSTRAINT ck_rooms_status CHECK (status IN ('active', 'suspended', 'retired'));
ALTER TABLE room_zones DROP CONSTRAINT IF EXISTS room_zones_status_valid;
ALTER TABLE room_zones DROP CONSTRAINT IF EXISTS ck_room_zones_status;
ALTER TABLE room_zones ADD CONSTRAINT ck_room_zones_status CHECK (status IN ('active', 'suspended', 'retired'));

CREATE INDEX IF NOT EXISTS idx_sites_active_catalog ON sites (tenant_id, code) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_buildings_active_catalog ON buildings (tenant_id, site_code, code) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_floors_active_catalog ON floors (tenant_id, site_code, building_code, code) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_rooms_active_catalog ON rooms (tenant_id, site_code, building_code, code) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_room_zones_active_catalog ON room_zones (tenant_id, site_code, building_code, room_code, code) WHERE status = 'active';


CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_site_lifecycle
    ON audit_events (tenant_id, target_type, created_at DESC)
    WHERE target_type IN ('site', 'building', 'floor', 'room', 'zone');

COMMIT;
