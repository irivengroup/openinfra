BEGIN;

CREATE TEMP TABLE openinfra_floor_nomenclature_map ON COMMIT DROP AS
SELECT
    tenant_id,
    site_code,
    building_code,
    code AS old_code,
    CASE
        WHEN level_index < 0 THEN
            'L-' || CASE
                WHEN abs(level_index) < 100 THEN lpad(abs(level_index)::text, 2, '0')
                ELSE abs(level_index)::text
            END
        ELSE
            'L' || CASE
                WHEN level_index < 100 THEN lpad(level_index::text, 2, '0')
                ELSE level_index::text
            END
    END AS new_code,
    CASE
        WHEN name = site_code || '/' || building_code || '/ETG' || level_index::text
          OR name = CASE
              WHEN level_index < 0 THEN 'Sous-sol ' || abs(level_index)::text
              WHEN level_index = 0 THEN 'Rez-de-chaussée'
              ELSE 'Étage ' || level_index::text
          END
          OR name = CASE
              WHEN level_index < 0 THEN 'Basement ' || abs(level_index)::text
              WHEN level_index = 0 THEN 'Ground floor'
              ELSE 'Level ' || level_index::text
          END
        THEN CASE
            WHEN level_index < 0 THEN 'Basement ' || abs(level_index)::text
            WHEN level_index = 0 THEN 'Ground floor'
            ELSE 'Level ' || level_index::text
        END
        ELSE name
    END AS new_name,
    level_index
FROM floors;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM openinfra_floor_nomenclature_map
        GROUP BY tenant_id, site_code, building_code, new_code
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION
            'cannot migrate DCIM floor nomenclature: duplicate levels exist in a building';
    END IF;
END;
$$;

UPDATE rooms AS target
SET floor_code = mapping.new_code
FROM openinfra_floor_nomenclature_map AS mapping
WHERE target.tenant_id = mapping.tenant_id
  AND target.site_code = mapping.site_code
  AND target.building_code = mapping.building_code
  AND target.floor_code = mapping.old_code
  AND target.floor_code IS DISTINCT FROM mapping.new_code;

UPDATE room_zones AS target
SET floor_code = mapping.new_code
FROM openinfra_floor_nomenclature_map AS mapping
WHERE target.tenant_id = mapping.tenant_id
  AND target.site_code = mapping.site_code
  AND target.building_code = mapping.building_code
  AND target.floor_code = mapping.old_code
  AND target.floor_code IS DISTINCT FROM mapping.new_code;

UPDATE racks AS target
SET floor_code = mapping.new_code
FROM openinfra_floor_nomenclature_map AS mapping
WHERE target.tenant_id = mapping.tenant_id
  AND target.site_code = mapping.site_code
  AND target.building_code = mapping.building_code
  AND target.floor_code = mapping.old_code
  AND target.floor_code IS DISTINCT FROM mapping.new_code;

UPDATE equipment AS target
SET floor_code = mapping.new_code
FROM openinfra_floor_nomenclature_map AS mapping
WHERE target.tenant_id = mapping.tenant_id
  AND target.site_code = mapping.site_code
  AND target.building_code = mapping.building_code
  AND target.floor_code = mapping.old_code
  AND target.floor_code IS DISTINCT FROM mapping.new_code;

UPDATE floors AS target
SET code = mapping.new_code,
    name = mapping.new_name
FROM openinfra_floor_nomenclature_map AS mapping
WHERE target.tenant_id = mapping.tenant_id
  AND target.site_code = mapping.site_code
  AND target.building_code = mapping.building_code
  AND target.code = mapping.old_code
  AND (target.code IS DISTINCT FROM mapping.new_code OR target.name IS DISTINCT FROM mapping.new_name);

CREATE UNIQUE INDEX IF NOT EXISTS uq_floors_building_level
    ON floors (tenant_id, site_code, building_code, level_index);

ALTER TABLE floors DROP CONSTRAINT IF EXISTS ck_floors_canonical_code;
ALTER TABLE floors ADD CONSTRAINT ck_floors_canonical_code CHECK (
    code = CASE
        WHEN level_index < 0 THEN
            'L-' || CASE
                WHEN abs(level_index) < 100 THEN lpad(abs(level_index)::text, 2, '0')
                ELSE abs(level_index)::text
            END
        ELSE
            'L' || CASE
                WHEN level_index < 100 THEN lpad(level_index::text, 2, '0')
                ELSE level_index::text
            END
    END
);

CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_floor_nomenclature
    ON audit_events (tenant_id, target_type, created_at DESC)
    WHERE target_type = 'floor';

COMMIT;
