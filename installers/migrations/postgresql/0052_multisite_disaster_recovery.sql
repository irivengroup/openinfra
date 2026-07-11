-- OpenInfra 0.29.104 / EPIC-1703: controlled multisite disaster recovery plans and drills.
BEGIN;

CREATE TABLE IF NOT EXISTS multisite_dr_plans (
    id uuid NOT NULL,
    tenant_id varchar(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name varchar(128) NOT NULL,
    primary_site_code varchar(64) NOT NULL,
    recovery_site_code varchar(64) NOT NULL,
    replication_mode varchar(32) NOT NULL,
    rpo_seconds integer NOT NULL,
    rto_seconds integer NOT NULL,
    max_backup_age_seconds integer NOT NULL,
    active boolean NOT NULL DEFAULT TRUE,
    configured_by varchar(128) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    disabled_at timestamptz NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, primary_site_code, recovery_site_code),
    CHECK (length(trim(name)) BETWEEN 3 AND 128),
    CHECK (primary_site_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
    CHECK (recovery_site_code ~ '^[A-Z0-9][A-Z0-9_-]{1,63}$'),
    CHECK (primary_site_code <> recovery_site_code),
    CHECK (replication_mode IN ('asynchronous', 'synchronous')),
    CHECK (rpo_seconds BETWEEN 1 AND 86400),
    CHECK (rto_seconds BETWEEN 1 AND 604800),
    CHECK (max_backup_age_seconds BETWEEN 60 AND 2592000),
    CHECK ((active AND disabled_at IS NULL) OR (NOT active AND disabled_at IS NOT NULL)),
    CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS multisite_dr_plans_p0
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS multisite_dr_plans_p1
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS multisite_dr_plans_p2
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS multisite_dr_plans_p3
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS multisite_dr_plans_p4
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS multisite_dr_plans_p5
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS multisite_dr_plans_p6
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS multisite_dr_plans_p7
    PARTITION OF multisite_dr_plans FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_multisite_dr_plans_active
    ON multisite_dr_plans (tenant_id, active, primary_site_code, recovery_site_code);
CREATE INDEX IF NOT EXISTS idx_multisite_dr_plans_payload_gin
    ON multisite_dr_plans USING gin (payload);

CREATE TABLE IF NOT EXISTS multisite_dr_drills (
    id uuid NOT NULL,
    tenant_id varchar(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id uuid NOT NULL,
    scenario varchar(64) NOT NULL,
    unavailable_site_code varchar(64) NOT NULL,
    recovery_site_code varchar(64) NOT NULL,
    status varchar(16) NOT NULL,
    replication_lag_seconds integer NOT NULL,
    backup_age_seconds integer NOT NULL,
    measured_rto_seconds integer NOT NULL,
    restore_verified boolean NOT NULL,
    recovery_available boolean NOT NULL,
    vip_reachable boolean NOT NULL,
    operator_confirmed boolean NOT NULL,
    executed_by varchar(128) NOT NULL,
    executed_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, plan_id)
        REFERENCES multisite_dr_plans (tenant_id, id) ON DELETE RESTRICT,
    CHECK (scenario = 'primary-site-loss'),
    CHECK (status IN ('passed', 'failed')),
    CHECK (replication_lag_seconds >= 0),
    CHECK (backup_age_seconds >= 0),
    CHECK (measured_rto_seconds >= 0),
    CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS multisite_dr_drills_p0
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS multisite_dr_drills_p1
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS multisite_dr_drills_p2
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS multisite_dr_drills_p3
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS multisite_dr_drills_p4
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS multisite_dr_drills_p5
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS multisite_dr_drills_p6
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS multisite_dr_drills_p7
    PARTITION OF multisite_dr_drills FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_multisite_dr_drills_plan_time
    ON multisite_dr_drills (tenant_id, plan_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_multisite_dr_drills_status_time
    ON multisite_dr_drills (tenant_id, status, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_multisite_dr_drills_payload_gin
    ON multisite_dr_drills USING gin (payload);
CREATE INDEX IF NOT EXISTS idx_audit_events_multisite_dr
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('multisite_dr_plan', 'multisite_dr_drill');

COMMIT;
