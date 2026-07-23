BEGIN;

CREATE TABLE IF NOT EXISTS itam_partners (
    organization_id text NOT NULL,
    partner_id text NOT NULL,
    kind text NOT NULL,
    legal_name text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL DEFAULT 'active',
    registration_number text NOT NULL,
    tax_identifier text NOT NULL,
    country_code char(2) NOT NULL,
    city text NOT NULL,
    address text NOT NULL,
    contact_email text NOT NULL,
    phone text NOT NULL,
    support_contact text NOT NULL,
    website text,
    description text,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (organization_id, partner_id),
    CONSTRAINT itam_partners_organization_fk FOREIGN KEY (organization_id) REFERENCES itam_organizations(organization_id),
    CONSTRAINT itam_partners_id_check CHECK (partner_id ~ '^[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]$'),
    CONSTRAINT itam_partners_kind_check CHECK (kind IN ('manufacturer', 'software_publisher', 'third_party_support')),
    CONSTRAINT itam_partners_status_check CHECK (status IN ('active', 'suspended', 'retired')),
    CONSTRAINT itam_partners_legal_name_check CHECK (length(btrim(legal_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_partners_display_name_check CHECK (length(btrim(display_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_partners_country_check CHECK (country_code ~ '^[A-Z]{2}$'),
    CONSTRAINT itam_partners_contact_email_check CHECK (contact_email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
    CONSTRAINT itam_partners_phone_check CHECK (phone ~ '^\+?[0-9][0-9 .()/-]{5,31}$'),
    CONSTRAINT itam_partners_website_check CHECK (website IS NULL OR website ~ '^https?://[^[:space:]]+$'),
    CONSTRAINT itam_partners_description_check CHECK (description IS NULL OR length(description) <= 1024)
) PARTITION BY HASH (organization_id);

CREATE TABLE IF NOT EXISTS itam_partners_p00 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS itam_partners_p01 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS itam_partners_p02 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS itam_partners_p03 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS itam_partners_p04 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS itam_partners_p05 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS itam_partners_p06 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS itam_partners_p07 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS itam_partners_p08 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS itam_partners_p09 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS itam_partners_p10 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS itam_partners_p11 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS itam_partners_p12 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS itam_partners_p13 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS itam_partners_p14 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS itam_partners_p15 PARTITION OF itam_partners FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_itam_partners_org_kind_status
    ON itam_partners (organization_id, kind, status, display_name, partner_id);
CREATE INDEX IF NOT EXISTS idx_itam_partners_status_name
    ON itam_partners (status, display_name, partner_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_itam_partner
    ON audit_events (tenant_id, created_at DESC)
    WHERE target_type = 'itam_partner';

ALTER TABLE software_license_entitlements
    ADD COLUMN IF NOT EXISTS vendor_partner_id text;

CREATE INDEX IF NOT EXISTS idx_software_license_entitlements_vendor_partner
    ON software_license_entitlements (tenant_id, vendor_partner_id, status);

COMMIT;
