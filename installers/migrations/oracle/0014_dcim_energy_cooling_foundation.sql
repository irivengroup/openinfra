-- Generated deterministically from installers/migrations/postgresql/0014_dcim_energy_cooling_foundation.sql.
-- Source SHA-256: f710d3e804290f2d9be9a467b8e2f4f1586efa10511de63cc8b1f38a6fe1f565
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE dcim_power_devices (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    code VARCHAR2(255 CHAR) NOT NULL,
    kind VARCHAR2(255 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    rack_code VARCHAR2(128 CHAR),
    side VARCHAR2(255 CHAR),
    capacity_watts NUMBER(10) NOT NULL,
    derating_percent NUMBER(10) NOT NULL,
    input_source VARCHAR2(255 CHAR) NOT NULL,
    output_voltage NUMBER(10) NOT NULL,
    label VARCHAR2(255 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CHECK (kind IN ('pdu', 'ups')),
    CHECK (side IS NULL OR side IN ('A', 'B')),
    CHECK (capacity_watts BETWEEN 1 AND 10000000),
    CHECK (derating_percent BETWEEN 1 AND 100),
    CHECK (output_voltage BETWEEN 48 AND 1000),
    CHECK (length(input_source) BETWEEN 1 AND 120),
    CHECK (length(label) <= 160)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE dcim_power_circuits (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    circuit_id VARCHAR2(128 CHAR) NOT NULL,
    source_device_code VARCHAR2(128 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    rack_code VARCHAR2(128 CHAR) NOT NULL,
    side VARCHAR2(255 CHAR) NOT NULL,
    capacity_watts NUMBER(10) NOT NULL,
    breaker_rating_amps NUMBER(10) NOT NULL,
    redundancy_group VARCHAR2(255 CHAR) NOT NULL,
    label VARCHAR2(255 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, circuit_id),
    CHECK (side IN ('A', 'B')),
    CHECK (capacity_watts BETWEEN 1 AND 1000000),
    CHECK (breaker_rating_amps BETWEEN 1 AND 10000),
    CHECK (length(redundancy_group) BETWEEN 1 AND 80),
    CHECK (length(label) <= 160)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE dcim_cooling_zones (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    zone_code VARCHAR2(128 CHAR) NOT NULL,
    role VARCHAR2(255 CHAR) NOT NULL,
    cooling_capacity_watts NUMBER(10) NOT NULL,
    supply_temperature_c NUMBER(5, 2) NOT NULL,
    return_temperature_c NUMBER(5, 2) NOT NULL,
    label VARCHAR2(255 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code, building_code, room_code, zone_code),
    CHECK (role IN ('cold_aisle', 'hot_aisle', 'neutral')),
    CHECK (cooling_capacity_watts BETWEEN 1 AND 10000000),
    CHECK (supply_temperature_c BETWEEN 5 AND 35),
    CHECK (return_temperature_c BETWEEN 10 AND 60),
    CHECK (return_temperature_c > supply_temperature_c),
    CHECK (length(label) <= 160)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE dcim_power_reservations (
    id VARCHAR2(36 CHAR) DEFAULT LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), '(.{8})(.{4})(.{4})(.{4})(.{12})', '\1-\2-\3-\4-\5')) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    asset_tag VARCHAR2(255 CHAR) NOT NULL,
    circuit_id VARCHAR2(128 CHAR) NOT NULL,
    side VARCHAR2(255 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    building_code VARCHAR2(128 CHAR) NOT NULL,
    room_code VARCHAR2(128 CHAR) NOT NULL,
    rack_code VARCHAR2(128 CHAR) NOT NULL,
    expected_watts NUMBER(10) NOT NULL,
    label VARCHAR2(255 CHAR) DEFAULT ' ' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, asset_tag, circuit_id),
    CHECK (side IN ('A', 'B')),
    CHECK (expected_watts BETWEEN 1 AND 1000000),
    CHECK (length(label) <= 160)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_dcim_power_devices_location
    ON dcim_power_devices (tenant_id, site_code, building_code, room_code, rack_code, side);

CREATE INDEX idx_dcim_power_circuits_source
    ON dcim_power_circuits (tenant_id, source_device_code, side);

CREATE INDEX idx_dcim_power_circuits_rack
    ON dcim_power_circuits (tenant_id, site_code, building_code, room_code, rack_code, side);

CREATE INDEX idx_dcim_cooling_zones_room
    ON dcim_cooling_zones (tenant_id, site_code, building_code, room_code, role, zone_code);

CREATE INDEX idx_dcim_power_reservations_circuit
    ON dcim_power_reservations (tenant_id, circuit_id, side);

CREATE INDEX idx_dcim_power_reservations_rack
    ON dcim_power_reservations (tenant_id, site_code, building_code, room_code, rack_code);

CREATE INDEX idx_audit_events_dcim_energy_cooling
    ON audit_events (tenant_id, action, created_at DESC);
