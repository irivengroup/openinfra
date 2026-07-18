-- Generated deterministically from installers/migrations/postgresql/0022_legacy_migration_framework.sql.
-- Source SHA-256: 2c83a2a1c3b6053e5e0bc271f0b58e37312192625f625e8d9de9a074c1ef73f8
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE migration_plan_reports (
    id VARCHAR2(255 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source VARCHAR2(255 CHAR) NOT NULL,
    import_format VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    template CLOB NOT NULL,
    total_rows NUMBER(19) DEFAULT 0 NOT NULL,
    valid_rows NUMBER(19) DEFAULT 0 NOT NULL,
    invalid_rows NUMBER(19) DEFAULT 0 NOT NULL,
    create_count NUMBER(19) DEFAULT 0 NOT NULL,
    update_count NUMBER(19) DEFAULT 0 NOT NULL,
    gaps CLOB NOT NULL,
    import_report CLOB NOT NULL,
    resume_strategy VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT migration_plan_reports_source_check CHECK (
        source IN ('device42', 'netbox', 'nautobot', 'glpi', 'csv')
    ),
    CONSTRAINT migration_plan_reports_format_check CHECK (import_format IN ('csv', 'json', 'xlsx')),
    CONSTRAINT migration_plan_reports_status_check CHECK (
        status IN ('queued', 'validated', 'applied', 'failed')
    ),
    CONSTRAINT migration_plan_reports_total_rows_check CHECK (total_rows >= 0),
    CONSTRAINT migration_plan_reports_valid_rows_check CHECK (valid_rows >= 0),
    CONSTRAINT migration_plan_reports_invalid_rows_check CHECK (invalid_rows >= 0),
    CONSTRAINT migration_plan_reports_create_count_check CHECK (create_count >= 0),
    CONSTRAINT migration_plan_reports_update_count_check CHECK (update_count >= 0),
    CONSTRAINT migration_plan_reports_row_count_check CHECK (valid_rows + invalid_rows = total_rows),
    CONSTRAINT migration_plan_reports_impact_count_check CHECK (create_count + update_count <= valid_rows),
    CONSTRAINT ck_migration_plan_reports_template_json CHECK (template IS JSON),
    CONSTRAINT ck_migration_plan_reports_gaps_json CHECK (gaps IS JSON),
    CONSTRAINT ck_migration_plan_reports_import_report_json CHECK (import_report IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 8;

CREATE INDEX idx_migration_plan_reports_source_status
    ON migration_plan_reports (tenant_id, source, status, created_at DESC, id);

CREATE INDEX idx_audit_events_migration_plans
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
