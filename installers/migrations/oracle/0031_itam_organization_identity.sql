-- Generated deterministically from installers/migrations/postgresql/0031_itam_organization_identity.sql.
-- Source SHA-256: f8607306a46ec4ca949fefc4ac77953b972409f1c74ae43361aca97bb8c501ab
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE itam_organizations (
    organization_id VARCHAR2(128 CHAR) NOT NULL,
    legal_name VARCHAR2(255 CHAR) NOT NULL,
    display_name VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL,
    registration_number VARCHAR2(255 CHAR) NOT NULL,
    tax_identifier VARCHAR2(255 CHAR) NOT NULL,
    country_code CHAR(2 CHAR) NOT NULL,
    city VARCHAR2(255 CHAR) NOT NULL,
    address VARCHAR2(255 CHAR) NOT NULL,
    contact_email VARCHAR2(255 CHAR) NOT NULL,
    support_contact VARCHAR2(255 CHAR) NOT NULL,
    description VARCHAR2(1000 CHAR),
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (organization_id),
    CONSTRAINT itam_organizations_id_check CHECK (REGEXP_LIKE(organization_id, '^[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]$')),
    CONSTRAINT itam_organizations_legal_name_check CHECK (length(TRIM(legal_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_organizations_display_name_check CHECK (length(TRIM(display_name)) BETWEEN 1 AND 255),
    CONSTRAINT itam_organizations_status_check CHECK (status IN ('active', 'suspended', 'retired')),
    CONSTRAINT itam_organizations_country_check CHECK (REGEXP_LIKE(country_code, '^[A-Z]{2}$')),
    CONSTRAINT itam_organizations_contact_email_check CHECK (REGEXP_LIKE(contact_email, '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')),
    CONSTRAINT itam_organizations_description_check CHECK (description IS NULL OR length(description) <= 1024)
)
PARTITION BY HASH (organization_id) PARTITIONS 16;

CREATE INDEX idx_itam_organizations_status_name
    ON itam_organizations (status, display_name, organization_id);

MERGE INTO itam_organizations target
USING (SELECT 'default' AS organization_id, 'Default Organization' AS legal_name, 'Default' AS display_name, 'active' AS status, 'N/A' AS registration_number, 'N/A' AS tax_identifier, 'FR' AS country_code, 'Non renseigné' AS city, 'Non renseigné' AS address, 'contact@example.invalid' AS contact_email, 'support@example.invalid' AS support_contact, 'Compatibility organization for single-tenant installations.' AS description, 'system' AS created_by, SYSTIMESTAMP AS created_at, 'system' AS updated_by, SYSTIMESTAMP AS updated_at FROM dual) source
ON (target.organization_id = source.organization_id)
WHEN NOT MATCHED THEN
    INSERT (organization_id, legal_name, display_name, status, registration_number, tax_identifier, country_code, city, address, contact_email, support_contact, description, created_by, created_at, updated_by, updated_at) VALUES (source.organization_id, source.legal_name, source.display_name, source.status, source.registration_number, source.tax_identifier, source.country_code, source.city, source.address, source.contact_email, source.support_contact, source.description, source.created_by, source.created_at, source.updated_by, source.updated_at);

ALTER TABLE itam_tenants ADD (organization_id VARCHAR2(128 CHAR));

UPDATE itam_tenants
SET organization_id = 'default'
WHERE organization_id IS NULL OR TRIM(organization_id) IS NULL;

ALTER TABLE itam_tenants MODIFY (organization_id NOT NULL);

ALTER TABLE itam_tenants ADD CONSTRAINT itam_tenants_organization_fk FOREIGN KEY (organization_id) REFERENCES itam_organizations(organization_id);

CREATE INDEX idx_itam_tenants_organization_status
    ON itam_tenants (organization_id, status, name, tenant_id);

CREATE INDEX idx_audit_events_itam_organization
    ON audit_events (tenant_id, created_at DESC);
