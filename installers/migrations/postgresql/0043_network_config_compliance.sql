-- OpenInfra v0.29.91 - P15 / EPIC-1504 network golden configuration compliance
BEGIN;

CREATE TABLE IF NOT EXISTS network_config_baselines (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code text NOT NULL,
    device_object_key text NOT NULL,
    platform text NOT NULL,
    expected_config jsonb NOT NULL,
    ignored_paths jsonb NOT NULL DEFAULT '[]'::jsonb,
    critical_paths jsonb NOT NULL DEFAULT '[]'::jsonb,
    owner text NOT NULL,
    justification text NOT NULL,
    status text NOT NULL,
    version integer NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL,
    fingerprint char(64) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CONSTRAINT network_config_baseline_code_valid CHECK (code ~ '^[A-Z0-9][A-Z0-9_.:-]{0,63}$'),
    CONSTRAINT network_config_baseline_object_valid CHECK (length(device_object_key) BETWEEN 3 AND 128),
    CONSTRAINT network_config_baseline_platform_valid CHECK (platform ~ '^[a-z0-9][a-z0-9_.:-]{1,63}$'),
    CONSTRAINT network_config_baseline_document_object CHECK (jsonb_typeof(expected_config) = 'object'),
    CONSTRAINT network_config_baseline_ignored_array CHECK (jsonb_typeof(ignored_paths) = 'array'),
    CONSTRAINT network_config_baseline_critical_array CHECK (jsonb_typeof(critical_paths) = 'array'),
    CONSTRAINT network_config_baseline_owner_valid CHECK (length(trim(owner)) BETWEEN 2 AND 255),
    CONSTRAINT network_config_baseline_justification_valid CHECK (length(trim(justification)) BETWEEN 8 AND 1000),
    CONSTRAINT network_config_baseline_status_valid CHECK (status IN ('active','retired')),
    CONSTRAINT network_config_baseline_version_valid CHECK (version >= 1),
    CONSTRAINT network_config_baseline_fingerprint_valid CHECK (fingerprint ~ '^[a-f0-9]{64}$'),
    CONSTRAINT network_config_baseline_timestamps_ordered CHECK (updated_at >= created_at)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS network_config_baselines_p00 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS network_config_baselines_p01 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS network_config_baselines_p02 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS network_config_baselines_p03 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS network_config_baselines_p04 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS network_config_baselines_p05 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS network_config_baselines_p06 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS network_config_baselines_p07 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS network_config_baselines_p08 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS network_config_baselines_p09 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS network_config_baselines_p10 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS network_config_baselines_p11 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS network_config_baselines_p12 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS network_config_baselines_p13 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS network_config_baselines_p14 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS network_config_baselines_p15 PARTITION OF network_config_baselines FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_network_config_baselines_device
    ON network_config_baselines (tenant_id, device_object_key, platform, status, code);
CREATE INDEX IF NOT EXISTS idx_network_config_baselines_owner
    ON network_config_baselines (tenant_id, owner, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_config_baselines_document
    ON network_config_baselines USING gin (expected_config jsonb_path_ops);

CREATE TABLE IF NOT EXISTS network_config_observations (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    source text NOT NULL,
    collector text NOT NULL,
    device_object_key text NOT NULL,
    platform text NOT NULL,
    observed_config jsonb NOT NULL,
    observed_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL,
    fingerprint char(64) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT network_config_observation_idempotency_valid CHECK (idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$'),
    CONSTRAINT network_config_observation_source_valid CHECK (source IN ('ssh','api','netconf','restconf','gnmi','discovery','import','manual')),
    CONSTRAINT network_config_observation_collector_valid CHECK (length(trim(collector)) BETWEEN 2 AND 255),
    CONSTRAINT network_config_observation_object_valid CHECK (length(device_object_key) BETWEEN 3 AND 128),
    CONSTRAINT network_config_observation_platform_valid CHECK (platform ~ '^[a-z0-9][a-z0-9_.:-]{1,63}$'),
    CONSTRAINT network_config_observation_document_object CHECK (jsonb_typeof(observed_config) = 'object'),
    CONSTRAINT network_config_observation_fingerprint_valid CHECK (fingerprint ~ '^[a-f0-9]{64}$'),
    CONSTRAINT network_config_observation_timestamps_ordered CHECK (received_at >= observed_at - interval '365 days')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS network_config_observations_p00 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS network_config_observations_p01 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS network_config_observations_p02 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS network_config_observations_p03 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS network_config_observations_p04 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS network_config_observations_p05 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS network_config_observations_p06 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS network_config_observations_p07 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS network_config_observations_p08 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS network_config_observations_p09 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS network_config_observations_p10 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS network_config_observations_p11 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS network_config_observations_p12 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS network_config_observations_p13 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS network_config_observations_p14 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS network_config_observations_p15 PARTITION OF network_config_observations FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_network_config_observations_device
    ON network_config_observations (tenant_id, device_object_key, platform, observed_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_network_config_observations_source
    ON network_config_observations (tenant_id, source, collector, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_config_observations_observed_brin
    ON network_config_observations USING brin (observed_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_network_config_observations_document
    ON network_config_observations USING gin (observed_config jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_audit_events_network_config
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('network_config_baseline','network_config_observation','network_config_compliance');

COMMIT;
