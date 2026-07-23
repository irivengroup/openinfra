BEGIN;

CREATE TABLE IF NOT EXISTS async_jobs (
    id UUID NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    specialization VARCHAR(64) NOT NULL,
    operation VARCHAR(128) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    payload_object_key VARCHAR(512) NOT NULL,
    payload_sha256 CHAR(64) NOT NULL,
    payload_size_bytes BIGINT NOT NULL,
    payload_media_type VARCHAR(255) NOT NULL,
    payload_created_at TIMESTAMPTZ NOT NULL,
    result_object_key VARCHAR(512),
    result_sha256 CHAR(64),
    result_size_bytes BIGINT,
    result_media_type VARCHAR(255),
    result_created_at TIMESTAMPTZ,
    requested_by VARCHAR(128) NOT NULL,
    max_attempts SMALLINT NOT NULL,
    attempt_count SMALLINT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    lease_owner VARCHAR(128),
    lease_token BIGINT NOT NULL DEFAULT 0,
    leased_until TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ,
    last_error VARCHAR(2048),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_async_jobs PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_async_jobs_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT ck_async_jobs_specialization CHECK (specialization IN ('reporting')),
    CONSTRAINT ck_async_jobs_operation CHECK (operation ~ '^[a-z][a-z0-9.-]{2,127}$'),
    CONSTRAINT ck_async_jobs_hashes CHECK (
        payload_sha256 ~ '^[0-9a-f]{64}$'
        AND (result_sha256 IS NULL OR result_sha256 ~ '^[0-9a-f]{64}$')
    ),
    CONSTRAINT ck_async_jobs_sizes CHECK (
        payload_size_bytes BETWEEN 0 AND 10737418240
        AND (result_size_bytes IS NULL OR result_size_bytes BETWEEN 0 AND 10737418240)
    ),
    CONSTRAINT ck_async_jobs_attempts CHECK (
        max_attempts BETWEEN 1 AND 20
        AND attempt_count BETWEEN 0 AND max_attempts
        AND lease_token >= 0
    ),
    CONSTRAINT ck_async_jobs_status CHECK (
        status IN ('queued', 'leased', 'retry-wait', 'completed', 'dead-letter')
    ),
    CONSTRAINT ck_async_jobs_lease_state CHECK (
        (status = 'leased' AND lease_owner IS NOT NULL AND leased_until IS NOT NULL)
        OR (status <> 'leased' AND lease_owner IS NULL AND leased_until IS NULL)
    ),
    CONSTRAINT ck_async_jobs_schedule_state CHECK (
        (status IN ('queued', 'retry-wait') AND next_attempt_at IS NOT NULL)
        OR (status NOT IN ('queued', 'retry-wait') AND next_attempt_at IS NULL)
    ),
    CONSTRAINT ck_async_jobs_terminal_state CHECK (
        (status = 'completed' AND completed_at IS NOT NULL AND result_object_key IS NOT NULL
            AND result_sha256 IS NOT NULL AND result_size_bytes IS NOT NULL
            AND result_media_type IS NOT NULL AND result_created_at IS NOT NULL)
        OR (status <> 'completed' AND completed_at IS NULL)
    ),
    CONSTRAINT ck_async_jobs_dead_letter CHECK (
        status <> 'dead-letter' OR (attempt_count = max_attempts AND last_error IS NOT NULL)
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS async_jobs_p0 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS async_jobs_p1 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS async_jobs_p2 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS async_jobs_p3 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS async_jobs_p4 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS async_jobs_p5 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS async_jobs_p6 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS async_jobs_p7 PARTITION OF async_jobs
    FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_async_jobs_claim
    ON async_jobs (tenant_id, specialization, next_attempt_at, created_at, id)
    WHERE status IN ('queued', 'retry-wait');
CREATE INDEX IF NOT EXISTS idx_async_jobs_expired_lease
    ON async_jobs (tenant_id, specialization, leased_until, created_at, id)
    WHERE status = 'leased';
CREATE INDEX IF NOT EXISTS idx_async_jobs_dead_letter
    ON async_jobs (tenant_id, updated_at DESC, id)
    WHERE status = 'dead-letter';
CREATE INDEX IF NOT EXISTS idx_async_jobs_list
    ON async_jobs (tenant_id, created_at, id);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    aggregate_type VARCHAR(96) NOT NULL,
    aggregate_id VARCHAR(128) NOT NULL,
    event_name VARCHAR(128) NOT NULL,
    idempotency_key VARCHAR(192) NOT NULL,
    payload JSONB NOT NULL,
    max_attempts SMALLINT NOT NULL,
    attempt_count SMALLINT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    lease_owner VARCHAR(128),
    lease_token BIGINT NOT NULL DEFAULT 0,
    leased_until TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ,
    last_error VARCHAR(2048),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_outbox_events PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_outbox_events_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT ck_outbox_event_name CHECK (event_name ~ '^[a-z][a-z0-9.-]{2,127}$'),
    CONSTRAINT ck_outbox_payload_size CHECK (octet_length(payload::text) <= 65536),
    CONSTRAINT ck_outbox_attempts CHECK (
        max_attempts BETWEEN 1 AND 20
        AND attempt_count BETWEEN 0 AND max_attempts
        AND lease_token >= 0
    ),
    CONSTRAINT ck_outbox_status CHECK (
        status IN ('queued', 'leased', 'retry-wait', 'completed', 'dead-letter')
    ),
    CONSTRAINT ck_outbox_lease_state CHECK (
        (status = 'leased' AND lease_owner IS NOT NULL AND leased_until IS NOT NULL)
        OR (status <> 'leased' AND lease_owner IS NULL AND leased_until IS NULL)
    ),
    CONSTRAINT ck_outbox_schedule_state CHECK (
        (status IN ('queued', 'retry-wait') AND next_attempt_at IS NOT NULL)
        OR (status NOT IN ('queued', 'retry-wait') AND next_attempt_at IS NULL)
    ),
    CONSTRAINT ck_outbox_completion CHECK (
        (status = 'completed' AND completed_at IS NOT NULL)
        OR (status <> 'completed' AND completed_at IS NULL)
    ),
    CONSTRAINT ck_outbox_dead_letter CHECK (
        status <> 'dead-letter' OR (attempt_count = max_attempts AND last_error IS NOT NULL)
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS outbox_events_p0 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS outbox_events_p1 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS outbox_events_p2 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS outbox_events_p3 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS outbox_events_p4 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS outbox_events_p5 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS outbox_events_p6 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS outbox_events_p7 PARTITION OF outbox_events
    FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_outbox_events_claim
    ON outbox_events (tenant_id, next_attempt_at, created_at, id)
    WHERE status IN ('queued', 'retry-wait');
CREATE INDEX IF NOT EXISTS idx_outbox_events_expired_lease
    ON outbox_events (tenant_id, leased_until, created_at, id)
    WHERE status = 'leased';
CREATE INDEX IF NOT EXISTS idx_outbox_events_dead_letter
    ON outbox_events (tenant_id, updated_at DESC, id)
    WHERE status = 'dead-letter';
CREATE INDEX IF NOT EXISTS idx_outbox_events_list
    ON outbox_events (tenant_id, created_at, id);
CREATE INDEX IF NOT EXISTS idx_audit_events_async_processing
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('async-job', 'outbox-event');

COMMIT;
