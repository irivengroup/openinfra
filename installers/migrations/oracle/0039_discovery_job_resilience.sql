-- Generated deterministically from installers/migrations/postgresql/0039_discovery_job_resilience.sql.
-- Source SHA-256: 471d810ba04d1ddd7778246a1b4b0f108d4ec7ed9c0dc80163b81f3e35ca49f4
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE discovery_jobs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    collector_id VARCHAR2(36 CHAR) NOT NULL,
    requested_scope VARCHAR2(255 CHAR) NOT NULL,
    job_type VARCHAR2(128 CHAR) NOT NULL,
    target VARCHAR2(255 CHAR) NOT NULL,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    max_attempts NUMBER(10) DEFAULT 3 NOT NULL,
    attempt_count NUMBER(10) DEFAULT 0 NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'queued' NOT NULL,
    lease_owner VARCHAR2(255 CHAR) NULL,
    lease_token NUMBER(19) DEFAULT 0 NOT NULL,
    leased_until TIMESTAMP WITH TIME ZONE NULL,
    next_attempt_at TIMESTAMP WITH TIME ZONE NULL,
    last_error VARCHAR2(255 CHAR) NULL,
    result_hash CHAR(64 CHAR) NULL,
    requested_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    FOREIGN KEY (tenant_id, collector_id)
        REFERENCES discovery_collectors (tenant_id, id),
    CONSTRAINT discovery_jobs_scope_valid CHECK (
        REGEXP_LIKE(requested_scope, '^[a-z0-9][a-z0-9_.:/-]{1,127}$')
    ),
    CONSTRAINT discovery_jobs_type_valid CHECK (
        REGEXP_LIKE(job_type, '^[a-z][a-z0-9.-]{1,63}$')
    ),
    CONSTRAINT discovery_jobs_target_not_blank CHECK (length(trim(target)) BETWEEN 1 AND 255),
    CONSTRAINT discovery_jobs_idempotency_key_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:/-]{7,127}$')
    ),
    CONSTRAINT discovery_jobs_attempts_valid CHECK (
        max_attempts BETWEEN 1 AND 20 AND attempt_count BETWEEN 0 AND max_attempts
    ),
    CONSTRAINT discovery_jobs_status_valid CHECK (
        status IN ('queued', 'leased', 'retry-wait', 'completed', 'dead-letter')
    ),
    CONSTRAINT discovery_jobs_lease_owner_valid CHECK (
        lease_owner IS NULL OR REGEXP_LIKE(lease_owner, '^[a-z0-9][a-z0-9_.:-]{2,127}$')
    ),
    CONSTRAINT discovery_jobs_lease_token_valid CHECK (lease_token >= 0),
    CONSTRAINT discovery_jobs_result_hash_valid CHECK (
        result_hash IS NULL OR REGEXP_LIKE(result_hash, '^[a-f0-9]{64}$')
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
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_discovery_jobs_claim
    ON discovery_jobs (
        tenant_id,
        collector_id,
        status,
        next_attempt_at,
        leased_until,
        created_at,
        id
    );

CREATE INDEX idx_discovery_jobs_dead_letter
    ON discovery_jobs (tenant_id, updated_at DESC, id);

CREATE INDEX idx_discovery_jobs_completed
    ON discovery_jobs (tenant_id, completed_at DESC, id);

CREATE INDEX idx_audit_events_discovery_jobs
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
