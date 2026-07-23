-- Generated deterministically from installers/migrations/postgresql/0040_dcim_floor_nomenclature.sql.
-- Source SHA-256: de9b9b52d095cd081222ea4f369dbdb22344ab985746b36e13a50e35226a514e
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE GLOBAL TEMPORARY TABLE openinfra_floor_nomenclature_map ON COMMIT PRESERVE ROWS AS
SELECT
    tenant_id,
    site_code,
    building_code,
    code AS old_code,
    CASE
        WHEN level_index < 0 THEN
            'L-' || CASE
                WHEN abs(level_index) < 100 THEN lpad(abs(level_index), 2, '0')
                ELSE abs(level_index)
            END
        ELSE
            'L' || CASE
                WHEN level_index < 100 THEN lpad(level_index, 2, '0')
                ELSE level_index
            END
    END AS new_code,
    CASE
        WHEN name = site_code || '/' || building_code || '/ETG' || level_index
          OR name = CASE
              WHEN level_index < 0 THEN 'Sous-sol ' || abs(level_index)
              WHEN level_index = 0 THEN 'Rez-de-chaussée'
              ELSE 'Étage ' || level_index
          END
          OR name = CASE
              WHEN level_index < 0 THEN 'Basement ' || abs(level_index)
              WHEN level_index = 0 THEN 'Ground floor'
              ELSE 'Level ' || level_index
          END
        THEN CASE
            WHEN level_index < 0 THEN 'Basement ' || abs(level_index)
            WHEN level_index = 0 THEN 'Ground floor'
            ELSE 'Level ' || level_index
        END
        ELSE name
    END AS new_name,
    level_index
FROM floors;

DECLARE
    duplicate_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count FROM (
        SELECT tenant_id, site_code, building_code, new_code
        FROM openinfra_floor_nomenclature_map
        GROUP BY tenant_id, site_code, building_code, new_code
        HAVING COUNT(*) > 1
    );
    IF duplicate_count > 0 THEN
        RAISE_APPLICATION_ERROR(-20001, 'cannot migrate DCIM floor nomenclature: duplicate levels exist in a building');
    END IF;
END;
/

UPDATE rooms target
SET floor_code = (SELECT mapping.new_code FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code)
WHERE EXISTS (SELECT 1 FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code);

UPDATE room_zones target
SET floor_code = (SELECT mapping.new_code FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code)
WHERE EXISTS (SELECT 1 FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code);

UPDATE racks target
SET floor_code = (SELECT mapping.new_code FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code)
WHERE EXISTS (SELECT 1 FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code);

UPDATE equipment target
SET floor_code = (SELECT mapping.new_code FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code)
WHERE EXISTS (SELECT 1 FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.floor_code);

UPDATE floors target
SET code = (SELECT mapping.new_code FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.code), name = (SELECT mapping.new_name FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.code)
WHERE EXISTS (SELECT 1 FROM openinfra_floor_nomenclature_map mapping WHERE mapping.tenant_id = target.tenant_id AND mapping.site_code = target.site_code AND mapping.building_code = target.building_code AND mapping.old_code = target.code);

CREATE UNIQUE INDEX uq_floors_building_level
    ON floors (tenant_id, site_code, building_code, level_index);

ALTER TABLE floors DROP CONSTRAINT ck_floors_canonical_code;

ALTER TABLE floors ADD CONSTRAINT ck_floors_canonical_code CHECK (
    code = CASE
        WHEN level_index < 0 THEN
            'L-' || CASE
                WHEN abs(level_index) < 100 THEN lpad(abs(level_index), 2, '0')
                ELSE abs(level_index)
            END
        ELSE
            'L' || CASE
                WHEN level_index < 100 THEN lpad(level_index, 2, '0')
                ELSE level_index
            END
    END
);

CREATE INDEX idx_audit_events_dcim_floor_nomenclature
    ON audit_events (tenant_id, target_type, created_at DESC);

DROP TABLE openinfra_floor_nomenclature_map;
