-- Generated deterministically from installers/migrations/postgresql/0016_ipam_transactional_allocation.sql.
-- Source SHA-256: 761347418e5855faf9b7988fd369b10c8f12255284fcfa8568b4deef43483c83
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE INDEX idx_ip_reservations_transactional_scan
    ON ip_reservations (tenant_id, vrf_name, prefix_cidr, address, idempotency_key);

CREATE INDEX idx_ip_address_records_transactional_scan
    ON ip_address_records (tenant_id, vrf_name, prefix_cidr, address, status);

CREATE INDEX idx_ip_ranges_transactional_pool_scan
    ON ip_ranges (tenant_id, vrf_name, prefix_cidr, purpose, start_address, end_address);

CREATE INDEX idx_ipam_transactional_allocation_audit
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
