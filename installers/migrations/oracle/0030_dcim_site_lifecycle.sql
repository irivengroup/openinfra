-- Generated deterministically from installers/migrations/postgresql/0030_dcim_site_lifecycle.sql.
-- Source SHA-256: b06ecf1fc715faf22b77bf1e255c627e8730f6d2e202c450e2f1344d3ffb1d5b
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE sites ADD (status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL);

ALTER TABLE buildings ADD (status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL);

ALTER TABLE floors ADD (status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL);

ALTER TABLE rooms ADD (status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL);

ALTER TABLE room_zones ADD (status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL);

ALTER TABLE sites DROP CONSTRAINT sites_status_valid;

ALTER TABLE sites DROP CONSTRAINT ck_sites_status;

ALTER TABLE sites ADD CONSTRAINT ck_sites_status CHECK (status IN ('active', 'suspended', 'retired'));

ALTER TABLE buildings DROP CONSTRAINT buildings_status_valid;

ALTER TABLE buildings DROP CONSTRAINT ck_buildings_status;

ALTER TABLE buildings ADD CONSTRAINT ck_buildings_status CHECK (status IN ('active', 'suspended', 'retired'));

ALTER TABLE floors DROP CONSTRAINT floors_status_valid;

ALTER TABLE floors DROP CONSTRAINT ck_floors_status;

ALTER TABLE floors ADD CONSTRAINT ck_floors_status CHECK (status IN ('active', 'suspended', 'retired'));

ALTER TABLE rooms DROP CONSTRAINT rooms_status_valid;

ALTER TABLE rooms DROP CONSTRAINT ck_rooms_status;

ALTER TABLE rooms ADD CONSTRAINT ck_rooms_status CHECK (status IN ('active', 'suspended', 'retired'));

ALTER TABLE room_zones DROP CONSTRAINT room_zones_status_valid;

ALTER TABLE room_zones DROP CONSTRAINT ck_room_zones_status;

ALTER TABLE room_zones ADD CONSTRAINT ck_room_zones_status CHECK (status IN ('active', 'suspended', 'retired'));

CREATE INDEX idx_sites_active_catalog ON sites (tenant_id, code);

CREATE INDEX idx_buildings_active_catalog ON buildings (tenant_id, site_code, code);

CREATE INDEX idx_floors_active_catalog ON floors (tenant_id, site_code, building_code, code);

CREATE INDEX idx_rooms_active_catalog ON rooms (tenant_id, site_code, building_code, code);

CREATE INDEX idx_room_zones_active_catalog ON room_zones (tenant_id, site_code, building_code, room_code, code);

CREATE INDEX idx_audit_events_dcim_site_lifecycle
    ON audit_events (tenant_id, target_type, created_at DESC);
