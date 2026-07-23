-- OpenInfra v0.29.51 - ITAM software license entitlements and compliance.
-- Partitioned by tenant for large software inventories and non-destructive toward existing support profiles.

CREATE TABLE IF NOT EXISTS software_license_entitlements (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_name text NOT NULL,
    vendor text NOT NULL,
    version text NULL,
    license_reference text NOT NULL,
    contract_reference text NULL,
    metric text NOT NULL,
    purchased_quantity bigint NOT NULL,
    assigned_quantity bigint NOT NULL DEFAULT 0,
    entitlement_start date NOT NULL,
    entitlement_end date NOT NULL,
    status text NOT NULL DEFAULT 'active',
    owner text NULL,
    notes text NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, license_reference),
    CONSTRAINT software_license_reference_check CHECK (license_reference ~ '^[A-Z0-9][A-Z0-9_.:-]{0,63}$'),
    CONSTRAINT software_license_contract_reference_check CHECK (
        contract_reference IS NULL OR contract_reference ~ '^[A-Z0-9][A-Z0-9_.:/#-]{0,127}$'
    ),
    CONSTRAINT software_license_metric_check CHECK (
        metric IN ('device', 'user', 'core', 'socket', 'instance', 'subscription')
    ),
    CONSTRAINT software_license_status_check CHECK (
        status IN ('active', 'expired', 'planned', 'terminated')
    ),
    CONSTRAINT software_license_quantities_check CHECK (
        purchased_quantity > 0 AND assigned_quantity >= 0
    ),
    CONSTRAINT software_license_dates_check CHECK (entitlement_end >= entitlement_start)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS software_license_entitlements_p00 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p01 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p02 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p03 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p04 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p05 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p06 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p07 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p08 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p09 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p10 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p11 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p12 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p13 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p14 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS software_license_entitlements_p15 PARTITION OF software_license_entitlements
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_software_license_entitlements_vendor_product
    ON software_license_entitlements (tenant_id, vendor, product_name);
CREATE INDEX IF NOT EXISTS idx_software_license_entitlements_end
    ON software_license_entitlements (tenant_id, entitlement_end, status);
CREATE INDEX IF NOT EXISTS idx_software_license_entitlements_compliance
    ON software_license_entitlements (tenant_id, status, purchased_quantity, assigned_quantity);
CREATE INDEX IF NOT EXISTS idx_audit_events_itam_software_license
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'software_license';
