CREATE TABLE IF NOT EXISTS migration_plan_reports (
    id text NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source text NOT NULL,
    import_format text NOT NULL,
    status text NOT NULL,
    template jsonb NOT NULL,
    total_rows bigint NOT NULL DEFAULT 0,
    valid_rows bigint NOT NULL DEFAULT 0,
    invalid_rows bigint NOT NULL DEFAULT 0,
    create_count bigint NOT NULL DEFAULT 0,
    update_count bigint NOT NULL DEFAULT 0,
    gaps jsonb NOT NULL,
    import_report jsonb NOT NULL,
    resume_strategy text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT migration_plan_reports_source_check CHECK (
        source IN ('device42', 'netbox', 'nautobot', 'glpi', 'csv')
    ),
    CONSTRAINT migration_plan_reports_format_check CHECK (import_format IN ('csv', 'json', 'xlsx')),
    CONSTRAINT migration_plan_reports_status_check CHECK (
        status IN ('queued', 'validated', 'applied', 'failed')
    ),
    CONSTRAINT migration_plan_reports_total_rows_check CHECK (total_rows >= 0),
    CONSTRAINT migration_plan_reports_valid_rows_check CHECK (valid_rows >= 0),
    CONSTRAINT migration_plan_reports_invalid_rows_check CHECK (invalid_rows >= 0),
    CONSTRAINT migration_plan_reports_create_count_check CHECK (create_count >= 0),
    CONSTRAINT migration_plan_reports_update_count_check CHECK (update_count >= 0),
    CONSTRAINT migration_plan_reports_row_count_check CHECK (valid_rows + invalid_rows = total_rows),
    CONSTRAINT migration_plan_reports_impact_count_check CHECK (create_count + update_count <= valid_rows)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS migration_plan_reports_p0 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS migration_plan_reports_p1 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS migration_plan_reports_p2 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS migration_plan_reports_p3 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS migration_plan_reports_p4 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS migration_plan_reports_p5 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS migration_plan_reports_p6 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS migration_plan_reports_p7 PARTITION OF migration_plan_reports FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_migration_plan_reports_source_status
    ON migration_plan_reports (tenant_id, source, status, created_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_audit_events_migration_plans
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'migration_plan';
