-- Generated deterministically from installers/migrations/postgresql/0043_network_config_compliance.sql.
-- Source SHA-256: e817b8a59abf1dc6773b97d880953d0216672ea55aaaf182b75aa2a5aa9c3238
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE network_config_baselines (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR2(255 CHAR) NOT NULL,
    device_object_key VARCHAR2(128 CHAR) NOT NULL,
    platform VARCHAR2(255 CHAR) NOT NULL,
    expected_config CLOB NOT NULL,
    ignored_paths CLOB DEFAULT '[]' NOT NULL,
    critical_paths CLOB DEFAULT '[]' NOT NULL,
    owner VARCHAR2(255 CHAR) NOT NULL,
    justification VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    version NUMBER(10) NOT NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    fingerprint CHAR(64 CHAR) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CONSTRAINT network_config_baseline_code_valid CHECK (REGEXP_LIKE(code, '^[A-Z0-9][A-Z0-9_.:-]{0,63}$')),
    CONSTRAINT network_config_baseline_object_valid CHECK (length(device_object_key) BETWEEN 3 AND 128),
    CONSTRAINT network_config_baseline_platform_valid CHECK (REGEXP_LIKE(platform, '^[a-z0-9][a-z0-9_.:-]{1,63}$')),
    CONSTRAINT network_config_baseline_document_object CHECK (JSON_EXISTS(expected_config, '$?(@.type() == \"object\")')),
    CONSTRAINT network_config_baseline_ignored_array CHECK (JSON_EXISTS(ignored_paths, '$?(@.type() == \"array\")')),
    CONSTRAINT network_config_baseline_critical_array CHECK (JSON_EXISTS(critical_paths, '$?(@.type() == \"array\")')),
    CONSTRAINT network_config_baseline_owner_valid CHECK (length(trim(owner)) BETWEEN 2 AND 255),
    CONSTRAINT network_config_baseline_justification_valid CHECK (length(trim(justification)) BETWEEN 8 AND 1000),
    CONSTRAINT network_config_baseline_status_valid CHECK (status IN ('active','retired')),
    CONSTRAINT network_config_baseline_version_valid CHECK (version >= 1),
    CONSTRAINT network_config_baseline_fingerprint_valid CHECK (REGEXP_LIKE(fingerprint, '^[a-f0-9]{64}$')),
    CONSTRAINT network_config_baseline_timestamps_ordered CHECK (updated_at >= created_at),
    CONSTRAINT ck_network_config_baselines_expected_config_json CHECK (expected_config IS JSON),
    CONSTRAINT ck_network_config_baselines_ignored_paths_json CHECK (ignored_paths IS JSON),
    CONSTRAINT ck_network_config_baselines_critical_paths_json CHECK (critical_paths IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_network_config_baselines_device
    ON network_config_baselines (tenant_id, device_object_key, platform, status, code);

CREATE INDEX idx_network_config_baselines_owner
    ON network_config_baselines (tenant_id, owner, status, updated_at DESC);

CREATE TABLE network_config_observations (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    source VARCHAR2(255 CHAR) NOT NULL,
    collector VARCHAR2(255 CHAR) NOT NULL,
    device_object_key VARCHAR2(128 CHAR) NOT NULL,
    platform VARCHAR2(255 CHAR) NOT NULL,
    observed_config CLOB NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    fingerprint CHAR(64 CHAR) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT network_config_observation_idempotency_valid CHECK (REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$')),
    CONSTRAINT network_config_observation_source_valid CHECK (source IN ('ssh','api','netconf','restconf','gnmi','discovery','import','manual')),
    CONSTRAINT network_config_observation_collector_valid CHECK (length(trim(collector)) BETWEEN 2 AND 255),
    CONSTRAINT network_config_observation_object_valid CHECK (length(device_object_key) BETWEEN 3 AND 128),
    CONSTRAINT network_config_observation_platform_valid CHECK (REGEXP_LIKE(platform, '^[a-z0-9][a-z0-9_.:-]{1,63}$')),
    CONSTRAINT network_config_observation_document_object CHECK (JSON_EXISTS(observed_config, '$?(@.type() == \"object\")')),
    CONSTRAINT network_config_observation_fingerprint_valid CHECK (REGEXP_LIKE(fingerprint, '^[a-f0-9]{64}$')),
    CONSTRAINT network_config_observation_timestamps_ordered CHECK (received_at >= observed_at - INTERVAL '365' DAY),
    CONSTRAINT ck_network_config_observations_observed_config_json CHECK (observed_config IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_network_config_observations_device
    ON network_config_observations (tenant_id, device_object_key, platform, observed_at DESC, id DESC);

CREATE INDEX idx_network_config_observations_source
    ON network_config_observations (tenant_id, source, collector, observed_at DESC);

CREATE INDEX idx_audit_events_network_config
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
