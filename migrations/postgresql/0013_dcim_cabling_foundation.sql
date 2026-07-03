-- OpenInfra v0.16.0 - DCIM cabling foundation.
-- Adds partitioned persistence for patch panels, DCIM ports and cable traces while preserving
-- the existing rack, room and equipment localization model.

BEGIN;

CREATE TABLE IF NOT EXISTS dcim_patch_panels (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    site_code text NOT NULL,
    building_code text NOT NULL,
    room_code text NOT NULL,
    rack_code text NOT NULL,
    code text NOT NULL,
    rack_face text NOT NULL,
    u_position integer NOT NULL,
    u_height integer NOT NULL,
    port_count integer NOT NULL,
    connector text NOT NULL,
    medium text NOT NULL,
    label text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, room_code, rack_code, code),
    CHECK (rack_face IN ('front', 'rear')),
    CHECK (u_position BETWEEN 1 AND 60),
    CHECK (u_height BETWEEN 1 AND 10),
    CHECK (port_count BETWEEN 1 AND 288),
    CHECK (connector IN ('rj45', 'lc', 'sc', 'mpo', 'sfp', 'qsfp')),
    CHECK (medium IN ('copper', 'fiber', 'dac')),
    CHECK ((connector = 'rj45' AND medium = 'copper') OR (connector IN ('lc', 'sc', 'mpo') AND medium = 'fiber') OR (connector IN ('sfp', 'qsfp') AND medium IN ('fiber', 'dac')))
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p00 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p01 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p02 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p03 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p04 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p05 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p06 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p07 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p08 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p09 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p10 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p11 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p12 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p13 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p14 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_patch_panels_p15 PARTITION OF dcim_patch_panels FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE TABLE IF NOT EXISTS dcim_ports (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    owner_type text NOT NULL,
    owner_code text NOT NULL,
    port_name text NOT NULL,
    site_code text NOT NULL,
    building_code text NOT NULL,
    room_code text NOT NULL,
    connector text NOT NULL,
    medium text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, owner_type, owner_code, port_name),
    CHECK (owner_type IN ('equipment', 'patch_panel')),
    CHECK (connector IN ('rj45', 'lc', 'sc', 'mpo', 'sfp', 'qsfp')),
    CHECK (medium IN ('copper', 'fiber', 'dac')),
    CHECK ((connector = 'rj45' AND medium = 'copper') OR (connector IN ('lc', 'sc', 'mpo') AND medium = 'fiber') OR (connector IN ('sfp', 'qsfp') AND medium IN ('fiber', 'dac')))
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS dcim_ports_p00 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_ports_p01 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_ports_p02 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_ports_p03 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_ports_p04 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_ports_p05 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_ports_p06 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_ports_p07 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_ports_p08 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_ports_p09 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_ports_p10 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_ports_p11 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_ports_p12 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_ports_p13 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_ports_p14 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_ports_p15 PARTITION OF dcim_ports FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE TABLE IF NOT EXISTS dcim_cables (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    cable_id text NOT NULL,
    a_owner_type text NOT NULL,
    a_owner_code text NOT NULL,
    a_port_name text NOT NULL,
    b_owner_type text NOT NULL,
    b_owner_code text NOT NULL,
    b_port_name text NOT NULL,
    medium text NOT NULL,
    status text NOT NULL,
    path_segments jsonb NOT NULL,
    length_m numeric(12, 3),
    label text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, cable_id),
    CHECK (a_owner_type IN ('equipment', 'patch_panel')),
    CHECK (b_owner_type IN ('equipment', 'patch_panel')),
    CHECK (medium IN ('copper', 'fiber', 'dac')),
    CHECK (status IN ('planned', 'installed', 'retired')),
    CHECK (jsonb_typeof(path_segments) = 'array'),
    CHECK (length_m IS NULL OR (length_m > 0 AND length_m <= 100000)),
    CHECK (NOT (a_owner_type = b_owner_type AND a_owner_code = b_owner_code AND a_port_name = b_port_name))
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS dcim_cables_p00 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_cables_p01 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_cables_p02 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_cables_p03 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_cables_p04 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_cables_p05 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_cables_p06 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_cables_p07 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_cables_p08 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_cables_p09 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_cables_p10 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_cables_p11 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_cables_p12 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_cables_p13 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_cables_p14 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_cables_p15 PARTITION OF dcim_cables FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_dcim_patch_panels_rack_units
    ON dcim_patch_panels (tenant_id, site_code, building_code, room_code, rack_code, rack_face, u_position);
CREATE INDEX IF NOT EXISTS idx_dcim_ports_owner_lookup
    ON dcim_ports (tenant_id, owner_type, owner_code, port_name);
CREATE INDEX IF NOT EXISTS idx_dcim_ports_location
    ON dcim_ports (tenant_id, site_code, building_code, room_code, owner_type, owner_code);
CREATE INDEX IF NOT EXISTS idx_dcim_cables_side_a_active
    ON dcim_cables (tenant_id, a_owner_type, a_owner_code, a_port_name)
    WHERE status IN ('planned', 'installed');
CREATE INDEX IF NOT EXISTS idx_dcim_cables_side_b_active
    ON dcim_cables (tenant_id, b_owner_type, b_owner_code, b_port_name)
    WHERE status IN ('planned', 'installed');
CREATE INDEX IF NOT EXISTS idx_dcim_cables_trace_gin
    ON dcim_cables USING gin (path_segments);
CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_cabling
    ON audit_events (tenant_id, action, occurred_at DESC)
    WHERE action IN ('dcim.patch-panel.defined', 'dcim.port.defined', 'dcim.cable.connected', 'dcim.cable.traced');

COMMIT;
