-- Generated deterministically from installers/migrations/postgresql/0047_greenops_energy_capacity.sql.
-- Source SHA-256: 77811a89bee3ce6fb9f9e42ab271214509d1e9fcfb951b9eb24b8364ecd2cae9
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE greenops_measurement_sources (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR2(255 CHAR) NOT NULL,
    active NUMBER(1) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CONSTRAINT greenops_source_code_valid CHECK (REGEXP_LIKE(code, '^[a-z0-9][a-z0-9_.:@/-]{0,63}$')),
    CONSTRAINT greenops_source_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_measurement_sources_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_policies (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code),
    CONSTRAINT greenops_policy_site_valid CHECK (REGEXP_LIKE(site_code, '^[a-z0-9][a-z0-9_.:@/-]{0,63}$')),
    CONSTRAINT greenops_policy_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_policies_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_carbon_factors (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR2(255 CHAR) NOT NULL,
    region VARCHAR2(255 CHAR) NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_factor_period_valid CHECK (period_end >= period_start),
    CONSTRAINT greenops_factor_code_valid CHECK (REGEXP_LIKE(code, '^[a-z0-9][a-z0-9_.:@/-]{0,63}$')),
    CONSTRAINT greenops_factor_region_valid CHECK (REGEXP_LIKE(region, '^[a-z0-9][a-z0-9_.:@/-]{0,63}$')),
    CONSTRAINT greenops_factor_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_carbon_factors_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_measurement_idempotency (
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    measurement_id VARCHAR2(36 CHAR) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    payload_digest CHAR(64 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, idempotency_key),
    CONSTRAINT greenops_measurement_registry_key_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}$')
    ),
    CONSTRAINT greenops_measurement_registry_digest_valid CHECK (
        REGEXP_LIKE(payload_digest, '^[a-f0-9]{64}$')
    )
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_energy_measurements (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    source_code VARCHAR2(128 CHAR) NOT NULL,
    kind VARCHAR2(255 CHAR) NOT NULL,
    scope VARCHAR2(255 CHAR) NOT NULL,
    scope_key VARCHAR2(128 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    energy_kwh NUMBER(24,6) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, period_start, id),
    CONSTRAINT greenops_measurement_period_valid CHECK (period_end > period_start),
    CONSTRAINT greenops_measurement_energy_valid CHECK (energy_kwh > 0),
    CONSTRAINT greenops_measurement_kind_valid CHECK (kind IN ('observed','estimated')),
    CONSTRAINT greenops_measurement_scope_valid CHECK (
        scope IN ('site','room','rack','pdu','asset','application')
    ),
    CONSTRAINT greenops_measurement_idempotency_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}$')
    ),
    CONSTRAINT greenops_measurement_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_energy_measurements_payload_json CHECK (payload IS JSON)
);

CREATE TABLE greenops_anomalies (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    severity VARCHAR2(255 CHAR) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_anomaly_severity_valid CHECK (
        severity IN ('info','warning','error','critical')
    ),
    CONSTRAINT greenops_anomaly_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_anomalies_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_forecasts (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    dimension VARCHAR2(255 CHAR) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_forecast_dimension_valid CHECK (
        dimension IN ('energy','cooling','space','weight')
    ),
    CONSTRAINT greenops_forecast_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_forecasts_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_consolidation_candidates (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    risk_level VARCHAR2(255 CHAR) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_candidate_risk_valid CHECK (
        risk_level IN ('info','warning','error','critical')
    ),
    CONSTRAINT greenops_candidate_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT greenops_candidate_human_approval CHECK (
        JSON_VALUE(payload, '$.requires_human_approval') = 'true'
    ),
    CONSTRAINT ck_greenops_consolidation_candidates_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_scores (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    scope VARCHAR2(255 CHAR) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_score_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_scores_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_reports (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    scope VARCHAR2(255 CHAR) NOT NULL,
    reproducibility_key CHAR(64 CHAR) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, reproducibility_key),
    CONSTRAINT greenops_report_key_valid CHECK (REGEXP_LIKE(reproducibility_key, '^[a-f0-9]{64}$')),
    CONSTRAINT greenops_report_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_greenops_reports_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE greenops_event_outbox (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id VARCHAR2(36 CHAR) NOT NULL,
    event_name VARCHAR2(255 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    attempt_count NUMBER(10) DEFAULT 0 NOT NULL,
    last_error VARCHAR2(255 CHAR),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_event_name_valid CHECK (REGEXP_LIKE(event_name, '^[a-z][a-z0-9_.-]{2,120}$')),
    CONSTRAINT greenops_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT greenops_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_greenops_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_greenops_measurements_idempotency_lookup
    ON greenops_energy_measurements (tenant_id, idempotency_key, period_start DESC);

CREATE INDEX idx_greenops_measurement_registry_lookup
    ON greenops_measurement_idempotency (tenant_id, measurement_id, period_start);

CREATE INDEX idx_greenops_measurements_listing
    ON greenops_energy_measurements (
        tenant_id, site_code, scope, scope_key, kind, period_start DESC, id DESC
    );

CREATE INDEX idx_greenops_sources_listing
    ON greenops_measurement_sources (tenant_id, active, code, id);

CREATE INDEX idx_greenops_policies_site
    ON greenops_policies (tenant_id, site_code, updated_at DESC);

CREATE INDEX idx_greenops_factors_listing
    ON greenops_carbon_factors (tenant_id, code, region, period_start DESC, period_end DESC);

CREATE INDEX idx_greenops_anomalies_listing
    ON greenops_anomalies (tenant_id, site_code, severity, detected_at DESC, id DESC);

CREATE INDEX idx_greenops_forecasts_listing
    ON greenops_forecasts (tenant_id, site_code, dimension, generated_at DESC, id DESC);

CREATE INDEX idx_greenops_candidates_listing
    ON greenops_consolidation_candidates (
        tenant_id, site_code, risk_level, generated_at DESC, id DESC
    );

CREATE INDEX idx_greenops_scores_listing
    ON greenops_scores (tenant_id, scope, generated_at DESC, id DESC);

CREATE INDEX idx_greenops_reports_listing
    ON greenops_reports (tenant_id, site_code, scope, generated_at DESC, id DESC);

CREATE INDEX idx_greenops_event_outbox_pending
    ON greenops_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_greenops
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
