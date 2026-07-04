CREATE TABLE IF NOT EXISTS export_jobs (
    id text NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    resource text NOT NULL,
    export_format text NOT NULL,
    status text NOT NULL,
    filter jsonb NOT NULL,
    requested_by text NOT NULL,
    total_rows bigint NOT NULL DEFAULT 0,
    artifact jsonb,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT export_jobs_resource_check CHECK (resource IN ('source_objects')),
    CONSTRAINT export_jobs_format_check CHECK (export_format IN ('csv', 'json', 'xlsx')),
    CONSTRAINT export_jobs_status_check CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    CONSTRAINT export_jobs_total_rows_check CHECK (total_rows >= 0)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS export_jobs_p0 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS export_jobs_p1 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS export_jobs_p2 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS export_jobs_p3 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS export_jobs_p4 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS export_jobs_p5 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS export_jobs_p6 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS export_jobs_p7 PARTITION OF export_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_export_jobs_queue
    ON export_jobs (tenant_id, status, created_at, id);

CREATE TABLE IF NOT EXISTS export_artifacts (
    job_id text NOT NULL,
    tenant_id text NOT NULL,
    content bytea NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, job_id),
    FOREIGN KEY (tenant_id, job_id) REFERENCES export_jobs(tenant_id, id) ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS export_artifacts_p0 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS export_artifacts_p1 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS export_artifacts_p2 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS export_artifacts_p3 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS export_artifacts_p4 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS export_artifacts_p5 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS export_artifacts_p6 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS export_artifacts_p7 PARTITION OF export_artifacts FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE TABLE IF NOT EXISTS export_signing_keys (
    id text PRIMARY KEY,
    secret_hex text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT export_signing_keys_secret_hex_check CHECK (secret_hex ~ '^[a-f0-9]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_audit_events_exports
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'export_job';
