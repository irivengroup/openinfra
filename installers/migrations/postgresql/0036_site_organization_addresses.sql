-- OpenInfra v0.29.80 - DCIM site and ITAM organization address completeness
BEGIN;

ALTER TABLE sites ADD COLUMN IF NOT EXISTS street_address text NOT NULL DEFAULT 'Adresse non renseignée';
ALTER TABLE sites ADD COLUMN IF NOT EXISTS postal_code text NOT NULL DEFAULT '00000';
ALTER TABLE sites ADD COLUMN IF NOT EXISTS contact_email text NOT NULL DEFAULT 'site@example.invalid';
ALTER TABLE sites ADD COLUMN IF NOT EXISTS phone text NOT NULL DEFAULT '+33000000000';

ALTER TABLE sites DROP CONSTRAINT IF EXISTS ck_sites_street_address;
ALTER TABLE sites ADD CONSTRAINT ck_sites_street_address CHECK (
    length(btrim(street_address)) BETWEEN 1 AND 512
);

ALTER TABLE sites DROP CONSTRAINT IF EXISTS ck_sites_postal_code;
ALTER TABLE sites ADD CONSTRAINT ck_sites_postal_code CHECK (
    length(btrim(postal_code)) BETWEEN 1 AND 32
);

ALTER TABLE sites DROP CONSTRAINT IF EXISTS ck_sites_contact_email;
ALTER TABLE sites ADD CONSTRAINT ck_sites_contact_email CHECK (
    contact_email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'
);

ALTER TABLE sites DROP CONSTRAINT IF EXISTS ck_sites_phone;
ALTER TABLE sites ADD CONSTRAINT ck_sites_phone CHECK (length(btrim(phone)) BETWEEN 1 AND 64);

ALTER TABLE itam_organizations ADD COLUMN IF NOT EXISTS postal_code text NOT NULL DEFAULT '00000';
ALTER TABLE itam_organizations ADD COLUMN IF NOT EXISTS phone text NOT NULL DEFAULT '+33000000000';

ALTER TABLE itam_organizations DROP CONSTRAINT IF EXISTS ck_itam_organizations_postal_code;
ALTER TABLE itam_organizations ADD CONSTRAINT ck_itam_organizations_postal_code CHECK (
    length(btrim(postal_code)) BETWEEN 1 AND 32
);

ALTER TABLE itam_organizations DROP CONSTRAINT IF EXISTS ck_itam_organizations_phone;
ALTER TABLE itam_organizations ADD CONSTRAINT ck_itam_organizations_phone CHECK (
    length(btrim(phone)) BETWEEN 1 AND 64
);

CREATE INDEX IF NOT EXISTS idx_sites_contact_catalog
    ON sites (tenant_id, country, city, postal_code, code)
    WHERE status = 'active';

ALTER TABLE itam_partners ADD COLUMN IF NOT EXISTS postal_code text NOT NULL DEFAULT '00000';

ALTER TABLE itam_partners DROP CONSTRAINT IF EXISTS ck_itam_partners_postal_code;
ALTER TABLE itam_partners ADD CONSTRAINT ck_itam_partners_postal_code CHECK (
    length(btrim(postal_code)) BETWEEN 1 AND 32
);

CREATE INDEX IF NOT EXISTS idx_itam_organizations_contact_catalog
    ON itam_organizations (country_code, city, postal_code, organization_id)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_itam_partners_contact_catalog
    ON itam_partners (organization_id, country_code, city, postal_code, partner_id)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_audit_events_site_organization_address
    ON audit_events (tenant_id, target_type, created_at DESC)
    WHERE target_type IN ('site', 'itam_organization', 'itam_partner');

COMMIT;
