-- OpenInfra v0.29.97 - P16 / EPIC-1603 FinOps costs, showback and controlled chargeback
BEGIN;

CREATE TABLE IF NOT EXISTS finops_allocation_rules (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    priority integer NOT NULL,
    active boolean NOT NULL,
    dimension text NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT finops_rule_priority_valid CHECK (priority BETWEEN 1 AND 10000),
    CONSTRAINT finops_rule_dimension_valid CHECK (
        dimension IN ('asset','application','business-service','tenant','owner','tag',
                      'cost-center','environment','dependency')
    ),
    CONSTRAINT finops_rule_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS finops_import_jobs (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    status text NOT NULL,
    submitted_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT finops_import_key_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}$'
    ),
    CONSTRAINT finops_import_status_valid CHECK (
        status IN ('queued','running','completed','failed','cancelled')
    ),
    CONSTRAINT finops_import_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS finops_cost_records (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    currency char(3) NOT NULL,
    category text NOT NULL,
    source text NOT NULL,
    quality_status text NOT NULL,
    amount numeric(24,6) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, period_start, id),
    CONSTRAINT finops_cost_period_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_cost_currency_valid CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT finops_cost_category_valid CHECK (
        category IN ('cloud','saas','datacenter','energy','license','support','contract')
    ),
    CONSTRAINT finops_cost_quality_valid CHECK (
        quality_status IN ('allocated','partial','unallocated')
    ),
    CONSTRAINT finops_cost_amount_valid CHECK (amount > 0),
    CONSTRAINT finops_cost_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY RANGE (period_start);

CREATE TABLE IF NOT EXISTS finops_cost_records_default
    PARTITION OF finops_cost_records DEFAULT;

CREATE TABLE IF NOT EXISTS finops_budgets (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    dimension text NOT NULL,
    target text NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    currency char(3) NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, dimension, target, period_start, period_end, currency),
    CONSTRAINT finops_budget_period_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_budget_currency_valid CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT finops_budget_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS finops_financial_periods (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period_start date NOT NULL,
    period_end date NOT NULL,
    currency char(3) NOT NULL,
    status text NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, period_start, period_end, currency),
    CONSTRAINT finops_period_dates_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_period_currency_valid CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT finops_period_status_valid CHECK (status IN ('open','closed')),
    CONSTRAINT finops_period_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS finops_cost_anomalies (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    severity text NOT NULL,
    detected_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT finops_anomaly_severity_valid CHECK (
        severity IN ('info','warning','error','critical')
    ),
    CONSTRAINT finops_anomaly_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS finops_forecasts (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    dimension text NOT NULL,
    target text NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT finops_forecast_period_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_forecast_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS finops_reports (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    kind text NOT NULL,
    currency char(3) NOT NULL,
    reproducibility_key char(64) NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, reproducibility_key),
    CONSTRAINT finops_report_kind_valid CHECK (kind IN ('showback','chargeback')),
    CONSTRAINT finops_report_currency_valid CHECK (currency ~ '^[A-Z]{3}$'),
    CONSTRAINT finops_report_key_valid CHECK (reproducibility_key ~ '^[a-f0-9]{64}$'),
    CONSTRAINT finops_report_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS finops_event_outbox (
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
    CONSTRAINT finops_event_name_valid CHECK (event_name ~ '^[a-z][a-z0-9_.-]{2,120}$'),
    CONSTRAINT finops_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT finops_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

DO $partitioning$
DECLARE
    table_name text;
    partition_index integer;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'finops_allocation_rules',
        'finops_import_jobs',
        'finops_budgets',
        'finops_financial_periods',
        'finops_cost_anomalies',
        'finops_forecasts',
        'finops_reports',
        'finops_event_outbox'
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

CREATE INDEX IF NOT EXISTS idx_finops_rules_listing
    ON finops_allocation_rules (tenant_id, active, priority, id);
CREATE INDEX IF NOT EXISTS idx_finops_import_jobs_listing
    ON finops_import_jobs (tenant_id, status, submitted_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_finops_cost_records_listing
    ON finops_cost_records (tenant_id, period_start DESC, currency, category, source, id DESC);
CREATE INDEX IF NOT EXISTS idx_finops_cost_records_idempotency
    ON finops_cost_records (tenant_id, idempotency_key, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_finops_cost_records_quality
    ON finops_cost_records (tenant_id, quality_status, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_finops_cost_records_period_brin
    ON finops_cost_records USING brin (period_start) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_finops_cost_records_payload
    ON finops_cost_records USING gin (payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_finops_budgets_listing
    ON finops_budgets (tenant_id, currency, period_start DESC, dimension, target);
CREATE INDEX IF NOT EXISTS idx_finops_periods_listing
    ON finops_financial_periods (tenant_id, status, period_start DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_finops_anomalies_listing
    ON finops_cost_anomalies (tenant_id, severity, detected_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_finops_forecasts_listing
    ON finops_forecasts (tenant_id, dimension, target, period_start DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_finops_reports_listing
    ON finops_reports (tenant_id, kind, currency, generated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_finops_event_outbox_pending
    ON finops_event_outbox (tenant_id, occurred_at, id) WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_finops_event_outbox_occurred_brin
    ON finops_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_audit_events_finops
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN (
        'finops_allocation_rule','finops_import_job','finops_budget',
        'finops_financial_period','finops_report'
    );

COMMIT;
