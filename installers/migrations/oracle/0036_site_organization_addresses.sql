-- Generated deterministically from installers/migrations/postgresql/0036_site_organization_addresses.sql.
-- Source SHA-256: bffc12d7de9df21c5fbe55e76b229211e50678130396b757ba5b9e326abbedb4
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

ALTER TABLE sites ADD (street_address VARCHAR2(255 CHAR) DEFAULT 'Adresse non renseignée' NOT NULL);

ALTER TABLE sites ADD (postal_code VARCHAR2(128 CHAR) DEFAULT '00000' NOT NULL);

ALTER TABLE sites ADD (contact_email VARCHAR2(255 CHAR) DEFAULT 'site@example.invalid' NOT NULL);

ALTER TABLE sites ADD (phone VARCHAR2(255 CHAR) DEFAULT '+33000000000' NOT NULL);

ALTER TABLE sites DROP CONSTRAINT ck_sites_street_address;

ALTER TABLE sites ADD CONSTRAINT ck_sites_street_address CHECK (
    length(TRIM(street_address)) BETWEEN 1 AND 512
);

ALTER TABLE sites DROP CONSTRAINT ck_sites_postal_code;

ALTER TABLE sites ADD CONSTRAINT ck_sites_postal_code CHECK (
    length(TRIM(postal_code)) BETWEEN 1 AND 32
);

ALTER TABLE sites DROP CONSTRAINT ck_sites_contact_email;

ALTER TABLE sites ADD CONSTRAINT ck_sites_contact_email CHECK (
    REGEXP_LIKE(contact_email, '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')
);

ALTER TABLE sites DROP CONSTRAINT ck_sites_phone;

ALTER TABLE sites ADD CONSTRAINT ck_sites_phone CHECK (length(TRIM(phone)) BETWEEN 1 AND 64);

ALTER TABLE itam_organizations ADD (postal_code VARCHAR2(128 CHAR) DEFAULT '00000' NOT NULL);

ALTER TABLE itam_organizations ADD (phone VARCHAR2(255 CHAR) DEFAULT '+33000000000' NOT NULL);

ALTER TABLE itam_organizations DROP CONSTRAINT ck_itam_organizations_postal_code;

ALTER TABLE itam_organizations ADD CONSTRAINT ck_itam_organizations_postal_code CHECK (
    length(TRIM(postal_code)) BETWEEN 1 AND 32
);

ALTER TABLE itam_organizations DROP CONSTRAINT ck_itam_organizations_phone;

ALTER TABLE itam_organizations ADD CONSTRAINT ck_itam_organizations_phone CHECK (
    length(TRIM(phone)) BETWEEN 1 AND 64
);

CREATE INDEX idx_sites_contact_catalog
    ON sites (tenant_id, country, city, postal_code, code);

ALTER TABLE itam_partners ADD (postal_code VARCHAR2(128 CHAR) DEFAULT '00000' NOT NULL);

ALTER TABLE itam_partners DROP CONSTRAINT ck_itam_partners_postal_code;

ALTER TABLE itam_partners ADD CONSTRAINT ck_itam_partners_postal_code CHECK (
    length(TRIM(postal_code)) BETWEEN 1 AND 32
);

CREATE INDEX idx_itam_organizations_contact_catalog
    ON itam_organizations (country_code, city, postal_code, organization_id);

CREATE INDEX idx_itam_partners_contact_catalog
    ON itam_partners (organization_id, country_code, city, postal_code, partner_id);

CREATE INDEX idx_audit_events_site_organization_address
    ON audit_events (tenant_id, target_type, created_at DESC);
