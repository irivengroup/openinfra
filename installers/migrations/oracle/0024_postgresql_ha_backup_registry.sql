-- Generated deterministically from installers/migrations/postgresql/0024_postgresql_ha_backup_registry.sql.
-- Source SHA-256: 40532bb90965a41091b0dc2a2e086ac95fe83efc8b8647c7e2c48b0e6be4c415
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE postgresql_ha_nodes (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    node_name VARCHAR2(255 CHAR) NOT NULL,
    role VARCHAR2(255 CHAR) NOT NULL,
    endpoint VARCHAR2(1000 CHAR) NOT NULL,
    replication_state VARCHAR2(255 CHAR) NOT NULL,
    synchronous_state VARCHAR2(255 CHAR) NULL,
    timeline_id NUMBER(19) NULL,
    replay_lag_ms NUMBER(19) NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
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
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE UNIQUE INDEX idx_postgresql_ha_nodes_name
    ON postgresql_ha_nodes (tenant_id, node_name);

CREATE INDEX idx_postgresql_ha_nodes_role_state
    ON postgresql_ha_nodes (tenant_id, role, replication_state, updated_at DESC);

CREATE TABLE postgresql_backup_runs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    backup_kind VARCHAR2(128 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE NULL,
    base_backup_path VARCHAR2(255 CHAR) NULL,
    wal_archive_path VARCHAR2(255 CHAR) NOT NULL,
    timeline_id NUMBER(19) NULL,
    start_lsn pg_lsn NULL,
    stop_lsn pg_lsn NULL,
    size_bytes NUMBER(19) NULL,
    checksum_sha256 VARCHAR2(255 CHAR) NULL,
    error_message CLOB NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, started_at, id),
    CONSTRAINT postgresql_backup_runs_kind_check CHECK (backup_kind IN ('basebackup', 'wal_archive', 'pitr_test')),
    CONSTRAINT postgresql_backup_runs_status_check CHECK (status IN ('planned', 'running', 'succeeded', 'failed', 'cancelled')),
    CONSTRAINT postgresql_backup_runs_finished_check CHECK (finished_at IS NULL OR finished_at >= started_at),
    CONSTRAINT postgresql_backup_runs_size_check CHECK (size_bytes IS NULL OR size_bytes >= 0),
    CONSTRAINT postgresql_backup_runs_checksum_check CHECK (
        checksum_sha256 IS NULL OR REGEXP_LIKE(checksum_sha256, '^[a-f0-9]{64}$')
    )
);

CREATE INDEX idx_postgresql_backup_runs_status
    ON postgresql_backup_runs (tenant_id, status, started_at DESC);

CREATE INDEX idx_postgresql_backup_runs_timeline
    ON postgresql_backup_runs (tenant_id, timeline_id, started_at DESC);

CREATE TABLE postgresql_failover_events (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_kind VARCHAR2(128 CHAR) NOT NULL,
    previous_primary VARCHAR2(255 CHAR) NOT NULL,
    candidate_primary VARCHAR2(255 CHAR) NOT NULL,
    decision VARCHAR2(255 CHAR) NOT NULL,
    operator VARCHAR2(255 CHAR) NOT NULL,
    precheck_report CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT postgresql_failover_events_kind_check CHECK (
        event_kind IN ('planned_switchover', 'manual_failover', 'failover_drill')
    ),
    CONSTRAINT postgresql_failover_events_decision_check CHECK (
        decision IN ('approved', 'rejected', 'aborted')
    ),
    CONSTRAINT postgresql_failover_events_precheck_check CHECK (JSON_EXISTS(precheck_report, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_postgresql_failover_events_precheck_report_json CHECK (precheck_report IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 4;

CREATE INDEX idx_postgresql_failover_events_time
    ON postgresql_failover_events (tenant_id, created_at DESC);

CREATE INDEX idx_audit_events_postgresql_ha
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
