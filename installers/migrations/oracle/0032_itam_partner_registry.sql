-- Generated deterministically from installers/migrations/postgresql/0032_itam_partner_registry.sql.
-- Source SHA-256: ccdcc29a6855d1fb298ce6cbb11c3d03cb0fd7a9b78bfa397bc07e8172ee0e0f
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE itam_partners (
    organization_id VARCHAR2(128 CHAR) NOT NULL,
    partner_id VARCHAR2(128 CHAR) NOT NULL,
    kind VARCHAR2(255 CHAR) NOT NULL,
    legal_name VARCHAR2(255 CHAR) NOT NULL,
    display_name VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL,
    registration_number VARCHAR2(255 CHAR) NOT NULL,
    tax_identifier VARCHAR2(255 CHAR) NOT NULL,
    country_code CHAR(2 CHAR) NOT NULL,
    city VARCHAR2(255 CHAR) NOT NULL,
    address VARCHAR2(255 CHAR) NOT NULL,
    contact_email VARCHAR2(255 CHAR) NOT NULL,
    phone VARCHAR2(255 CHAR) NOT NULL,
    support_contact VARCHAR2(255 CHAR) NOT NULL,
    website VARCHAR2(255 CHAR),
    description VARCHAR2(1000 CHAR),
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (organization_id, partner_id),
    CONSTRAINT itam_partners_organization_fk FOREIGN KEY (organization_id) REFERENCES itam_organizations(organization_id),
    CONSTRAINT itam_partners_id_check CHECK (REGEXP_LIKE(partner_id, '^[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]$')),
    CONSTRAINT itam_partners_kind_check CHECK (kind IN ('manufacturer', 'software_publisher', 'third_party_support')),
    CONSTRAINT itam_partners_status_check CHECK (status IN ('active', 'suspended', 'retired')),
    CONSTRAINT itam_partners_legal_name_check CHECK (length(TRIM(legal_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_partners_display_name_check CHECK (length(TRIM(display_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_partners_country_check CHECK (REGEXP_LIKE(country_code, '^[A-Z]{2}$')),
    CONSTRAINT itam_partners_contact_email_check CHECK (REGEXP_LIKE(contact_email, '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')),
    CONSTRAINT itam_partners_phone_check CHECK (REGEXP_LIKE(phone, '^\+?[0-9][0-9 .()/-]{5,31}$')),
    CONSTRAINT itam_partners_website_check CHECK (website IS NULL OR REGEXP_LIKE(website, '^https?://[^[:space:]]+$')),
    CONSTRAINT itam_partners_description_check CHECK (description IS NULL OR length(description) <= 1024)
)
PARTITION BY HASH (organization_id) PARTITIONS 16;

CREATE INDEX idx_itam_partners_org_kind_status
    ON itam_partners (organization_id, kind, status, display_name, partner_id);

CREATE INDEX idx_itam_partners_status_name
    ON itam_partners (status, display_name, partner_id);

CREATE INDEX idx_audit_events_itam_partner
    ON audit_events (tenant_id, created_at DESC);

ALTER TABLE software_license_entitlements ADD (vendor_partner_id VARCHAR2(128 CHAR));

CREATE INDEX idx_software_license_entitlements_vendor_partner
    ON software_license_entitlements (tenant_id, vendor_partner_id, status);
