-- Generated deterministically from installers/migrations/postgresql/0012_dcim_visualization_indexes.sql.
-- Source SHA-256: 7603abc962105f9e6d3c67ac5a18652b8859510b77aebfd8d263b96e3695e4f9
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE INDEX idx_racks_room_grid_visualization
    ON racks (tenant_id, site_code, building_code, room_code, row_code, column_code, code);

CREATE INDEX idx_equipment_room_grid_visualization
    ON equipment (tenant_id, site_code, building_code, room_code, row_code, column_code, rack_code, asset_tag);

CREATE INDEX idx_equipment_rack_elevation_visualization
    ON equipment (tenant_id, site_code, building_code, room_code, rack_code, rack_face, u_position, asset_tag);

CREATE INDEX idx_audit_events_dcim_visualization
    ON audit_events (tenant_id, action, created_at DESC);
