-- Generated deterministically from installers/migrations/postgresql/0033_dcim_site_dependencies_rack_lifecycle.sql.
-- Source SHA-256: 1cd9e3eb031aa21b53a1a96fdf48f45bf9e064f14c174112c13cdec2e01087ef
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE racks ADD (status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL);

ALTER TABLE racks DROP CONSTRAINT racks_status_valid;

ALTER TABLE racks DROP CONSTRAINT ck_racks_status;

ALTER TABLE racks ADD CONSTRAINT ck_racks_status CHECK (status IN ('active', 'suspended', 'retired'));

CREATE INDEX idx_racks_active_catalog
    ON racks (tenant_id, site_code, building_code, room_code, code);

CREATE INDEX idx_racks_room_grid_active
    ON racks (tenant_id, site_code, building_code, room_code, row_code, column_code);

CREATE INDEX idx_audit_events_dcim_rack_lifecycle
    ON audit_events (tenant_id, target_type, created_at DESC);
