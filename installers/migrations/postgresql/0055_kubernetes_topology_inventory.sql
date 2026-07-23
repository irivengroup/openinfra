-- OpenInfra v0.33.0 - P21 / EPIC-2101 Kubernetes inventory and physical topology mapping
BEGIN;

CREATE TABLE IF NOT EXISTS kubernetes_topology_snapshots (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cluster_key text NOT NULL,
    provider text NOT NULL,
    site_code text,
    observed_at timestamptz NOT NULL,
    imported_at timestamptz NOT NULL,
    fingerprint char(64) NOT NULL,
    resource_count integer NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint),
    CONSTRAINT kubernetes_topology_fingerprint_valid CHECK (fingerprint ~ '^[a-f0-9]{64}$'),
    CONSTRAINT kubernetes_topology_resource_count_valid CHECK (
        resource_count BETWEEN 1 AND 50000
    ),
    CONSTRAINT kubernetes_topology_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS kubernetes_topology_event_outbox (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id uuid NOT NULL,
    name text NOT NULL,
    payload jsonb NOT NULL,
    occurred_at timestamptz NOT NULL,
    published_at timestamptz,
    attempt_count integer NOT NULL DEFAULT 0,
    last_error text,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT kubernetes_topology_event_name_valid CHECK (
        name ~ '^[a-z][a-z0-9_.-]{2,120}$'
    ),
    CONSTRAINT kubernetes_topology_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT kubernetes_topology_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

DO $partitioning$
DECLARE
    table_name text;
    partition_index integer;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'kubernetes_topology_snapshots',
        'kubernetes_topology_event_outbox'
    ]
    LOOP
        FOR partition_index IN 0..15 LOOP
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
                table_name || '_p' || lpad(partition_index::text, 2, '0'),
                table_name,
                partition_index
            );
        END LOOP;
    END LOOP;
END
$partitioning$;

CREATE INDEX IF NOT EXISTS idx_kubernetes_topology_latest
    ON kubernetes_topology_snapshots (
        tenant_id, cluster_key, observed_at DESC, imported_at DESC, id DESC
    );
CREATE INDEX IF NOT EXISTS idx_kubernetes_topology_provider_site
    ON kubernetes_topology_snapshots (
        tenant_id, provider, site_code, observed_at DESC, imported_at DESC, id DESC
    );
CREATE INDEX IF NOT EXISTS idx_kubernetes_topology_payload
    ON kubernetes_topology_snapshots USING gin (payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_kubernetes_topology_event_outbox_pending
    ON kubernetes_topology_event_outbox (tenant_id, occurred_at, id)
    WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kubernetes_topology_event_outbox_occurred_brin
    ON kubernetes_topology_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_audit_events_kubernetes_topology
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'kubernetes_topology_snapshot';

COMMIT;
