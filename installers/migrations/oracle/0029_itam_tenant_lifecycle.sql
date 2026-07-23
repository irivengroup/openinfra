-- Generated deterministically from installers/migrations/postgresql/0029_itam_tenant_lifecycle.sql.
-- Source SHA-256: 70807f05ee11a1d0c2ebed0144f6e7e55171796cd5d0feed9b93c97c243c644f
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE itam_tenants (
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL,
    is_default NUMBER(1) DEFAULT 0 NOT NULL,
    description VARCHAR2(1000 CHAR),
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id),
    CONSTRAINT itam_tenants_id_check CHECK (REGEXP_LIKE(tenant_id, '^[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]$')),
    CONSTRAINT itam_tenants_name_check CHECK (length(TRIM(name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_tenants_status_check CHECK (status IN ('active', 'suspended', 'retired')),
    CONSTRAINT itam_tenants_description_check CHECK (description IS NULL OR length(description) <= 1024)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_itam_tenants_single_default
    ON itam_tenants (is_default);

CREATE INDEX idx_itam_tenants_status_name
    ON itam_tenants (status, name, tenant_id);

CREATE INDEX idx_audit_events_itam_tenant
    ON audit_events (tenant_id, created_at DESC);

MERGE INTO tenants target
USING (SELECT 'default' AS id, 'Default' AS display_name FROM dual) source
ON (target.id = source.id)
WHEN MATCHED THEN UPDATE SET display_name = COALESCE(NULLIF(TRIM(target.display_name), ''), source.display_name)
WHEN NOT MATCHED THEN INSERT (id, display_name) VALUES (source.id, source.display_name);

MERGE INTO itam_tenants target
USING (SELECT 'default' AS tenant_id, 'Default' AS name, 'active' AS status, 1 AS is_default, 'Default ITAM tenant created for single-tenant installations.' AS description, 'system' AS created_by, SYSTIMESTAMP AS created_at, 'system' AS updated_by, SYSTIMESTAMP AS updated_at FROM dual) source
ON (target.tenant_id = source.tenant_id)
WHEN NOT MATCHED THEN
    INSERT (tenant_id, name, status, is_default, description, created_by, created_at, updated_by, updated_at) VALUES (source.tenant_id, source.name, source.status, source.is_default, source.description, source.created_by, source.created_at, source.updated_by, source.updated_at);
