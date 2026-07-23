-- Generated deterministically from installers/migrations/postgresql/0046_finops_costs_showback.sql.
-- Source SHA-256: a041dfe0eb46ad3003b27391b9bc6677127de2116f73a27e5f4c2302036adb7e
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE finops_allocation_rules (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    priority NUMBER(10) NOT NULL,
    active NUMBER(1) NOT NULL,
    dimension VARCHAR2(255 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT finops_rule_priority_valid CHECK (priority BETWEEN 1 AND 10000),
    CONSTRAINT finops_rule_dimension_valid CHECK (
        dimension IN ('asset','application','business-service','tenant','owner','tag',
                      'cost-center','environment','dependency')
    ),
    CONSTRAINT finops_rule_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_allocation_rules_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE finops_import_jobs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT finops_import_key_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}$')
    ),
    CONSTRAINT finops_import_status_valid CHECK (
        status IN ('queued','running','completed','failed','cancelled')
    ),
    CONSTRAINT finops_import_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_import_jobs_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE finops_cost_records (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    currency CHAR(3 CHAR) NOT NULL,
    category VARCHAR2(255 CHAR) NOT NULL,
    source VARCHAR2(255 CHAR) NOT NULL,
    quality_status VARCHAR2(128 CHAR) NOT NULL,
    amount NUMBER(24,6) NOT NULL,
    payload CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, period_start, id),
    CONSTRAINT finops_cost_period_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_cost_currency_valid CHECK (REGEXP_LIKE(currency, '^[A-Z]{3}$')),
    CONSTRAINT finops_cost_category_valid CHECK (
        category IN ('cloud','saas','datacenter','energy','license','support','contract')
    ),
    CONSTRAINT finops_cost_quality_valid CHECK (
        quality_status IN ('allocated','partial','unallocated')
    ),
    CONSTRAINT finops_cost_amount_valid CHECK (amount > 0),
    CONSTRAINT finops_cost_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_cost_records_payload_json CHECK (payload IS JSON)
);

CREATE TABLE finops_budgets (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    dimension VARCHAR2(255 CHAR) NOT NULL,
    target VARCHAR2(255 CHAR) NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    currency CHAR(3 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, dimension, target, period_start, period_end, currency),
    CONSTRAINT finops_budget_period_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_budget_currency_valid CHECK (REGEXP_LIKE(currency, '^[A-Z]{3}$')),
    CONSTRAINT finops_budget_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_budgets_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE finops_financial_periods (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period_start date NOT NULL,
    period_end date NOT NULL,
    currency CHAR(3 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, period_start, period_end, currency),
    CONSTRAINT finops_period_dates_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_period_currency_valid CHECK (REGEXP_LIKE(currency, '^[A-Z]{3}$')),
    CONSTRAINT finops_period_status_valid CHECK (status IN ('open','closed')),
    CONSTRAINT finops_period_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_financial_periods_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE finops_cost_anomalies (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    severity VARCHAR2(255 CHAR) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT finops_anomaly_severity_valid CHECK (
        severity IN ('info','warning','error','critical')
    ),
    CONSTRAINT finops_anomaly_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_cost_anomalies_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE finops_forecasts (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    dimension VARCHAR2(255 CHAR) NOT NULL,
    target VARCHAR2(255 CHAR) NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT finops_forecast_period_valid CHECK (period_end >= period_start),
    CONSTRAINT finops_forecast_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_forecasts_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE finops_reports (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    kind VARCHAR2(255 CHAR) NOT NULL,
    currency CHAR(3 CHAR) NOT NULL,
    reproducibility_key CHAR(64 CHAR) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, reproducibility_key),
    CONSTRAINT finops_report_kind_valid CHECK (kind IN ('showback','chargeback')),
    CONSTRAINT finops_report_currency_valid CHECK (REGEXP_LIKE(currency, '^[A-Z]{3}$')),
    CONSTRAINT finops_report_key_valid CHECK (REGEXP_LIKE(reproducibility_key, '^[a-f0-9]{64}$')),
    CONSTRAINT finops_report_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_finops_reports_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE finops_event_outbox (
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
    CONSTRAINT finops_event_name_valid CHECK (REGEXP_LIKE(event_name, '^[a-z][a-z0-9_.-]{2,120}$')),
    CONSTRAINT finops_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT finops_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_finops_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_finops_rules_listing
    ON finops_allocation_rules (tenant_id, active, priority, id);

CREATE INDEX idx_finops_import_jobs_listing
    ON finops_import_jobs (tenant_id, status, submitted_at DESC, id DESC);

CREATE INDEX idx_finops_cost_records_listing
    ON finops_cost_records (tenant_id, period_start DESC, currency, category, source, id DESC);

CREATE INDEX idx_finops_cost_records_idempotency
    ON finops_cost_records (tenant_id, idempotency_key, period_start DESC);

CREATE INDEX idx_finops_cost_records_quality
    ON finops_cost_records (tenant_id, quality_status, period_start DESC);

CREATE INDEX idx_finops_budgets_listing
    ON finops_budgets (tenant_id, currency, period_start DESC, dimension, target);

CREATE INDEX idx_finops_periods_listing
    ON finops_financial_periods (tenant_id, status, period_start DESC, id DESC);

CREATE INDEX idx_finops_anomalies_listing
    ON finops_cost_anomalies (tenant_id, severity, detected_at DESC, id DESC);

CREATE INDEX idx_finops_forecasts_listing
    ON finops_forecasts (tenant_id, dimension, target, period_start DESC, id DESC);

CREATE INDEX idx_finops_reports_listing
    ON finops_reports (tenant_id, kind, currency, generated_at DESC, id DESC);

CREATE INDEX idx_finops_event_outbox_pending
    ON finops_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_finops
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
