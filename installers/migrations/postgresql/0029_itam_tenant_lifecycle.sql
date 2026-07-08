CREATE TABLE IF NOT EXISTS itam_tenants (
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name text NOT NULL,
    status text NOT NULL DEFAULT 'active',
    is_default boolean NOT NULL DEFAULT false,
    description text,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id),
    CONSTRAINT itam_tenants_id_check CHECK (tenant_id ~ '^[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]$'),
    CONSTRAINT itam_tenants_name_check CHECK (length(btrim(name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_tenants_status_check CHECK (status IN ('active', 'suspended', 'retired')),
    CONSTRAINT itam_tenants_description_check CHECK (description IS NULL OR length(description) <= 1024)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS itam_tenants_p00 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS itam_tenants_p01 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS itam_tenants_p02 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS itam_tenants_p03 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS itam_tenants_p04 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS itam_tenants_p05 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS itam_tenants_p06 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS itam_tenants_p07 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS itam_tenants_p08 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS itam_tenants_p09 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS itam_tenants_p10 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS itam_tenants_p11 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS itam_tenants_p12 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS itam_tenants_p13 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS itam_tenants_p14 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS itam_tenants_p15 PARTITION OF itam_tenants FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_itam_tenants_single_default
    ON itam_tenants (is_default)
    WHERE is_default = true AND status = 'active';
CREATE INDEX IF NOT EXISTS idx_itam_tenants_status_name
    ON itam_tenants (status, name, tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_itam_tenant
    ON audit_events (tenant_id, created_at DESC)
    WHERE target_type = 'itam_tenant';

INSERT INTO tenants (id) VALUES ('default') ON CONFLICT (id) DO NOTHING;
INSERT INTO itam_tenants (
    tenant_id, name, status, is_default, description,
    created_by, created_at, updated_by, updated_at
) VALUES (
    'default', 'Default', 'active', true,
    'Default ITAM tenant created for single-tenant installations.',
    'system', now(), 'system', now()
) ON CONFLICT (tenant_id) DO NOTHING;
