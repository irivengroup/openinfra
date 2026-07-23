-- OpenInfra migration 0011: DCIM field operations QR scans and locator sheets
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs (
    id uuid NOT NULL,
    tenant_id text NOT NULL,
    asset_tag text NOT NULL,
    actor text NOT NULL,
    payload text NOT NULL,
    verified boolean NOT NULL,
    scanned_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p00 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p01 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p02 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p03 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p04 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p05 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p06 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p07 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p08 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p09 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p10 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p11 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p12 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p13 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p14 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS dcim_field_scan_proofs_p15 PARTITION OF dcim_field_scan_proofs
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_dcim_field_scan_asset
    ON dcim_field_scan_proofs (tenant_id, asset_tag, scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_dcim_field_scan_verified
    ON dcim_field_scan_proofs (tenant_id, verified, scanned_at DESC);

-- Audit linkage for field operations is stored in audit_events via dcim.qr-scan.* and dcim.locator-sheet.* actions.
CREATE INDEX IF NOT EXISTS idx_audit_events_dcim_field_operations
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action LIKE 'dcim.qr-scan.%' OR action LIKE 'dcim.locator-sheet.%';
