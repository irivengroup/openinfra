BEGIN;

ALTER TABLE racks ADD COLUMN IF NOT EXISTS usable_faces text[] NOT NULL DEFAULT '{front}';
ALTER TABLE racks ADD COLUMN IF NOT EXISTS max_weight_kg numeric(10, 2);
ALTER TABLE racks ADD COLUMN IF NOT EXISTS power_capacity_watts bigint;
ALTER TABLE racks DROP CONSTRAINT IF EXISTS racks_usable_faces_valid;
ALTER TABLE racks ADD CONSTRAINT racks_usable_faces_valid CHECK (
    array_length(usable_faces, 1) >= 1
    AND usable_faces <@ ARRAY['front', 'rear']::text[]
);
ALTER TABLE racks DROP CONSTRAINT IF EXISTS racks_max_weight_positive;
ALTER TABLE racks ADD CONSTRAINT racks_max_weight_positive CHECK (
    max_weight_kg IS NULL OR (max_weight_kg >= 1 AND max_weight_kg <= 10000)
);
ALTER TABLE racks DROP CONSTRAINT IF EXISTS racks_power_capacity_positive;
ALTER TABLE racks ADD CONSTRAINT racks_power_capacity_positive CHECK (
    power_capacity_watts IS NULL OR (power_capacity_watts >= 1 AND power_capacity_watts <= 1000000)
);

ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rack_face text;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS u_height integer;
ALTER TABLE equipment DROP CONSTRAINT IF EXISTS equipment_rack_face_valid;
ALTER TABLE equipment ADD CONSTRAINT equipment_rack_face_valid CHECK (
    rack_face IS NULL OR rack_face IN ('front', 'rear')
);
ALTER TABLE equipment DROP CONSTRAINT IF EXISTS equipment_u_height_valid;
ALTER TABLE equipment ADD CONSTRAINT equipment_u_height_valid CHECK (
    u_height IS NULL OR (u_height BETWEEN 1 AND 60)
);
ALTER TABLE equipment DROP CONSTRAINT IF EXISTS equipment_rack_mount_consistency;
ALTER TABLE equipment ADD CONSTRAINT equipment_rack_mount_consistency CHECK (
    (rack_code IS NULL AND u_position IS NULL AND rack_face IS NULL AND u_height IS NULL)
    OR rack_code IS NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_racks_location_capacity
    ON racks (tenant_id, site_code, building_code, room_code, code, units);
CREATE INDEX IF NOT EXISTS idx_racks_usable_faces_gin
    ON racks USING gin (usable_faces);
CREATE INDEX IF NOT EXISTS idx_equipment_rack_occupancy
    ON equipment (tenant_id, site_code, building_code, room_code, rack_code, rack_face, u_position)
    WHERE rack_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_dcim_rack_capacity ON audit_events (tenant_id, action, created_at)
    WHERE action IN ('dcim.rack.defined', 'dcim.equipment.located');

COMMIT;
