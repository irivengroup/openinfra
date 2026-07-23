-- Generated deterministically from installers/migrations/postgresql/0011_dcim_field_operations.sql.
-- Source SHA-256: e1142d32857b451849bc8f2fe039cecfa520d0f21af42010ad4a1073de98357b
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE dcim_field_scan_proofs (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    asset_tag VARCHAR2(255 CHAR) NOT NULL,
    actor VARCHAR2(255 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    verified NUMBER(1) NOT NULL,
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_dcim_field_scan_asset
    ON dcim_field_scan_proofs (tenant_id, asset_tag, scanned_at DESC);

CREATE INDEX idx_dcim_field_scan_verified
    ON dcim_field_scan_proofs (tenant_id, verified, scanned_at DESC);

CREATE INDEX idx_audit_events_dcim_field_operations
    ON audit_events (tenant_id, action, created_at DESC);
