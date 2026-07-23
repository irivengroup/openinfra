BEGIN;

CREATE TABLE IF NOT EXISTS itam_organizations (
    organization_id text NOT NULL,
    legal_name text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL DEFAULT 'active',
    registration_number text NOT NULL,
    tax_identifier text NOT NULL,
    country_code char(2) NOT NULL,
    city text NOT NULL,
    address text NOT NULL,
    contact_email text NOT NULL,
    support_contact text NOT NULL,
    description text,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (organization_id),
    CONSTRAINT itam_organizations_id_check CHECK (organization_id ~ '^[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]$'),
    CONSTRAINT itam_organizations_legal_name_check CHECK (length(btrim(legal_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_organizations_display_name_check CHECK (length(btrim(display_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_organizations_status_check CHECK (status IN ('active', 'suspended', 'retired')),
    CONSTRAINT itam_organizations_country_check CHECK (country_code ~ '^[A-Z]{2}$'),
    CONSTRAINT itam_organizations_contact_email_check CHECK (contact_email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
    CONSTRAINT itam_organizations_description_check CHECK (description IS NULL OR length(description) <= 1024)
) PARTITION BY HASH (organization_id);

CREATE TABLE IF NOT EXISTS itam_organizations_p00 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS itam_organizations_p01 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS itam_organizations_p02 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS itam_organizations_p03 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS itam_organizations_p04 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS itam_organizations_p05 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS itam_organizations_p06 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS itam_organizations_p07 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS itam_organizations_p08 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS itam_organizations_p09 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS itam_organizations_p10 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS itam_organizations_p11 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS itam_organizations_p12 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS itam_organizations_p13 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS itam_organizations_p14 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS itam_organizations_p15 PARTITION OF itam_organizations FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_itam_organizations_status_name
    ON itam_organizations (status, display_name, organization_id);

INSERT INTO itam_organizations (
    organization_id, legal_name, display_name, status,
    registration_number, tax_identifier, country_code, city, address,
    contact_email, support_contact, description,
    created_by, created_at, updated_by, updated_at
) VALUES (
    'default', 'Default Organization', 'Default', 'active',
    'N/A', 'N/A', 'FR', 'Non renseigné', 'Non renseigné',
    'contact@example.invalid', 'support@example.invalid',
    'Compatibility organization for single-tenant installations.',
    'system', now(), 'system', now()
) ON CONFLICT (organization_id) DO NOTHING;

ALTER TABLE itam_tenants
    ADD COLUMN IF NOT EXISTS organization_id text;

UPDATE itam_tenants
SET organization_id = 'default'
WHERE organization_id IS NULL OR btrim(organization_id) = '';

ALTER TABLE itam_tenants
    ALTER COLUMN organization_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'itam_tenants_organization_fk'
    ) THEN
        ALTER TABLE itam_tenants
            ADD CONSTRAINT itam_tenants_organization_fk
            FOREIGN KEY (organization_id) REFERENCES itam_organizations(organization_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_itam_tenants_organization_status
    ON itam_tenants (organization_id, status, name, tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_itam_organization
    ON audit_events (tenant_id, created_at DESC)
    WHERE target_type = 'itam_organization';

COMMIT;
