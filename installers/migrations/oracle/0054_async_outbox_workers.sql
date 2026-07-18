-- Generated deterministically from installers/migrations/postgresql/0054_async_outbox_workers.sql.
-- Source SHA-256: b6c6cbfc491558e13f58de4943bfcbf016b96649938be3a03c2b6509cc8fc001
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE async_jobs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(64 CHAR) NOT NULL,
    specialization VARCHAR2(64 CHAR) NOT NULL,
    operation VARCHAR2(128 CHAR) NOT NULL,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    payload_object_key VARCHAR2(512 CHAR) NOT NULL,
    payload_sha256 CHAR(64 CHAR) NOT NULL,
    payload_size_bytes NUMBER(19) NOT NULL,
    payload_media_type VARCHAR2(255 CHAR) NOT NULL,
    payload_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    result_object_key VARCHAR2(512 CHAR),
    result_sha256 CHAR(64 CHAR),
    result_size_bytes NUMBER(19),
    result_media_type VARCHAR2(255 CHAR),
    result_created_at TIMESTAMP WITH TIME ZONE,
    requested_by VARCHAR2(128 CHAR) NOT NULL,
    max_attempts NUMBER(5) NOT NULL,
    attempt_count NUMBER(5) DEFAULT 0 NOT NULL,
    status VARCHAR2(32 CHAR) NOT NULL,
    lease_owner VARCHAR2(128 CHAR),
    lease_token NUMBER(19) DEFAULT 0 NOT NULL,
    leased_until TIMESTAMP WITH TIME ZONE,
    next_attempt_at TIMESTAMP WITH TIME ZONE,
    last_error VARCHAR2(1000 CHAR),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_async_jobs PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_async_jobs_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT ck_async_jobs_specialization CHECK (specialization IN ('reporting')),
    CONSTRAINT ck_async_jobs_operation CHECK (REGEXP_LIKE(operation, '^[a-z][a-z0-9.-]{2,127}$')),
    CONSTRAINT ck_async_jobs_hashes CHECK (
        REGEXP_LIKE(payload_sha256, '^[0-9a-f]{64}$')
        AND (result_sha256 IS NULL OR REGEXP_LIKE(result_sha256, '^[0-9a-f]{64}$'))
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
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_async_jobs_claim
    ON async_jobs (tenant_id, specialization, next_attempt_at, created_at, id);

CREATE INDEX idx_async_jobs_expired_lease
    ON async_jobs (tenant_id, specialization, leased_until, created_at, id);

CREATE INDEX idx_async_jobs_dead_letter
    ON async_jobs (tenant_id, updated_at DESC, id);

CREATE INDEX idx_async_jobs_list
    ON async_jobs (tenant_id, created_at, id);

CREATE TABLE outbox_events (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(64 CHAR) NOT NULL,
    aggregate_type VARCHAR2(96 CHAR) NOT NULL,
    aggregate_id VARCHAR2(128 CHAR) NOT NULL,
    event_name VARCHAR2(128 CHAR) NOT NULL,
    idempotency_key VARCHAR2(192 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    max_attempts NUMBER(5) NOT NULL,
    attempt_count NUMBER(5) DEFAULT 0 NOT NULL,
    status VARCHAR2(32 CHAR) NOT NULL,
    lease_owner VARCHAR2(128 CHAR),
    lease_token NUMBER(19) DEFAULT 0 NOT NULL,
    leased_until TIMESTAMP WITH TIME ZONE,
    next_attempt_at TIMESTAMP WITH TIME ZONE,
    last_error VARCHAR2(1000 CHAR),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_outbox_events PRIMARY KEY (tenant_id, id),
    CONSTRAINT uq_outbox_events_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT ck_outbox_event_name CHECK (REGEXP_LIKE(event_name, '^[a-z][a-z0-9.-]{2,127}$')),
    CONSTRAINT ck_outbox_payload_size CHECK (LENGTH(payload) <= 65536),
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
    ),
    CONSTRAINT ck_outbox_events_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_outbox_events_claim
    ON outbox_events (tenant_id, next_attempt_at, created_at, id);

CREATE INDEX idx_outbox_events_expired_lease
    ON outbox_events (tenant_id, leased_until, created_at, id);

CREATE INDEX idx_outbox_events_dead_letter
    ON outbox_events (tenant_id, updated_at DESC, id);

CREATE INDEX idx_outbox_events_list
    ON outbox_events (tenant_id, created_at, id);

CREATE INDEX idx_audit_events_async_processing
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
