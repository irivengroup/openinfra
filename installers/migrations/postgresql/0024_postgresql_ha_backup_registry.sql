-- OpenInfra v0.29.7 - P06 PostgreSQL HA, PITR backup registry and failover audit

CREATE TABLE IF NOT EXISTS postgresql_ha_nodes (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    node_name text NOT NULL,
    role text NOT NULL,
    endpoint text NOT NULL,
    replication_state text NOT NULL,
    synchronous_state text NULL,
    timeline_id bigint NULL,
    replay_lag_ms bigint NULL,
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT postgresql_ha_nodes_name_check CHECK (length(trim(node_name)) BETWEEN 2 AND 128),
    CONSTRAINT postgresql_ha_nodes_role_check CHECK (role IN ('primary', 'standby', 'witness')),
    CONSTRAINT postgresql_ha_nodes_replication_state_check CHECK (
        replication_state IN ('streaming', 'catchup', 'archive_recovery', 'paused', 'unknown')
    ),
    CONSTRAINT postgresql_ha_nodes_sync_state_check CHECK (
        synchronous_state IS NULL OR synchronous_state IN ('sync', 'potential', 'async', 'quorum')
    ),
    CONSTRAINT postgresql_ha_nodes_lag_check CHECK (replay_lag_ms IS NULL OR replay_lag_ms >= 0)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p00 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p01 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p02 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p03 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p04 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p05 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p06 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS postgresql_ha_nodes_p07 PARTITION OF postgresql_ha_nodes
    FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE UNIQUE INDEX IF NOT EXISTS idx_postgresql_ha_nodes_name
    ON postgresql_ha_nodes (tenant_id, node_name);
CREATE INDEX IF NOT EXISTS idx_postgresql_ha_nodes_role_state
    ON postgresql_ha_nodes (tenant_id, role, replication_state, updated_at DESC);

CREATE TABLE IF NOT EXISTS postgresql_backup_runs (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    backup_kind text NOT NULL,
    status text NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz NULL,
    base_backup_path text NULL,
    wal_archive_path text NOT NULL,
    timeline_id bigint NULL,
    start_lsn pg_lsn NULL,
    stop_lsn pg_lsn NULL,
    size_bytes bigint NULL,
    checksum_sha256 text NULL,
    error_message text NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT postgresql_backup_runs_kind_check CHECK (backup_kind IN ('basebackup', 'wal_archive', 'pitr_test')),
    CONSTRAINT postgresql_backup_runs_status_check CHECK (status IN ('planned', 'running', 'succeeded', 'failed', 'cancelled')),
    CONSTRAINT postgresql_backup_runs_finished_check CHECK (finished_at IS NULL OR finished_at >= started_at),
    CONSTRAINT postgresql_backup_runs_size_check CHECK (size_bytes IS NULL OR size_bytes >= 0),
    CONSTRAINT postgresql_backup_runs_checksum_check CHECK (
        checksum_sha256 IS NULL OR checksum_sha256 ~ '^[a-f0-9]{64}$'
    )
) PARTITION BY RANGE (started_at);

CREATE TABLE IF NOT EXISTS postgresql_backup_runs_default PARTITION OF postgresql_backup_runs DEFAULT;
CREATE INDEX IF NOT EXISTS idx_postgresql_backup_runs_status
    ON postgresql_backup_runs (tenant_id, status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_postgresql_backup_runs_timeline
    ON postgresql_backup_runs (tenant_id, timeline_id, started_at DESC);

CREATE TABLE IF NOT EXISTS postgresql_failover_events (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_kind text NOT NULL,
    previous_primary text NOT NULL,
    candidate_primary text NOT NULL,
    decision text NOT NULL,
    operator text NOT NULL,
    precheck_report jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT postgresql_failover_events_kind_check CHECK (
        event_kind IN ('planned_switchover', 'manual_failover', 'failover_drill')
    ),
    CONSTRAINT postgresql_failover_events_decision_check CHECK (
        decision IN ('approved', 'rejected', 'aborted')
    ),
    CONSTRAINT postgresql_failover_events_precheck_check CHECK (jsonb_typeof(precheck_report) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS postgresql_failover_events_p00 PARTITION OF postgresql_failover_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE IF NOT EXISTS postgresql_failover_events_p01 PARTITION OF postgresql_failover_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE IF NOT EXISTS postgresql_failover_events_p02 PARTITION OF postgresql_failover_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE IF NOT EXISTS postgresql_failover_events_p03 PARTITION OF postgresql_failover_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

CREATE INDEX IF NOT EXISTS idx_postgresql_failover_events_time
    ON postgresql_failover_events (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_postgresql_failover_events_precheck_gin
    ON postgresql_failover_events USING gin (precheck_report);


CREATE INDEX IF NOT EXISTS idx_audit_events_postgresql_ha
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('postgresql_ha_node', 'postgresql_backup_run', 'postgresql_failover_event');
