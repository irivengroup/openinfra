-- OpenInfra v0.29.43 - ITAM asset support profiles.
-- Non-destructive foundation for mandatory manufacturer warranty/support and separated
-- third-party support contracts. The table is partitioned by tenant for large inventories.

CREATE TABLE IF NOT EXISTS asset_support_profiles (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_tag text NOT NULL,
    manufacturer_warranty jsonb NOT NULL,
    third_party_contracts jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, asset_tag),
    CONSTRAINT asset_support_profiles_asset_tag_check CHECK (asset_tag ~ '^[A-Z0-9][A-Z0-9_.:-]{0,63}$'),
    CONSTRAINT asset_support_profiles_manufacturer_warranty_object CHECK (
        jsonb_typeof(manufacturer_warranty) = 'object'
        AND manufacturer_warranty ? 'manufacturer'
        AND manufacturer_warranty ? 'warranty_reference'
        AND manufacturer_warranty ? 'warranty_start'
        AND manufacturer_warranty ? 'warranty_end'
        AND manufacturer_warranty ? 'support_reference'
        AND manufacturer_warranty ? 'support_contact'
    ),
    CONSTRAINT asset_support_profiles_third_party_array CHECK (
        jsonb_typeof(third_party_contracts) = 'array'
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS asset_support_profiles_p00 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p01 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p02 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p03 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p04 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p05 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p06 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p07 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p08 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p09 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p10 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p11 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p12 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p13 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p14 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS asset_support_profiles_p15 PARTITION OF asset_support_profiles
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_asset_support_profiles_warranty_end
    ON asset_support_profiles (tenant_id, ((manufacturer_warranty->>'warranty_end')));
CREATE INDEX IF NOT EXISTS idx_asset_support_profiles_third_party_gin
    ON asset_support_profiles USING gin (third_party_contracts);
CREATE INDEX IF NOT EXISTS idx_audit_events_itam_support_profiles
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'asset_support_profile';
