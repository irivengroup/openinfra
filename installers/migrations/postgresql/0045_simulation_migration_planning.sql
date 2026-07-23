-- OpenInfra v0.29.96 - P16 / EPIC-1602 Simulation and migration planning
BEGIN;

CREATE TABLE IF NOT EXISTS simulation_scenarios (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    site_code text,
    environment text,
    criticality text,
    status text NOT NULL,
    owner_name text NOT NULL,
    version integer NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    started_at timestamptz,
    completed_at timestamptz,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT simulation_scenario_idempotency_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$'
    ),
    CONSTRAINT simulation_scenario_status_valid CHECK (
        status IN ('draft','queued','running','completed','failed','cancelled')
    ),
    CONSTRAINT simulation_scenario_owner_valid CHECK (length(trim(owner_name)) BETWEEN 2 AND 128),
    CONSTRAINT simulation_scenario_version_valid CHECK (version >= 1),
    CONSTRAINT simulation_scenario_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT simulation_scenario_timestamps_ordered CHECK (updated_at >= created_at),
    CONSTRAINT simulation_scenario_started_ordered CHECK (
        started_at IS NULL OR started_at >= created_at
    ),
    CONSTRAINT simulation_scenario_completed_ordered CHECK (
        completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at)
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS simulation_impact_reports (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    scenario_id uuid NOT NULL,
    scenario_version integer NOT NULL,
    input_sha256 char(64) NOT NULL,
    risk_before integer NOT NULL,
    risk_after integer NOT NULL,
    readiness_score integer NOT NULL,
    impacted_count integer NOT NULL,
    truncated boolean NOT NULL,
    payload jsonb NOT NULL,
    generated_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT simulation_report_version_valid CHECK (scenario_version >= 1),
    CONSTRAINT simulation_report_sha_valid CHECK (input_sha256 ~ '^[a-f0-9]{64}$'),
    CONSTRAINT simulation_report_risk_before_valid CHECK (risk_before BETWEEN 0 AND 100),
    CONSTRAINT simulation_report_risk_after_valid CHECK (risk_after BETWEEN 0 AND 100),
    CONSTRAINT simulation_report_readiness_valid CHECK (readiness_score BETWEEN 0 AND 100),
    CONSTRAINT simulation_report_impacted_valid CHECK (impacted_count >= 0),
    CONSTRAINT simulation_report_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS simulation_scenario_comparisons (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    left_report_id uuid NOT NULL,
    right_report_id uuid NOT NULL,
    preferred_report_id uuid,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT simulation_comparison_distinct CHECK (left_report_id <> right_report_id),
    CONSTRAINT simulation_comparison_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS simulation_event_outbox (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id uuid NOT NULL,
    event_name text NOT NULL,
    payload jsonb NOT NULL,
    occurred_at timestamptz NOT NULL,
    published_at timestamptz,
    attempt_count integer NOT NULL DEFAULT 0,
    last_error text,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT simulation_event_name_valid CHECK (event_name ~ '^[a-z][a-z0-9_.-]{2,120}$'),
    CONSTRAINT simulation_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT simulation_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

DO $partitioning$
DECLARE
    table_name text;
    partition_index integer;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'simulation_scenarios',
        'simulation_impact_reports',
        'simulation_scenario_comparisons',
        'simulation_event_outbox'
    ]
    LOOP
        FOR partition_index IN 0..15 LOOP
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
                table_name || '_p' || lpad(partition_index::text, 2, '0'),
                table_name,
                partition_index
            );
        END LOOP;
    END LOOP;
END
$partitioning$;

CREATE INDEX IF NOT EXISTS idx_simulation_scenario_listing
    ON simulation_scenarios (tenant_id, status, site_code, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_simulation_scenario_owner
    ON simulation_scenarios (tenant_id, owner_name, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_simulation_scenario_payload
    ON simulation_scenarios USING gin (payload jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_simulation_report_scenario
    ON simulation_impact_reports (tenant_id, scenario_id, generated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_simulation_report_risk
    ON simulation_impact_reports (tenant_id, risk_after DESC, readiness_score, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_simulation_report_generated_brin
    ON simulation_impact_reports USING brin (generated_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_simulation_report_payload
    ON simulation_impact_reports USING gin (payload jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_simulation_comparison_reports
    ON simulation_scenario_comparisons (tenant_id, left_report_id, right_report_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_simulation_event_outbox_pending
    ON simulation_event_outbox (tenant_id, occurred_at, id)
    WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_simulation_event_outbox_occurred_brin
    ON simulation_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);

CREATE INDEX IF NOT EXISTS idx_audit_events_simulation
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('simulation_scenario','simulation_report','simulation_comparison');

COMMIT;
