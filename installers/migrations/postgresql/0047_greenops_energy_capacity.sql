-- OpenInfra v0.29.98 - P16 / EPIC-1604 GreenOps and energy capacity
BEGIN;

CREATE TABLE IF NOT EXISTS greenops_measurement_sources (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code text NOT NULL,
    active boolean NOT NULL,
    created_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CONSTRAINT greenops_source_code_valid CHECK (code ~ '^[a-z0-9][a-z0-9_.:@/-]{0,63}$'),
    CONSTRAINT greenops_source_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_policies (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code text NOT NULL,
    updated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, site_code),
    CONSTRAINT greenops_policy_site_valid CHECK (site_code ~ '^[a-z0-9][a-z0-9_.:@/-]{0,63}$'),
    CONSTRAINT greenops_policy_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_carbon_factors (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code text NOT NULL,
    region text NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    created_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_factor_period_valid CHECK (period_end >= period_start),
    CONSTRAINT greenops_factor_code_valid CHECK (code ~ '^[a-z0-9][a-z0-9_.:@/-]{0,63}$'),
    CONSTRAINT greenops_factor_region_valid CHECK (region ~ '^[a-z0-9][a-z0-9_.:@/-]{0,63}$'),
    CONSTRAINT greenops_factor_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_measurement_idempotency (
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    measurement_id uuid NOT NULL,
    period_start timestamptz NOT NULL,
    payload_digest char(64) NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, idempotency_key),
    CONSTRAINT greenops_measurement_registry_key_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}$'
    ),
    CONSTRAINT greenops_measurement_registry_digest_valid CHECK (
        payload_digest ~ '^[a-f0-9]{64}$'
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_energy_measurements (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    source_code text NOT NULL,
    kind text NOT NULL,
    scope text NOT NULL,
    scope_key text NOT NULL,
    site_code text NOT NULL,
    period_start timestamptz NOT NULL,
    period_end timestamptz NOT NULL,
    energy_kwh numeric(24,6) NOT NULL,
    recorded_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, period_start, id),
    CONSTRAINT greenops_measurement_period_valid CHECK (period_end > period_start),
    CONSTRAINT greenops_measurement_energy_valid CHECK (energy_kwh > 0),
    CONSTRAINT greenops_measurement_kind_valid CHECK (kind IN ('observed','estimated')),
    CONSTRAINT greenops_measurement_scope_valid CHECK (
        scope IN ('site','room','rack','pdu','asset','application')
    ),
    CONSTRAINT greenops_measurement_idempotency_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}$'
    ),
    CONSTRAINT greenops_measurement_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY RANGE (period_start);

CREATE TABLE IF NOT EXISTS greenops_energy_measurements_default
    PARTITION OF greenops_energy_measurements DEFAULT;

CREATE TABLE IF NOT EXISTS greenops_anomalies (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code text NOT NULL,
    severity text NOT NULL,
    detected_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_anomaly_severity_valid CHECK (
        severity IN ('info','warning','error','critical')
    ),
    CONSTRAINT greenops_anomaly_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_forecasts (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code text NOT NULL,
    dimension text NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_forecast_dimension_valid CHECK (
        dimension IN ('energy','cooling','space','weight')
    ),
    CONSTRAINT greenops_forecast_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_consolidation_candidates (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code text NOT NULL,
    risk_level text NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_candidate_risk_valid CHECK (
        risk_level IN ('info','warning','error','critical')
    ),
    CONSTRAINT greenops_candidate_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT greenops_candidate_human_approval CHECK (
        payload ->> 'requires_human_approval' = 'true'
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_scores (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    scope text NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT greenops_score_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_reports (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code text NOT NULL,
    scope text NOT NULL,
    reproducibility_key char(64) NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, reproducibility_key),
    CONSTRAINT greenops_report_key_valid CHECK (reproducibility_key ~ '^[a-f0-9]{64}$'),
    CONSTRAINT greenops_report_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS greenops_event_outbox (
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
    CONSTRAINT greenops_event_name_valid CHECK (event_name ~ '^[a-z][a-z0-9_.-]{2,120}$'),
    CONSTRAINT greenops_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT greenops_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

DO $partitioning$
DECLARE
    table_name text;
    partition_index integer;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'greenops_measurement_sources',
        'greenops_policies',
        'greenops_carbon_factors',
        'greenops_anomalies',
        'greenops_forecasts',
        'greenops_consolidation_candidates',
        'greenops_scores',
        'greenops_reports',
        'greenops_event_outbox'
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

CREATE INDEX IF NOT EXISTS idx_greenops_measurements_idempotency_lookup
    ON greenops_energy_measurements (tenant_id, idempotency_key, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_greenops_measurement_registry_lookup
    ON greenops_measurement_idempotency (tenant_id, measurement_id, period_start);
CREATE INDEX IF NOT EXISTS idx_greenops_measurements_listing
    ON greenops_energy_measurements (
        tenant_id, site_code, scope, scope_key, kind, period_start DESC, id DESC
    );
CREATE INDEX IF NOT EXISTS idx_greenops_measurements_period_brin
    ON greenops_energy_measurements USING brin (period_start) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_greenops_measurements_payload
    ON greenops_energy_measurements USING gin (payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_greenops_sources_listing
    ON greenops_measurement_sources (tenant_id, active, code, id);
CREATE INDEX IF NOT EXISTS idx_greenops_policies_site
    ON greenops_policies (tenant_id, site_code, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_greenops_factors_listing
    ON greenops_carbon_factors (tenant_id, code, region, period_start DESC, period_end DESC);
CREATE INDEX IF NOT EXISTS idx_greenops_anomalies_listing
    ON greenops_anomalies (tenant_id, site_code, severity, detected_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_greenops_forecasts_listing
    ON greenops_forecasts (tenant_id, site_code, dimension, generated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_greenops_candidates_listing
    ON greenops_consolidation_candidates (
        tenant_id, site_code, risk_level, generated_at DESC, id DESC
    );
CREATE INDEX IF NOT EXISTS idx_greenops_scores_listing
    ON greenops_scores (tenant_id, scope, generated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_greenops_reports_listing
    ON greenops_reports (tenant_id, site_code, scope, generated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_greenops_event_outbox_pending
    ON greenops_event_outbox (tenant_id, occurred_at, id) WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_greenops_event_outbox_occurred_brin
    ON greenops_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_audit_events_greenops
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN (
        'green_measurement_source','greenops_policy','green_carbon_factor',
        'green_energy_measurement','green_sustainability_report'
    );

COMMIT;
