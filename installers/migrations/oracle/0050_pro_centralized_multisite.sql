-- Generated deterministically from installers/migrations/postgresql/0050_pro_centralized_multisite.sql.
-- Source SHA-256: 99c3f731422796739251daff28a2e159b150d28bdc8bb9fb3ff17b1b1e68207d
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE multisite_site_access_grants (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(64 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    subject VARCHAR2(128 CHAR) NOT NULL,
    site_code VARCHAR2(64 CHAR) NOT NULL,
    access_level VARCHAR2(16 CHAR) NOT NULL CHECK (access_level IN ('viewer', 'operator', 'admin')),
    active NUMBER(1) DEFAULT 1 NOT NULL,
    granted_by VARCHAR2(128 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, subject, site_code),
    CHECK ((active AND revoked_at IS NULL) OR (NOT active AND revoked_at IS NOT NULL)),
    CONSTRAINT ck_multisite_site_access_grants_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_multisite_grants_subject_active
    ON multisite_site_access_grants (tenant_id, subject, active, site_code);

CREATE INDEX idx_multisite_grants_site_active
    ON multisite_site_access_grants (tenant_id, site_code, active, subject);

CREATE TABLE multisite_reports (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(64 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    requested_subject VARCHAR2(128 CHAR) NOT NULL,
    generated_by VARCHAR2(128 CHAR) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT ck_multisite_reports_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_multisite_reports_subject_generated
    ON multisite_reports (tenant_id, requested_subject, generated_at DESC, id DESC);

CREATE INDEX idx_audit_events_multisite
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
