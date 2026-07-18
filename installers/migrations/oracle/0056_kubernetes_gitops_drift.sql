-- Generated deterministically from installers/migrations/postgresql/0056_kubernetes_gitops_drift.sql.
-- Source SHA-256: fa0d5f90ad59a9e8bc9f1eeb753944fd5cfd9cae58dfb86d7368585962befed0
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE kubernetes_gitops_states (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cluster_key VARCHAR2(128 CHAR) NOT NULL,
    environment VARCHAR2(255 CHAR) NOT NULL,
    owner VARCHAR2(255 CHAR) NOT NULL,
    revision VARCHAR2(255 CHAR) NOT NULL,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    imported_at TIMESTAMP WITH TIME ZONE NOT NULL,
    fingerprint CHAR(64 CHAR) NOT NULL,
    resource_count NUMBER(10) NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint),
    CONSTRAINT kubernetes_gitops_revision_valid CHECK (
        REGEXP_LIKE(revision, '^[a-f0-9]{40}$') OR REGEXP_LIKE(revision, '^[a-f0-9]{64}$')
    ),
    CONSTRAINT kubernetes_gitops_fingerprint_valid CHECK (REGEXP_LIKE(fingerprint, '^[a-f0-9]{64}$')),
    CONSTRAINT kubernetes_gitops_resource_count_valid CHECK (
        resource_count BETWEEN 1 AND 50000
    ),
    CONSTRAINT kubernetes_gitops_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_kubernetes_gitops_states_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE kubernetes_gitops_event_outbox (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id VARCHAR2(36 CHAR) NOT NULL,
    name VARCHAR2(255 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    attempt_count NUMBER(10) DEFAULT 0 NOT NULL,
    last_error VARCHAR2(255 CHAR),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT kubernetes_gitops_event_name_valid CHECK (
        REGEXP_LIKE(name, '^[a-z][a-z0-9_.-]{2,120}$')
    ),
    CONSTRAINT kubernetes_gitops_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT kubernetes_gitops_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_kubernetes_gitops_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_kubernetes_gitops_latest
    ON kubernetes_gitops_states (
        tenant_id, cluster_key, captured_at DESC, imported_at DESC, id DESC
    );

CREATE INDEX idx_kubernetes_gitops_owner_environment
    ON kubernetes_gitops_states (
        tenant_id, owner, environment, captured_at DESC, imported_at DESC, id DESC
    );

CREATE INDEX idx_kubernetes_gitops_event_outbox_pending
    ON kubernetes_gitops_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_kubernetes_gitops
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
