-- Generated deterministically from installers/migrations/postgresql/0010_dcim_rack_capacity.sql.
-- Source SHA-256: 92a6f6b4a5d59ffa719f066718bbd7f9f4b73674e088c975651431e471ef937a
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE racks ADD (usable_faces CLOB DEFAULT '{front}' NOT NULL);

ALTER TABLE racks ADD (max_weight_kg NUMBER(10, 2));

ALTER TABLE racks ADD (power_capacity_watts NUMBER(19));

ALTER TABLE racks DROP CONSTRAINT racks_usable_faces_valid;

ALTER TABLE racks ADD CONSTRAINT racks_usable_faces_valid CHECK (
    JSON_EXISTS(usable_faces, '$[0]')
    AND usable_faces <@ '["front","rear"]'
);

ALTER TABLE racks DROP CONSTRAINT racks_max_weight_positive;

ALTER TABLE racks ADD CONSTRAINT racks_max_weight_positive CHECK (
    max_weight_kg IS NULL OR (max_weight_kg >= 1 AND max_weight_kg <= 10000)
);

ALTER TABLE racks DROP CONSTRAINT racks_power_capacity_positive;

ALTER TABLE racks ADD CONSTRAINT racks_power_capacity_positive CHECK (
    power_capacity_watts IS NULL OR (power_capacity_watts >= 1 AND power_capacity_watts <= 1000000)
);

ALTER TABLE equipment ADD (rack_face VARCHAR2(255 CHAR));

ALTER TABLE equipment ADD (u_height NUMBER(10));

ALTER TABLE equipment DROP CONSTRAINT equipment_rack_face_valid;

ALTER TABLE equipment ADD CONSTRAINT equipment_rack_face_valid CHECK (
    rack_face IS NULL OR rack_face IN ('front', 'rear')
);

ALTER TABLE equipment DROP CONSTRAINT equipment_u_height_valid;

ALTER TABLE equipment ADD CONSTRAINT equipment_u_height_valid CHECK (
    u_height IS NULL OR (u_height BETWEEN 1 AND 60)
);

ALTER TABLE equipment DROP CONSTRAINT equipment_rack_mount_consistency;

ALTER TABLE equipment ADD CONSTRAINT equipment_rack_mount_consistency CHECK (
    (rack_code IS NULL AND u_position IS NULL AND rack_face IS NULL AND u_height IS NULL)
    OR rack_code IS NOT NULL
);

CREATE INDEX idx_racks_location_capacity
    ON racks (tenant_id, site_code, building_code, room_code, code, units);

CREATE INDEX idx_equipment_rack_occupancy
    ON equipment (tenant_id, site_code, building_code, room_code, rack_code, rack_face, u_position);

CREATE INDEX idx_audit_dcim_rack_capacity ON audit_events (tenant_id, action, created_at);
