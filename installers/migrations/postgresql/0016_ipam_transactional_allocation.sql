BEGIN;

CREATE INDEX IF NOT EXISTS idx_ip_reservations_transactional_scan
    ON ip_reservations (tenant_id, vrf_name, prefix_cidr, address, idempotency_key);

CREATE INDEX IF NOT EXISTS idx_ip_address_records_transactional_scan
    ON ip_address_records (tenant_id, vrf_name, prefix_cidr, address, status);

CREATE INDEX IF NOT EXISTS idx_ip_ranges_transactional_pool_scan
    ON ip_ranges (tenant_id, vrf_name, prefix_cidr, purpose, start_address, end_address);

COMMENT ON INDEX idx_ip_reservations_transactional_scan IS
    'Supports EPIC-0502 idempotent next-available allocation scans and collision checks.';
COMMENT ON INDEX idx_ip_address_records_transactional_scan IS
    'Ensures registered IP addresses are considered occupied by the transaction allocator.';
COMMENT ON INDEX idx_ip_ranges_transactional_pool_scan IS
    'Supports allocation pools, reservation windows and exclusion windows during IP selection.';

CREATE INDEX IF NOT EXISTS idx_ipam_transactional_allocation_audit
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE action = 'ipam.address.allocated';

COMMENT ON INDEX idx_ipam_transactional_allocation_audit IS
    'Supports EPIC-0502 audit lookups for transactional IP allocation events.';

COMMIT;
