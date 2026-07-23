-- OpenInfra v0.33.5 - P21 / EPIC-2104 Kubernetes GitOps expected state and drift governance
BEGIN;

CREATE TABLE IF NOT EXISTS kubernetes_gitops_states (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cluster_key text NOT NULL,
    environment text NOT NULL,
    owner text NOT NULL,
    revision text NOT NULL,
    captured_at timestamptz NOT NULL,
    imported_at timestamptz NOT NULL,
    fingerprint char(64) NOT NULL,
    resource_count integer NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint),
    CONSTRAINT kubernetes_gitops_revision_valid CHECK (
        revision ~ '^[a-f0-9]{40}$' OR revision ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT kubernetes_gitops_fingerprint_valid CHECK (fingerprint ~ '^[a-f0-9]{64}$'),
    CONSTRAINT kubernetes_gitops_resource_count_valid CHECK (
        resource_count BETWEEN 1 AND 50000
    ),
    CONSTRAINT kubernetes_gitops_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS kubernetes_gitops_event_outbox (
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
    CONSTRAINT kubernetes_gitops_event_name_valid CHECK (
        name ~ '^[a-z][a-z0-9_.-]{2,120}$'
    ),
    CONSTRAINT kubernetes_gitops_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT kubernetes_gitops_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

DO $partitioning$
DECLARE
    table_name text;
    partition_index integer;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'kubernetes_gitops_states',
        'kubernetes_gitops_event_outbox'
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

CREATE INDEX IF NOT EXISTS idx_kubernetes_gitops_latest
    ON kubernetes_gitops_states (
        tenant_id, cluster_key, captured_at DESC, imported_at DESC, id DESC
    );
CREATE INDEX IF NOT EXISTS idx_kubernetes_gitops_owner_environment
    ON kubernetes_gitops_states (
        tenant_id, owner, environment, captured_at DESC, imported_at DESC, id DESC
    );
CREATE INDEX IF NOT EXISTS idx_kubernetes_gitops_payload
    ON kubernetes_gitops_states USING gin (payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_kubernetes_gitops_event_outbox_pending
    ON kubernetes_gitops_event_outbox (tenant_id, occurred_at, id)
    WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_kubernetes_gitops_event_outbox_occurred_brin
    ON kubernetes_gitops_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_audit_events_kubernetes_gitops
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'kubernetes_gitops_state';

COMMIT;
