-- Generated deterministically from installers/migrations/postgresql/0045_simulation_migration_planning.sql.
-- Source SHA-256: 0925adc7984e35b97add7f389a2d1c8417b8721e735718765e50f35457bb532f
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE simulation_scenarios (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR),
    environment VARCHAR2(255 CHAR),
    criticality VARCHAR2(255 CHAR),
    status VARCHAR2(255 CHAR) NOT NULL,
    owner_name VARCHAR2(255 CHAR) NOT NULL,
    version NUMBER(10) NOT NULL,
    payload CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT simulation_scenario_idempotency_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$')
    ),
    CONSTRAINT simulation_scenario_status_valid CHECK (
        status IN ('draft','queued','running','completed','failed','cancelled')
    ),
    CONSTRAINT simulation_scenario_owner_valid CHECK (length(trim(owner_name)) BETWEEN 2 AND 128),
    CONSTRAINT simulation_scenario_version_valid CHECK (version >= 1),
    CONSTRAINT simulation_scenario_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT simulation_scenario_timestamps_ordered CHECK (updated_at >= created_at),
    CONSTRAINT simulation_scenario_started_ordered CHECK (
        started_at IS NULL OR started_at >= created_at
    ),
    CONSTRAINT simulation_scenario_completed_ordered CHECK (
        completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at)
    ),
    CONSTRAINT ck_simulation_scenarios_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE simulation_impact_reports (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    scenario_id VARCHAR2(36 CHAR) NOT NULL,
    scenario_version NUMBER(10) NOT NULL,
    input_sha256 CHAR(64 CHAR) NOT NULL,
    risk_before NUMBER(10) NOT NULL,
    risk_after NUMBER(10) NOT NULL,
    readiness_score NUMBER(10) NOT NULL,
    impacted_count NUMBER(10) NOT NULL,
    truncated NUMBER(1) NOT NULL,
    payload CLOB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT simulation_report_version_valid CHECK (scenario_version >= 1),
    CONSTRAINT simulation_report_sha_valid CHECK (REGEXP_LIKE(input_sha256, '^[a-f0-9]{64}$')),
    CONSTRAINT simulation_report_risk_before_valid CHECK (risk_before BETWEEN 0 AND 100),
    CONSTRAINT simulation_report_risk_after_valid CHECK (risk_after BETWEEN 0 AND 100),
    CONSTRAINT simulation_report_readiness_valid CHECK (readiness_score BETWEEN 0 AND 100),
    CONSTRAINT simulation_report_impacted_valid CHECK (impacted_count >= 0),
    CONSTRAINT simulation_report_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_simulation_impact_reports_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE simulation_scenario_comparisons (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    left_report_id VARCHAR2(36 CHAR) NOT NULL,
    right_report_id VARCHAR2(36 CHAR) NOT NULL,
    preferred_report_id VARCHAR2(36 CHAR),
    payload CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT simulation_comparison_distinct CHECK (left_report_id <> right_report_id),
    CONSTRAINT simulation_comparison_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_simulation_scenario_comparisons_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE simulation_event_outbox (
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
    CONSTRAINT simulation_event_name_valid CHECK (REGEXP_LIKE(event_name, '^[a-z][a-z0-9_.-]{2,120}$')),
    CONSTRAINT simulation_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT simulation_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_simulation_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_simulation_scenario_listing
    ON simulation_scenarios (tenant_id, status, site_code, updated_at DESC, id DESC);

CREATE INDEX idx_simulation_scenario_owner
    ON simulation_scenarios (tenant_id, owner_name, updated_at DESC);

CREATE INDEX idx_simulation_report_scenario
    ON simulation_impact_reports (tenant_id, scenario_id, generated_at DESC, id DESC);

CREATE INDEX idx_simulation_report_risk
    ON simulation_impact_reports (tenant_id, risk_after DESC, readiness_score, generated_at DESC);

CREATE INDEX idx_simulation_comparison_reports
    ON simulation_scenario_comparisons (tenant_id, left_report_id, right_report_id, created_at DESC);

CREATE INDEX idx_simulation_event_outbox_pending
    ON simulation_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_simulation
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
