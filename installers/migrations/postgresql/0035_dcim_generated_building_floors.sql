BEGIN;

ALTER TABLE buildings ADD COLUMN IF NOT EXISTS building_type text NOT NULL DEFAULT 'simple';
ALTER TABLE buildings ADD COLUMN IF NOT EXISTS initial_level integer;
ALTER TABLE buildings ADD COLUMN IF NOT EXISTS final_level integer;

ALTER TABLE buildings DROP CONSTRAINT IF EXISTS ck_buildings_type;
ALTER TABLE buildings ADD CONSTRAINT ck_buildings_type CHECK (building_type IN ('simple', 'floors'));

ALTER TABLE buildings DROP CONSTRAINT IF EXISTS ck_buildings_floor_levels;
ALTER TABLE buildings ADD CONSTRAINT ck_buildings_floor_levels CHECK (
    (building_type = 'simple' AND initial_level IS NULL AND final_level IS NULL)
    OR (
        building_type = 'floors'
        AND initial_level BETWEEN -20 AND 0
        AND final_level BETWEEN 1 AND 150
        AND initial_level < final_level
    )
);

ALTER TABLE floors DROP CONSTRAINT IF EXISTS floors_level_index_check;
ALTER TABLE floors DROP CONSTRAINT IF EXISTS ck_floors_level_index;
ALTER TABLE floors ADD CONSTRAINT ck_floors_level_index CHECK (level_index BETWEEN -20 AND 150);

CREATE INDEX IF NOT EXISTS idx_buildings_type_active
    ON buildings (tenant_id, site_code, building_type, code)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_generated_floors
    ON audit_events (tenant_id, target_type, created_at DESC)
    WHERE target_type IN ('building', 'floor');

COMMIT;
