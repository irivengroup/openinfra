-- Generated deterministically from installers/migrations/postgresql/0027_itam_asset_support_profiles.sql.
-- Source SHA-256: 5d77fdfe80d4790e31785c0117ff861c4cc408af8de55f4312fb795fc5b17028
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE asset_support_profiles (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_tag VARCHAR2(255 CHAR) NOT NULL,
    manufacturer_warranty CLOB NOT NULL,
    third_party_contracts CLOB DEFAULT '[]' NOT NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, asset_tag),
    CONSTRAINT asset_support_profiles_asset_tag_check CHECK (REGEXP_LIKE(asset_tag, '^[A-Z0-9][A-Z0-9_.:-]{0,63}$')),
    CONSTRAINT asset_support_profiles_manufacturer_warranty_object CHECK (
        JSON_EXISTS(manufacturer_warranty, '$?(@.type() == \"object\")')
        AND manufacturer_warranty ? 'manufacturer'
        AND manufacturer_warranty ? 'warranty_reference'
        AND manufacturer_warranty ? 'warranty_start'
        AND manufacturer_warranty ? 'warranty_end'
        AND manufacturer_warranty ? 'support_reference'
        AND manufacturer_warranty ? 'support_contact'
    ),
    CONSTRAINT asset_support_profiles_third_party_array CHECK (
        JSON_EXISTS(third_party_contracts, '$?(@.type() == \"array\")')
    ),
    CONSTRAINT ck_asset_support_profiles_manufacturer_warranty_json CHECK (manufacturer_warranty IS JSON),
    CONSTRAINT ck_asset_support_profiles_third_party_contracts_json CHECK (third_party_contracts IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_asset_support_profiles_warranty_end
    ON asset_support_profiles (tenant_id, (JSON_VALUE(manufacturer_warranty, '$.warranty_end' RETURNING VARCHAR2(64 CHAR))));

CREATE INDEX idx_audit_events_itam_support_profiles
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
