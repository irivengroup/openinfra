BEGIN;

ALTER TABLE racks ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE racks DROP CONSTRAINT IF EXISTS racks_status_valid;
ALTER TABLE racks DROP CONSTRAINT IF EXISTS ck_racks_status;
ALTER TABLE racks ADD CONSTRAINT ck_racks_status CHECK (status IN ('active', 'suspended', 'retired'));

CREATE INDEX IF NOT EXISTS idx_racks_active_catalog
    ON racks (tenant_id, site_code, building_code, room_code, code)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_racks_room_grid_active
    ON racks (tenant_id, site_code, building_code, room_code, row_code, column_code)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_rack_lifecycle
    ON audit_events (tenant_id, target_type, created_at DESC)
    WHERE target_type = 'rack';

COMMIT;
