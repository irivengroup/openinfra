-- Generated deterministically from installers/migrations/postgresql/0055_kubernetes_topology_inventory.sql.
-- Source SHA-256: aedc26690b57eaa0f79128bdb4d2f0198f124e2fa5c1cc4bb78d32e7b74cbde4
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE kubernetes_topology_snapshots (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cluster_key VARCHAR2(128 CHAR) NOT NULL,
    provider VARCHAR2(255 CHAR) NOT NULL,
    site_code VARCHAR2(128 CHAR),
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    imported_at TIMESTAMP WITH TIME ZONE NOT NULL,
    fingerprint CHAR(64 CHAR) NOT NULL,
    resource_count NUMBER(10) NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint),
    CONSTRAINT kubernetes_topology_fingerprint_valid CHECK (REGEXP_LIKE(fingerprint, '^[a-f0-9]{64}$')),
    CONSTRAINT kubernetes_topology_resource_count_valid CHECK (
        resource_count BETWEEN 1 AND 50000
    ),
    CONSTRAINT kubernetes_topology_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_kubernetes_topology_snapshots_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE kubernetes_topology_event_outbox (
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
    CONSTRAINT kubernetes_topology_event_name_valid CHECK (
        REGEXP_LIKE(name, '^[a-z][a-z0-9_.-]{2,120}$')
    ),
    CONSTRAINT kubernetes_topology_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT kubernetes_topology_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_kubernetes_topology_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_kubernetes_topology_latest
    ON kubernetes_topology_snapshots (
        tenant_id, cluster_key, observed_at DESC, imported_at DESC, id DESC
    );

CREATE INDEX idx_kubernetes_topology_provider_site
    ON kubernetes_topology_snapshots (
        tenant_id, provider, site_code, observed_at DESC, imported_at DESC, id DESC
    );

CREATE INDEX idx_kubernetes_topology_event_outbox_pending
    ON kubernetes_topology_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_kubernetes_topology
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
