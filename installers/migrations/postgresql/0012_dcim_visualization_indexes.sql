-- OpenInfra v0.15.0 - DCIM visualization read-path indexes.
-- These indexes keep room 2D plans, rack elevations and visualization audit lookups deterministic
-- and scalable without changing existing transactional structures.

CREATE INDEX IF NOT EXISTS idx_racks_room_grid_visualization
    ON racks (tenant_id, site_code, building_code, room_code, row_code, column_code, code);

CREATE INDEX IF NOT EXISTS idx_equipment_room_grid_visualization
    ON equipment (tenant_id, site_code, building_code, room_code, row_code, column_code, rack_code, asset_tag);

CREATE INDEX IF NOT EXISTS idx_equipment_rack_elevation_visualization
    ON equipment (tenant_id, site_code, building_code, room_code, rack_code, rack_face, u_position, asset_tag)
    WHERE rack_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_visualization
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action IN ('dcim.room-plan.rendered', 'dcim.rack-elevation.rendered');
