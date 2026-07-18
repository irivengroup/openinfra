-- Generated deterministically from installers/migrations/postgresql/0028_itam_software_license_entitlements.sql.
-- Source SHA-256: d9a9595fc814e9677a52b6bfa9eff6e47f48542f03c45c4aebe1145e61db55b3
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE software_license_entitlements (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_name VARCHAR2(255 CHAR) NOT NULL,
    vendor VARCHAR2(255 CHAR) NOT NULL,
    version VARCHAR2(255 CHAR) NULL,
    license_reference VARCHAR2(255 CHAR) NOT NULL,
    contract_reference VARCHAR2(255 CHAR) NULL,
    metric VARCHAR2(255 CHAR) NOT NULL,
    purchased_quantity NUMBER(19) NOT NULL,
    assigned_quantity NUMBER(19) DEFAULT 0 NOT NULL,
    entitlement_start date NOT NULL,
    entitlement_end date NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL,
    owner VARCHAR2(255 CHAR) NULL,
    notes CLOB NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, license_reference),
    CONSTRAINT software_license_reference_check CHECK (REGEXP_LIKE(license_reference, '^[A-Z0-9][A-Z0-9_.:-]{0,63}$')),
    CONSTRAINT software_license_contract_reference_check CHECK (
        contract_reference IS NULL OR REGEXP_LIKE(contract_reference, '^[A-Z0-9][A-Z0-9_.:/#-]{0,127}$')
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
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_software_license_entitlements_vendor_product
    ON software_license_entitlements (tenant_id, vendor, product_name);

CREATE INDEX idx_software_license_entitlements_end
    ON software_license_entitlements (tenant_id, entitlement_end, status);

CREATE INDEX idx_software_license_entitlements_compliance
    ON software_license_entitlements (tenant_id, status, purchased_quantity, assigned_quantity);

CREATE INDEX idx_audit_events_itam_software_license
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
