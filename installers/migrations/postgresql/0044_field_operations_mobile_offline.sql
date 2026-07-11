-- OpenInfra v0.29.95 - P16 / EPIC-1601 Field Operations mobile/offline
BEGIN;

CREATE TABLE IF NOT EXISTS field_operation_sheets (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    target_type text NOT NULL,
    target_id text NOT NULL,
    site_code text NOT NULL,
    status text NOT NULL,
    owner text NOT NULL,
    operator_name text NOT NULL,
    version integer NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT field_operation_target_type_valid CHECK (
        target_type IN ('equipment','rack','cable','power-device','certificate')
    ),
    CONSTRAINT field_operation_target_id_valid CHECK (length(target_id) BETWEEN 1 AND 256),
    CONSTRAINT field_operation_site_valid CHECK (site_code ~ '^[A-Z0-9][A-Z0-9_.:-]{0,63}$'),
    CONSTRAINT field_operation_status_valid CHECK (
        status IN ('ready','in-progress','completed','cancelled')
    ),
    CONSTRAINT field_operation_owner_valid CHECK (length(trim(owner)) BETWEEN 2 AND 128),
    CONSTRAINT field_operation_operator_valid CHECK (length(trim(operator_name)) BETWEEN 2 AND 128),
    CONSTRAINT field_operation_version_valid CHECK (version >= 1),
    CONSTRAINT field_operation_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT field_operation_timestamps_ordered CHECK (updated_at >= created_at)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS field_evidence (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sheet_id uuid NOT NULL,
    phase text NOT NULL,
    status text NOT NULL,
    content_sha256 char(64) NOT NULL,
    size_bytes integer NOT NULL,
    payload jsonb NOT NULL,
    attached_at timestamptz NOT NULL,
    validated_at timestamptz,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT field_evidence_phase_valid CHECK (phase IN ('before','after')),
    CONSTRAINT field_evidence_status_valid CHECK (status IN ('attached','validated')),
    CONSTRAINT field_evidence_sha_valid CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    CONSTRAINT field_evidence_size_valid CHECK (size_bytes BETWEEN 1 AND 2097152),
    CONSTRAINT field_evidence_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT field_evidence_validation_ordered CHECK (
        validated_at IS NULL OR validated_at >= attached_at
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS intervention_locks (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sheet_id uuid NOT NULL,
    target_type text NOT NULL,
    target_id text NOT NULL,
    idempotency_key text NOT NULL,
    owner text NOT NULL,
    status text NOT NULL,
    acquired_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    released_at timestamptz,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT intervention_lock_target_type_valid CHECK (
        target_type IN ('equipment','rack','cable','power-device','certificate')
    ),
    CONSTRAINT intervention_lock_target_id_valid CHECK (length(target_id) BETWEEN 1 AND 256),
    CONSTRAINT intervention_lock_idempotency_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$'
    ),
    CONSTRAINT intervention_lock_owner_valid CHECK (length(trim(owner)) BETWEEN 2 AND 128),
    CONSTRAINT intervention_lock_status_valid CHECK (status IN ('active','released')),
    CONSTRAINT intervention_lock_expiration_valid CHECK (expires_at > acquired_at),
    CONSTRAINT intervention_lock_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS offline_sync_packages (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sheet_id uuid NOT NULL,
    idempotency_key text NOT NULL,
    authorized_site text NOT NULL,
    payload_sha256 char(64) NOT NULL,
    status text NOT NULL,
    package_payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    synchronized_at timestamptz,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT offline_package_idempotency_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$'
    ),
    CONSTRAINT offline_package_site_valid CHECK (
        authorized_site ~ '^[A-Z0-9][A-Z0-9_.:-]{0,63}$'
    ),
    CONSTRAINT offline_package_sha_valid CHECK (payload_sha256 ~ '^[a-f0-9]{64}$'),
    CONSTRAINT offline_package_status_valid CHECK (status IN ('ready','synchronized','revoked')),
    CONSTRAINT offline_package_payload_object CHECK (jsonb_typeof(package_payload) = 'object'),
    CONSTRAINT offline_package_expiration_valid CHECK (expires_at > created_at),
    CONSTRAINT offline_package_sync_ordered CHECK (
        synchronized_at IS NULL OR synchronized_at >= created_at
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS field_event_outbox (
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
    CONSTRAINT field_event_name_valid CHECK (event_name ~ '^[a-z][a-z0-9_.-]{2,120}$'),
    CONSTRAINT field_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT field_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS field_operation_sheets_p00 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p01 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p02 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p03 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p04 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p05 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p06 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p07 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p08 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p09 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p10 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p11 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p12 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p13 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p14 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS field_operation_sheets_p15 PARTITION OF field_operation_sheets FOR VALUES WITH (MODULUS 16, REMAINDER 15);
CREATE TABLE IF NOT EXISTS field_evidence_p00 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS field_evidence_p01 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS field_evidence_p02 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS field_evidence_p03 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS field_evidence_p04 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS field_evidence_p05 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS field_evidence_p06 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS field_evidence_p07 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS field_evidence_p08 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS field_evidence_p09 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS field_evidence_p10 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS field_evidence_p11 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS field_evidence_p12 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS field_evidence_p13 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS field_evidence_p14 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS field_evidence_p15 PARTITION OF field_evidence FOR VALUES WITH (MODULUS 16, REMAINDER 15);
CREATE TABLE IF NOT EXISTS intervention_locks_p00 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS intervention_locks_p01 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS intervention_locks_p02 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS intervention_locks_p03 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS intervention_locks_p04 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS intervention_locks_p05 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS intervention_locks_p06 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS intervention_locks_p07 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS intervention_locks_p08 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS intervention_locks_p09 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS intervention_locks_p10 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS intervention_locks_p11 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS intervention_locks_p12 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS intervention_locks_p13 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS intervention_locks_p14 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS intervention_locks_p15 PARTITION OF intervention_locks FOR VALUES WITH (MODULUS 16, REMAINDER 15);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p00 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p01 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p02 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p03 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p04 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p05 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p06 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p07 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p08 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p09 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p10 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p11 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p12 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p13 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p14 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS offline_sync_packages_p15 PARTITION OF offline_sync_packages FOR VALUES WITH (MODULUS 16, REMAINDER 15);
CREATE TABLE IF NOT EXISTS field_event_outbox_p00 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS field_event_outbox_p01 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS field_event_outbox_p02 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS field_event_outbox_p03 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS field_event_outbox_p04 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS field_event_outbox_p05 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS field_event_outbox_p06 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS field_event_outbox_p07 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS field_event_outbox_p08 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS field_event_outbox_p09 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS field_event_outbox_p10 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS field_event_outbox_p11 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS field_event_outbox_p12 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS field_event_outbox_p13 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS field_event_outbox_p14 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS field_event_outbox_p15 PARTITION OF field_event_outbox FOR VALUES WITH (MODULUS 16, REMAINDER 15);
CREATE INDEX IF NOT EXISTS idx_field_operation_sheet_listing
    ON field_operation_sheets (tenant_id, site_code, status, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_field_operation_sheet_target
    ON field_operation_sheets (tenant_id, target_type, target_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_field_operation_sheet_payload
    ON field_operation_sheets USING gin (payload jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_field_evidence_sheet
    ON field_evidence (tenant_id, sheet_id, phase, attached_at, id);
CREATE INDEX IF NOT EXISTS idx_field_evidence_hash
    ON field_evidence (tenant_id, content_sha256);
CREATE INDEX IF NOT EXISTS idx_field_evidence_attached_brin
    ON field_evidence USING brin (attached_at) WITH (pages_per_range = 64);

CREATE INDEX IF NOT EXISTS idx_intervention_locks_target
    ON intervention_locks (tenant_id, target_type, target_id, status, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_intervention_locks_sheet
    ON intervention_locks (tenant_id, sheet_id, acquired_at DESC);

CREATE INDEX IF NOT EXISTS idx_offline_sync_packages_sheet
    ON offline_sync_packages (tenant_id, sheet_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_offline_sync_packages_expiration
    ON offline_sync_packages (tenant_id, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_field_event_outbox_pending
    ON field_event_outbox (tenant_id, occurred_at, id)
    WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_field_event_outbox_occurred_brin
    ON field_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);

CREATE INDEX IF NOT EXISTS idx_audit_events_field_operations
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN (
        'field_operation_sheet','field_evidence','intervention_lock','offline_sync_package'
    );

COMMIT;
