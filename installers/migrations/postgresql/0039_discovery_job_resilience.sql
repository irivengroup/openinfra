-- OpenInfra v0.29.83 - P14 / EPIC-1406 resilient discovery job lifecycle

BEGIN;

CREATE TABLE IF NOT EXISTS discovery_jobs (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    collector_id uuid NOT NULL,
    requested_scope text NOT NULL,
    job_type text NOT NULL,
    target text NOT NULL,
    idempotency_key text NOT NULL,
    max_attempts integer NOT NULL DEFAULT 3,
    attempt_count integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'queued',
    lease_owner text NULL,
    lease_token bigint NOT NULL DEFAULT 0,
    leased_until timestamptz NULL,
    next_attempt_at timestamptz NULL,
    last_error text NULL,
    result_hash char(64) NULL,
    requested_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    FOREIGN KEY (tenant_id, collector_id)
        REFERENCES discovery_collectors (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT discovery_jobs_scope_valid CHECK (
        requested_scope ~ '^[a-z0-9][a-z0-9_.:/-]{1,127}$'
    ),
    CONSTRAINT discovery_jobs_type_valid CHECK (
        job_type ~ '^[a-z][a-z0-9.-]{1,63}$'
    ),
    CONSTRAINT discovery_jobs_target_not_blank CHECK (length(trim(target)) BETWEEN 1 AND 255),
    CONSTRAINT discovery_jobs_idempotency_key_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:/-]{7,127}$'
    ),
    CONSTRAINT discovery_jobs_attempts_valid CHECK (
        max_attempts BETWEEN 1 AND 20 AND attempt_count BETWEEN 0 AND max_attempts
    ),
    CONSTRAINT discovery_jobs_status_valid CHECK (
        status IN ('queued', 'leased', 'retry-wait', 'completed', 'dead-letter')
    ),
    CONSTRAINT discovery_jobs_lease_owner_valid CHECK (
        lease_owner IS NULL OR lease_owner ~ '^[a-z0-9][a-z0-9_.:-]{2,127}$'
    ),
    CONSTRAINT discovery_jobs_lease_token_valid CHECK (lease_token >= 0),
    CONSTRAINT discovery_jobs_result_hash_valid CHECK (
        result_hash IS NULL OR result_hash ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT discovery_jobs_requested_by_not_blank CHECK (length(trim(requested_by)) >= 1),
    CONSTRAINT discovery_jobs_timestamps_ordered CHECK (updated_at >= created_at),
    CONSTRAINT discovery_jobs_state_consistent CHECK (
        (
            status = 'leased'
            AND lease_owner IS NOT NULL
            AND leased_until IS NOT NULL
            AND next_attempt_at IS NULL
            AND attempt_count >= 1
            AND completed_at IS NULL
            AND result_hash IS NULL
        )
        OR (
            status IN ('queued', 'retry-wait')
            AND lease_owner IS NULL
            AND leased_until IS NULL
            AND next_attempt_at IS NOT NULL
            AND completed_at IS NULL
            AND result_hash IS NULL
        )
        OR (
            status = 'completed'
            AND lease_owner IS NULL
            AND leased_until IS NULL
            AND next_attempt_at IS NULL
            AND completed_at IS NOT NULL
            AND result_hash IS NOT NULL
        )
        OR (
            status = 'dead-letter'
            AND lease_owner IS NULL
            AND leased_until IS NULL
            AND next_attempt_at IS NULL
            AND completed_at IS NULL
            AND result_hash IS NULL
            AND last_error IS NOT NULL
            AND attempt_count = max_attempts
        )
    ),
    CONSTRAINT discovery_jobs_retry_error_required CHECK (
        status <> 'retry-wait' OR last_error IS NOT NULL
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS discovery_jobs_p00 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS discovery_jobs_p01 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS discovery_jobs_p02 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS discovery_jobs_p03 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS discovery_jobs_p04 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS discovery_jobs_p05 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS discovery_jobs_p06 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS discovery_jobs_p07 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS discovery_jobs_p08 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS discovery_jobs_p09 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS discovery_jobs_p10 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS discovery_jobs_p11 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS discovery_jobs_p12 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS discovery_jobs_p13 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS discovery_jobs_p14 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS discovery_jobs_p15 PARTITION OF discovery_jobs
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_discovery_jobs_claim
    ON discovery_jobs (
        tenant_id,
        collector_id,
        status,
        next_attempt_at,
        leased_until,
        created_at,
        id
    )
    WHERE status IN ('queued', 'retry-wait', 'leased');

CREATE INDEX IF NOT EXISTS idx_discovery_jobs_dead_letter
    ON discovery_jobs (tenant_id, updated_at DESC, id)
    WHERE status = 'dead-letter';

CREATE INDEX IF NOT EXISTS idx_discovery_jobs_completed
    ON discovery_jobs (tenant_id, completed_at DESC, id)
    WHERE status = 'completed';

CREATE INDEX IF NOT EXISTS idx_audit_events_discovery_jobs
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'discovery_job';

COMMIT;
