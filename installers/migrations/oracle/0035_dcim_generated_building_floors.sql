-- Generated deterministically from installers/migrations/postgresql/0035_dcim_generated_building_floors.sql.
-- Source SHA-256: 915c3c04dd7d085f9bbccee1178896ae36217eb5f587ff91dd1e25e863670bb3
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE buildings ADD (building_type VARCHAR2(128 CHAR) DEFAULT 'simple' NOT NULL);

ALTER TABLE buildings ADD (initial_level NUMBER(10));

ALTER TABLE buildings ADD (final_level NUMBER(10));

ALTER TABLE buildings DROP CONSTRAINT ck_buildings_type;

ALTER TABLE buildings ADD CONSTRAINT ck_buildings_type CHECK (building_type IN ('simple', 'floors'));

ALTER TABLE buildings DROP CONSTRAINT ck_buildings_floor_levels;

ALTER TABLE buildings ADD CONSTRAINT ck_buildings_floor_levels CHECK (
    (building_type = 'simple' AND initial_level IS NULL AND final_level IS NULL)
    OR (
        building_type = 'floors'
        AND initial_level BETWEEN -20 AND 0
        AND final_level BETWEEN 1 AND 150
        AND initial_level < final_level
    )
);

ALTER TABLE floors DROP CONSTRAINT floors_level_index_check;

ALTER TABLE floors DROP CONSTRAINT ck_floors_level_index;

ALTER TABLE floors ADD CONSTRAINT ck_floors_level_index CHECK (level_index BETWEEN -20 AND 150);

CREATE INDEX idx_buildings_type_active
    ON buildings (tenant_id, site_code, building_type, code);

CREATE INDEX idx_audit_events_dcim_generated_floors
    ON audit_events (tenant_id, target_type, created_at DESC);
