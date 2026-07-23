-- OpenInfra v0.29.90 - P15 / EPIC-1503 certificate and PKI inventory

BEGIN;

CREATE TABLE IF NOT EXISTS certificate_inventory (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    fingerprint_sha256 char(64) NOT NULL,
    serial_number text NOT NULL,
    subject_dn text NOT NULL,
    issuer_dn text NOT NULL,
    common_name text NULL,
    san_dns jsonb NOT NULL DEFAULT '[]'::jsonb,
    san_ip jsonb NOT NULL DEFAULT '[]'::jsonb,
    san_email jsonb NOT NULL DEFAULT '[]'::jsonb,
    san_uri jsonb NOT NULL DEFAULT '[]'::jsonb,
    not_before timestamptz NOT NULL,
    not_after timestamptz NOT NULL,
    public_key_algorithm text NOT NULL,
    public_key_size integer NULL,
    signature_algorithm text NOT NULL,
    is_ca boolean NOT NULL DEFAULT false,
    chain_fingerprints jsonb NOT NULL DEFAULT '[]'::jsonb,
    owner text NOT NULL,
    environment text NOT NULL,
    source text NOT NULL,
    object_key text NULL,
    lifecycle text NOT NULL,
    version integer NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint_sha256),
    CONSTRAINT certificate_inventory_fingerprint_valid CHECK (
        fingerprint_sha256 ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT certificate_inventory_serial_valid CHECK (
        serial_number ~ '^[0-9A-F]{1,128}$'
    ),
    CONSTRAINT certificate_inventory_subject_valid CHECK (
        length(subject_dn) BETWEEN 1 AND 2048
    ),
    CONSTRAINT certificate_inventory_issuer_valid CHECK (
        length(issuer_dn) BETWEEN 1 AND 2048
    ),
    CONSTRAINT certificate_inventory_common_name_valid CHECK (
        common_name IS NULL OR length(common_name) BETWEEN 1 AND 255
    ),
    CONSTRAINT certificate_inventory_san_dns_array CHECK (jsonb_typeof(san_dns) = 'array'),
    CONSTRAINT certificate_inventory_san_ip_array CHECK (jsonb_typeof(san_ip) = 'array'),
    CONSTRAINT certificate_inventory_san_email_array CHECK (jsonb_typeof(san_email) = 'array'),
    CONSTRAINT certificate_inventory_san_uri_array CHECK (jsonb_typeof(san_uri) = 'array'),
    CONSTRAINT certificate_inventory_dates_ordered CHECK (not_after > not_before),
    CONSTRAINT certificate_inventory_public_key_size_valid CHECK (
        public_key_size IS NULL OR public_key_size BETWEEN 128 AND 65536
    ),
    CONSTRAINT certificate_inventory_chain_array CHECK (
        jsonb_typeof(chain_fingerprints) = 'array'
        AND jsonb_array_length(chain_fingerprints) <= 16
    ),
    CONSTRAINT certificate_inventory_owner_valid CHECK (
        length(trim(owner)) BETWEEN 2 AND 255
    ),
    CONSTRAINT certificate_inventory_environment_valid CHECK (
        environment ~ '^[a-z0-9][a-z0-9_.:+/-]{0,63}$'
    ),
    CONSTRAINT certificate_inventory_source_valid CHECK (
        source IN ('manual', 'discovery', 'import', 'acme', 'internal-pki', 'external-pki')
    ),
    CONSTRAINT certificate_inventory_object_key_valid CHECK (
        object_key IS NULL
        OR object_key ~ '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$'
    ),
    CONSTRAINT certificate_inventory_lifecycle_valid CHECK (
        lifecycle IN ('active', 'retired')
    ),
    CONSTRAINT certificate_inventory_version_valid CHECK (version >= 1),
    CONSTRAINT certificate_inventory_timestamps_ordered CHECK (updated_at >= created_at)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS certificate_inventory_p00 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS certificate_inventory_p01 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS certificate_inventory_p02 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS certificate_inventory_p03 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS certificate_inventory_p04 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS certificate_inventory_p05 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS certificate_inventory_p06 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS certificate_inventory_p07 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS certificate_inventory_p08 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS certificate_inventory_p09 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS certificate_inventory_p10 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS certificate_inventory_p11 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS certificate_inventory_p12 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS certificate_inventory_p13 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS certificate_inventory_p14 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS certificate_inventory_p15 PARTITION OF certificate_inventory
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_certificate_inventory_expiration
    ON certificate_inventory (tenant_id, lifecycle, not_after, fingerprint_sha256);
CREATE INDEX IF NOT EXISTS idx_certificate_inventory_owner
    ON certificate_inventory (tenant_id, owner, environment, lifecycle, not_after);
CREATE INDEX IF NOT EXISTS idx_certificate_inventory_object
    ON certificate_inventory (tenant_id, object_key, lifecycle, not_after)
    WHERE object_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_certificate_inventory_subject
    ON certificate_inventory (tenant_id, subject_dn, issuer_dn);
CREATE INDEX IF NOT EXISTS idx_certificate_inventory_san_dns
    ON certificate_inventory USING gin (san_dns jsonb_path_ops);

CREATE TABLE IF NOT EXISTS certificate_endpoint_observations (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    protocol text NOT NULL,
    host text NOT NULL,
    port integer NOT NULL,
    service text NOT NULL,
    certificate_fingerprint char(64) NOT NULL,
    observed_at timestamptz NOT NULL,
    source text NOT NULL,
    collector text NOT NULL,
    object_key text NULL,
    tls_version text NULL,
    cipher text NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    payload_fingerprint char(64) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    FOREIGN KEY (tenant_id, certificate_fingerprint)
        REFERENCES certificate_inventory(tenant_id, fingerprint_sha256)
        ON DELETE RESTRICT,
    CONSTRAINT certificate_endpoint_idempotency_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{2,127}$'
    ),
    CONSTRAINT certificate_endpoint_protocol_valid CHECK (
        protocol ~ '^[a-z0-9][a-z0-9_.:+/-]{0,31}$'
    ),
    CONSTRAINT certificate_endpoint_host_valid CHECK (length(host) BETWEEN 1 AND 253),
    CONSTRAINT certificate_endpoint_port_valid CHECK (port BETWEEN 1 AND 65535),
    CONSTRAINT certificate_endpoint_service_valid CHECK (
        length(trim(service)) BETWEEN 1 AND 128
    ),
    CONSTRAINT certificate_endpoint_fingerprint_valid CHECK (
        certificate_fingerprint ~ '^[a-f0-9]{64}$'
    ),
    CONSTRAINT certificate_endpoint_source_valid CHECK (
        source IN ('manual', 'discovery', 'import', 'acme', 'internal-pki', 'external-pki')
    ),
    CONSTRAINT certificate_endpoint_collector_valid CHECK (
        collector ~ '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{1,127}$'
    ),
    CONSTRAINT certificate_endpoint_object_key_valid CHECK (
        object_key IS NULL
        OR object_key ~ '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$'
    ),
    CONSTRAINT certificate_endpoint_payload_fingerprint_valid CHECK (
        payload_fingerprint ~ '^[a-f0-9]{64}$'
    )
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p00
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p01
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p02
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p03
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p04
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p05
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p06
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p07
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p08
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p09
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p10
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p11
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p12
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p13
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p14
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS certificate_endpoint_observations_p15
    PARTITION OF certificate_endpoint_observations FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_certificate_endpoint_certificate
    ON certificate_endpoint_observations (
        tenant_id, certificate_fingerprint, observed_at DESC, id
    );
CREATE INDEX IF NOT EXISTS idx_certificate_endpoint_address
    ON certificate_endpoint_observations (tenant_id, host, port, protocol, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_certificate_endpoint_object
    ON certificate_endpoint_observations (tenant_id, object_key, observed_at DESC)
    WHERE object_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_certificate_endpoint_observed_brin
    ON certificate_endpoint_observations USING brin (observed_at) WITH (pages_per_range = 64);

CREATE INDEX IF NOT EXISTS idx_audit_events_certificate_pki
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('certificate', 'certificate_endpoint', 'certificate_inventory');

COMMIT;
