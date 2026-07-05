-- OpenInfra PostgreSQL migration 0019
-- P06 / EPIC-0601 - Generic import framework jobs, impact reports and DLQ evidence.

CREATE TABLE IF NOT EXISTS import_jobs (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    import_format text NOT NULL,
    dry_run boolean NOT NULL,
    status text NOT NULL,
    total_rows bigint NOT NULL,
    valid_rows bigint NOT NULL,
    invalid_rows bigint NOT NULL,
    mapping jsonb NOT NULL,
    impacts jsonb NOT NULL,
    dlq jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CHECK (import_format IN ('csv', 'json', 'xlsx')),
    CHECK (status IN ('queued', 'validated', 'applied', 'failed')),
    CHECK (total_rows >= 0),
    CHECK (valid_rows >= 0),
    CHECK (invalid_rows >= 0),
    CHECK (valid_rows + invalid_rows = total_rows),
    CHECK (jsonb_typeof(mapping) = 'object'),
    CHECK (jsonb_typeof(impacts) = 'array'),
    CHECK (jsonb_typeof(dlq) = 'array')
) PARTITION BY HASH (tenant_id);

DO $$
DECLARE
    partition_index integer;
BEGIN
    FOR partition_index IN 0..15 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS import_jobs_p%s PARTITION OF import_jobs FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
            partition_index,
            partition_index
        );
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS idx_import_jobs_status_updated
    ON import_jobs (tenant_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_import_jobs_format_created
    ON import_jobs (tenant_id, import_format, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_import_jobs_dlq_gin
    ON import_jobs USING gin (dlq jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_import_framework_audit_events
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action LIKE 'import.dataset.%';
