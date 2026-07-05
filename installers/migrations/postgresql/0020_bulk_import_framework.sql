-- OpenInfra PostgreSQL migration 0020
-- P06 / EPIC-0602 - Bulk import checkpoints, bounded batches and scalable metrics.

CREATE TABLE IF NOT EXISTS bulk_import_jobs (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    import_format text NOT NULL,
    dry_run boolean NOT NULL,
    status text NOT NULL,
    total_rows bigint NOT NULL,
    valid_rows bigint NOT NULL,
    invalid_rows bigint NOT NULL,
    create_count bigint NOT NULL,
    update_count bigint NOT NULL,
    mapping jsonb NOT NULL,
    metrics jsonb NOT NULL,
    checkpoint jsonb NOT NULL,
    impact_sample jsonb NOT NULL,
    dlq_sample jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CHECK (import_format IN ('csv', 'json', 'xlsx')),
    CHECK (status IN ('queued', 'validated', 'applied', 'failed')),
    CHECK (total_rows >= 0),
    CHECK (valid_rows >= 0),
    CHECK (invalid_rows >= 0),
    CHECK (valid_rows + invalid_rows = total_rows),
    CHECK (create_count >= 0),
    CHECK (update_count >= 0),
    CHECK (create_count + update_count <= valid_rows),
    CHECK (jsonb_typeof(mapping) = 'object'),
    CHECK (jsonb_typeof(metrics) = 'object'),
    CHECK (jsonb_typeof(checkpoint) = 'object'),
    CHECK (jsonb_typeof(impact_sample) = 'array'),
    CHECK (jsonb_typeof(dlq_sample) = 'array')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS bulk_import_checkpoints (
    job_id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    next_row_number bigint NOT NULL,
    total_rows bigint NOT NULL,
    valid_rows bigint NOT NULL,
    invalid_rows bigint NOT NULL,
    create_count bigint NOT NULL,
    update_count bigint NOT NULL,
    batches_completed bigint NOT NULL,
    status text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, job_id),
    CHECK (next_row_number >= 1),
    CHECK (total_rows >= 0),
    CHECK (valid_rows >= 0),
    CHECK (invalid_rows >= 0),
    CHECK (valid_rows + invalid_rows = total_rows),
    CHECK (create_count >= 0),
    CHECK (update_count >= 0),
    CHECK (create_count + update_count <= valid_rows),
    CHECK (batches_completed >= 0),
    CHECK (status IN ('queued', 'validated', 'applied', 'failed'))
) PARTITION BY HASH (tenant_id);

DO $$
DECLARE
    partition_index integer;
BEGIN
    FOR partition_index IN 0..15 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS bulk_import_jobs_p%s PARTITION OF bulk_import_jobs FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
            partition_index,
            partition_index
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS bulk_import_checkpoints_p%s PARTITION OF bulk_import_checkpoints FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
            partition_index,
            partition_index
        );
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS idx_bulk_import_jobs_status_updated
    ON bulk_import_jobs (tenant_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_bulk_import_jobs_metrics_gin
    ON bulk_import_jobs USING gin (metrics jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_bulk_import_checkpoints_status_updated
    ON bulk_import_checkpoints (tenant_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_bulk_import_audit_events
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action LIKE 'import.bulk_dataset.%';
