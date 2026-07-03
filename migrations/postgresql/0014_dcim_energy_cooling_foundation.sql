-- OpenInfra v0.17.0 - DCIM energy and cooling foundation.
-- Adds native DCIM power-chain and cooling-capacity structures for racks without creating
-- any Docker dependency in production runtime.

BEGIN;

CREATE TABLE IF NOT EXISTS dcim_power_devices (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    code text NOT NULL,
    kind text NOT NULL,
    site_code text NOT NULL,
    building_code text NOT NULL,
    room_code text NOT NULL,
    rack_code text,
    side text,
    capacity_watts integer NOT NULL,
    derating_percent integer NOT NULL,
    input_source text NOT NULL,
    output_voltage integer NOT NULL,
    label text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CHECK (kind IN ('pdu', 'ups')),
    CHECK (side IS NULL OR side IN ('A', 'B')),
    CHECK (capacity_watts BETWEEN 1 AND 10000000),
    CHECK (derating_percent BETWEEN 1 AND 100),
    CHECK (output_voltage BETWEEN 48 AND 1000),
    CHECK (length(input_source) BETWEEN 1 AND 120),
    CHECK (length(label) <= 160)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS dcim_power_circuits (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    circuit_id text NOT NULL,
    source_device_code text NOT NULL,
    site_code text NOT NULL,
    building_code text NOT NULL,
    room_code text NOT NULL,
    rack_code text NOT NULL,
    side text NOT NULL,
    capacity_watts integer NOT NULL,
    breaker_rating_amps integer NOT NULL,
    redundancy_group text NOT NULL,
    label text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, circuit_id),
    CHECK (side IN ('A', 'B')),
    CHECK (capacity_watts BETWEEN 1 AND 1000000),
    CHECK (breaker_rating_amps BETWEEN 1 AND 10000),
    CHECK (length(redundancy_group) BETWEEN 1 AND 80),
    CHECK (length(label) <= 160)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS dcim_cooling_zones (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    site_code text NOT NULL,
    building_code text NOT NULL,
    room_code text NOT NULL,
    zone_code text NOT NULL,
    role text NOT NULL,
    cooling_capacity_watts integer NOT NULL,
    supply_temperature_c numeric(5, 2) NOT NULL,
    return_temperature_c numeric(5, 2) NOT NULL,
    label text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, room_code, zone_code),
    CHECK (role IN ('cold_aisle', 'hot_aisle', 'neutral')),
    CHECK (cooling_capacity_watts BETWEEN 1 AND 10000000),
    CHECK (supply_temperature_c BETWEEN 5 AND 35),
    CHECK (return_temperature_c BETWEEN 10 AND 60),
    CHECK (return_temperature_c > supply_temperature_c),
    CHECK (length(label) <= 160)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS dcim_power_reservations (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL REFERENCES tenants(id),
    asset_tag text NOT NULL,
    circuit_id text NOT NULL,
    side text NOT NULL,
    site_code text NOT NULL,
    building_code text NOT NULL,
    room_code text NOT NULL,
    rack_code text NOT NULL,
    expected_watts integer NOT NULL,
    label text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, asset_tag, circuit_id),
    CHECK (side IN ('A', 'B')),
    CHECK (expected_watts BETWEEN 1 AND 1000000),
    CHECK (length(label) <= 160)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p00 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p01 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p02 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p03 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p04 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p05 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p06 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p07 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p08 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p09 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p10 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p11 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p12 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p13 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p14 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_power_devices_p15 PARTITION OF dcim_power_devices FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE TABLE IF NOT EXISTS dcim_power_circuits_p00 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p01 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p02 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p03 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p04 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p05 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p06 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p07 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p08 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p09 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p10 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p11 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p12 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p13 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p14 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_power_circuits_p15 PARTITION OF dcim_power_circuits FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p00 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p01 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p02 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p03 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p04 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p05 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p06 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p07 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p08 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p09 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p10 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p11 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p12 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p13 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p14 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_cooling_zones_p15 PARTITION OF dcim_cooling_zones FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE TABLE IF NOT EXISTS dcim_power_reservations_p00 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p01 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p02 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p03 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p04 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p05 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p06 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p07 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p08 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p09 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p10 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p11 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p12 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p13 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p14 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_power_reservations_p15 PARTITION OF dcim_power_reservations FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_dcim_power_devices_location
    ON dcim_power_devices (tenant_id, site_code, building_code, room_code, rack_code, side);
CREATE INDEX IF NOT EXISTS idx_dcim_power_circuits_source
    ON dcim_power_circuits (tenant_id, source_device_code, side);
CREATE INDEX IF NOT EXISTS idx_dcim_power_circuits_rack
    ON dcim_power_circuits (tenant_id, site_code, building_code, room_code, rack_code, side);
CREATE INDEX IF NOT EXISTS idx_dcim_cooling_zones_room
    ON dcim_cooling_zones (tenant_id, site_code, building_code, room_code, role, zone_code);
CREATE INDEX IF NOT EXISTS idx_dcim_power_reservations_circuit
    ON dcim_power_reservations (tenant_id, circuit_id, side);
CREATE INDEX IF NOT EXISTS idx_dcim_power_reservations_rack
    ON dcim_power_reservations (tenant_id, site_code, building_code, room_code, rack_code);
CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_energy_cooling
    ON audit_events (tenant_id, action, occurred_at DESC)
    WHERE action IN (
        'dcim.power-device.defined',
        'dcim.power-circuit.defined',
        'dcim.cooling-zone.defined',
        'dcim.power-reservation.created',
        'dcim.energy-cooling-capacity.reported'
    );

COMMIT;
