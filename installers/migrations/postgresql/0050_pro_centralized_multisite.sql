-- OpenInfra 0.29.102 / EPIC-1701: centralized Pro multisite with site-scoped RBAC.
BEGIN;

CREATE TABLE IF NOT EXISTS multisite_site_access_grants (
    id uuid NOT NULL,
    tenant_id varchar(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    subject varchar(128) NOT NULL,
    site_code varchar(64) NOT NULL,
    access_level varchar(16) NOT NULL CHECK (access_level IN ('viewer', 'operator', 'admin')),
    active boolean NOT NULL DEFAULT TRUE,
    granted_by varchar(128) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    revoked_at timestamptz NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, subject, site_code),
    CHECK ((active AND revoked_at IS NULL) OR (NOT active AND revoked_at IS NOT NULL))
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p0
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p1
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p2
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p3
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p4
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p5
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p6
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS multisite_site_access_grants_p7
    PARTITION OF multisite_site_access_grants FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_multisite_grants_subject_active
    ON multisite_site_access_grants (tenant_id, subject, active, site_code);
CREATE INDEX IF NOT EXISTS idx_multisite_grants_site_active
    ON multisite_site_access_grants (tenant_id, site_code, active, subject);

CREATE TABLE IF NOT EXISTS multisite_reports (
    id uuid NOT NULL,
    tenant_id varchar(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    requested_subject varchar(128) NOT NULL,
    generated_by varchar(128) NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS multisite_reports_p0
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS multisite_reports_p1
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS multisite_reports_p2
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS multisite_reports_p3
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS multisite_reports_p4
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS multisite_reports_p5
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS multisite_reports_p6
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS multisite_reports_p7
    PARTITION OF multisite_reports FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX IF NOT EXISTS idx_multisite_reports_subject_generated
    ON multisite_reports (tenant_id, requested_subject, generated_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_multisite
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('site_access_grant', 'multisite_report');

COMMIT;
