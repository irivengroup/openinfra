-- Generated deterministically from installers/migrations/postgresql/0044_field_operations_mobile_offline.sql.
-- Source SHA-256: 9d8cd622c420070c570622aa5f6d8c1c74c84b2709320f649d239b782813c063
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE field_operation_sheets (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    target_type VARCHAR2(128 CHAR) NOT NULL,
    target_id VARCHAR2(128 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    owner VARCHAR2(255 CHAR) NOT NULL,
    operator_name VARCHAR2(255 CHAR) NOT NULL,
    version NUMBER(10) NOT NULL,
    payload CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT field_operation_target_type_valid CHECK (
        target_type IN ('equipment','rack','cable','power-device','certificate')
    ),
    CONSTRAINT field_operation_target_id_valid CHECK (length(target_id) BETWEEN 1 AND 256),
    CONSTRAINT field_operation_site_valid CHECK (REGEXP_LIKE(site_code, '^[A-Z0-9][A-Z0-9_.:-]{0,63}$')),
    CONSTRAINT field_operation_status_valid CHECK (
        status IN ('ready','in-progress','completed','cancelled')
    ),
    CONSTRAINT field_operation_owner_valid CHECK (length(trim(owner)) BETWEEN 2 AND 128),
    CONSTRAINT field_operation_operator_valid CHECK (length(trim(operator_name)) BETWEEN 2 AND 128),
    CONSTRAINT field_operation_version_valid CHECK (version >= 1),
    CONSTRAINT field_operation_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT field_operation_timestamps_ordered CHECK (updated_at >= created_at),
    CONSTRAINT ck_field_operation_sheets_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE field_evidence (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sheet_id VARCHAR2(36 CHAR) NOT NULL,
    phase VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    content_sha256 CHAR(64 CHAR) NOT NULL,
    size_bytes NUMBER(10) NOT NULL,
    payload CLOB NOT NULL,
    attached_at TIMESTAMP WITH TIME ZONE NOT NULL,
    validated_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT field_evidence_phase_valid CHECK (phase IN ('before','after')),
    CONSTRAINT field_evidence_status_valid CHECK (status IN ('attached','validated')),
    CONSTRAINT field_evidence_sha_valid CHECK (REGEXP_LIKE(content_sha256, '^[a-f0-9]{64}$')),
    CONSTRAINT field_evidence_size_valid CHECK (size_bytes BETWEEN 1 AND 2097152),
    CONSTRAINT field_evidence_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT field_evidence_validation_ordered CHECK (
        validated_at IS NULL OR validated_at >= attached_at
    ),
    CONSTRAINT ck_field_evidence_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE intervention_locks (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sheet_id VARCHAR2(36 CHAR) NOT NULL,
    target_type VARCHAR2(128 CHAR) NOT NULL,
    target_id VARCHAR2(128 CHAR) NOT NULL,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    owner VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    released_at TIMESTAMP WITH TIME ZONE,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT intervention_lock_target_type_valid CHECK (
        target_type IN ('equipment','rack','cable','power-device','certificate')
    ),
    CONSTRAINT intervention_lock_target_id_valid CHECK (length(target_id) BETWEEN 1 AND 256),
    CONSTRAINT intervention_lock_idempotency_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$')
    ),
    CONSTRAINT intervention_lock_owner_valid CHECK (length(trim(owner)) BETWEEN 2 AND 128),
    CONSTRAINT intervention_lock_status_valid CHECK (status IN ('active','released')),
    CONSTRAINT intervention_lock_expiration_valid CHECK (expires_at > acquired_at),
    CONSTRAINT intervention_lock_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_intervention_locks_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE offline_sync_packages (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sheet_id VARCHAR2(36 CHAR) NOT NULL,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    authorized_site VARCHAR2(255 CHAR) NOT NULL,
    payload_sha256 CHAR(64 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    package_payload CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    synchronized_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT offline_package_idempotency_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$')
    ),
    CONSTRAINT offline_package_site_valid CHECK (
        REGEXP_LIKE(authorized_site, '^[A-Z0-9][A-Z0-9_.:-]{0,63}$')
    ),
    CONSTRAINT offline_package_sha_valid CHECK (REGEXP_LIKE(payload_sha256, '^[a-f0-9]{64}$')),
    CONSTRAINT offline_package_status_valid CHECK (status IN ('ready','synchronized','revoked')),
    CONSTRAINT offline_package_payload_object CHECK (JSON_EXISTS(package_payload, '$?(@.type() == \"object\")')),
    CONSTRAINT offline_package_expiration_valid CHECK (expires_at > created_at),
    CONSTRAINT offline_package_sync_ordered CHECK (
        synchronized_at IS NULL OR synchronized_at >= created_at
    ),
    CONSTRAINT ck_offline_sync_packages_package_payload_json CHECK (package_payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE field_event_outbox (
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
    CONSTRAINT field_event_name_valid CHECK (REGEXP_LIKE(event_name, '^[a-z][a-z0-9_.-]{2,120}$')),
    CONSTRAINT field_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT field_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_field_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_field_operation_sheet_listing
    ON field_operation_sheets (tenant_id, site_code, status, updated_at DESC, id DESC);

CREATE INDEX idx_field_operation_sheet_target
    ON field_operation_sheets (tenant_id, target_type, target_id, updated_at DESC);

CREATE INDEX idx_field_evidence_sheet
    ON field_evidence (tenant_id, sheet_id, phase, attached_at, id);

CREATE INDEX idx_field_evidence_hash
    ON field_evidence (tenant_id, content_sha256);

CREATE INDEX idx_intervention_locks_target
    ON intervention_locks (tenant_id, target_type, target_id, status, expires_at DESC);

CREATE INDEX idx_intervention_locks_sheet
    ON intervention_locks (tenant_id, sheet_id, acquired_at DESC);

CREATE INDEX idx_offline_sync_packages_sheet
    ON offline_sync_packages (tenant_id, sheet_id, created_at DESC, id DESC);

CREATE INDEX idx_offline_sync_packages_expiration
    ON offline_sync_packages (tenant_id, status, expires_at);

CREATE INDEX idx_field_event_outbox_pending
    ON field_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_field_operations
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
