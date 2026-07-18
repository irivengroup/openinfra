-- Generated deterministically from installers/migrations/postgresql/0052_multisite_disaster_recovery.sql.
-- Source SHA-256: 3320e65f50bf25b11366c5806cf60bdf287d33c882ceb5bf2356846b998b5d88
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE multisite_dr_plans (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(64 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR2(128 CHAR) NOT NULL,
    primary_site_code VARCHAR2(64 CHAR) NOT NULL,
    recovery_site_code VARCHAR2(64 CHAR) NOT NULL,
    replication_mode VARCHAR2(32 CHAR) NOT NULL,
    rpo_seconds NUMBER(10) NOT NULL,
    rto_seconds NUMBER(10) NOT NULL,
    max_backup_age_seconds NUMBER(10) NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    configured_by VARCHAR2(128 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    disabled_at TIMESTAMP WITH TIME ZONE NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, primary_site_code, recovery_site_code),
    CHECK (length(trim(name)) BETWEEN 3 AND 128),
    CHECK (REGEXP_LIKE(primary_site_code, '^[A-Z0-9][A-Z0-9_-]{1,63}$')),
    CHECK (REGEXP_LIKE(recovery_site_code, '^[A-Z0-9][A-Z0-9_-]{1,63}$')),
    CHECK (primary_site_code <> recovery_site_code),
    CHECK (replication_mode IN ('asynchronous', 'synchronous')),
    CHECK (rpo_seconds BETWEEN 1 AND 86400),
    CHECK (rto_seconds BETWEEN 1 AND 604800),
    CHECK (max_backup_age_seconds BETWEEN 60 AND 2592000),
    CHECK ((active AND disabled_at IS NULL) OR (NOT active AND disabled_at IS NOT NULL)),
    CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_multisite_dr_plans_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_multisite_dr_plans_active
    ON multisite_dr_plans (tenant_id, active, primary_site_code, recovery_site_code);

CREATE TABLE multisite_dr_drills (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(64 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id VARCHAR2(36 CHAR) NOT NULL,
    scenario VARCHAR2(64 CHAR) NOT NULL,
    unavailable_site_code VARCHAR2(64 CHAR) NOT NULL,
    recovery_site_code VARCHAR2(64 CHAR) NOT NULL,
    status VARCHAR2(16 CHAR) NOT NULL,
    replication_lag_seconds NUMBER(10) NOT NULL,
    backup_age_seconds NUMBER(10) NOT NULL,
    measured_rto_seconds NUMBER(10) NOT NULL,
    restore_verified NUMBER(1) NOT NULL,
    recovery_available NUMBER(1) NOT NULL,
    vip_reachable NUMBER(1) NOT NULL,
    operator_confirmed NUMBER(1) NOT NULL,
    executed_by VARCHAR2(128 CHAR) NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, plan_id)
        REFERENCES multisite_dr_plans (tenant_id, id),
    CHECK (scenario = 'primary-site-loss'),
    CHECK (status IN ('passed', 'failed')),
    CHECK (replication_lag_seconds >= 0),
    CHECK (backup_age_seconds >= 0),
    CHECK (measured_rto_seconds >= 0),
    CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_multisite_dr_drills_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_multisite_dr_drills_plan_time
    ON multisite_dr_drills (tenant_id, plan_id, executed_at DESC);

CREATE INDEX idx_multisite_dr_drills_status_time
    ON multisite_dr_drills (tenant_id, status, executed_at DESC);

CREATE INDEX idx_audit_events_multisite_dr
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
