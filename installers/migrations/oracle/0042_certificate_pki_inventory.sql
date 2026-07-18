-- Generated deterministically from installers/migrations/postgresql/0042_certificate_pki_inventory.sql.
-- Source SHA-256: fe6a6bed9845c6ff24d15c0dc1fd2dd081275a49b09bc1fba9dc43689fa964f9
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE certificate_inventory (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    fingerprint_sha256 CHAR(64 CHAR) NOT NULL,
    serial_number VARCHAR2(255 CHAR) NOT NULL,
    subject_dn VARCHAR2(255 CHAR) NOT NULL,
    issuer_dn VARCHAR2(255 CHAR) NOT NULL,
    common_name VARCHAR2(255 CHAR) NULL,
    san_dns CLOB DEFAULT '[]' NOT NULL,
    san_ip CLOB DEFAULT '[]' NOT NULL,
    san_email CLOB DEFAULT '[]' NOT NULL,
    san_uri CLOB DEFAULT '[]' NOT NULL,
    not_before TIMESTAMP WITH TIME ZONE NOT NULL,
    not_after TIMESTAMP WITH TIME ZONE NOT NULL,
    public_key_algorithm VARCHAR2(255 CHAR) NOT NULL,
    public_key_size NUMBER(10) NULL,
    signature_algorithm VARCHAR2(255 CHAR) NOT NULL,
    is_ca NUMBER(1) DEFAULT 0 NOT NULL,
    chain_fingerprints CLOB DEFAULT '[]' NOT NULL,
    owner VARCHAR2(255 CHAR) NOT NULL,
    environment VARCHAR2(255 CHAR) NOT NULL,
    source VARCHAR2(255 CHAR) NOT NULL,
    object_key VARCHAR2(128 CHAR) NULL,
    lifecycle VARCHAR2(255 CHAR) NOT NULL,
    version NUMBER(10) NOT NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint_sha256),
    CONSTRAINT certificate_inventory_fingerprint_valid CHECK (
        REGEXP_LIKE(fingerprint_sha256, '^[a-f0-9]{64}$')
    ),
    CONSTRAINT certificate_inventory_serial_valid CHECK (
        REGEXP_LIKE(serial_number, '^[0-9A-F]{1,128}$')
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
    CONSTRAINT certificate_inventory_san_dns_array CHECK (JSON_EXISTS(san_dns, '$?(@.type() == \"array\")')),
    CONSTRAINT certificate_inventory_san_ip_array CHECK (JSON_EXISTS(san_ip, '$?(@.type() == \"array\")')),
    CONSTRAINT certificate_inventory_san_email_array CHECK (JSON_EXISTS(san_email, '$?(@.type() == \"array\")')),
    CONSTRAINT certificate_inventory_san_uri_array CHECK (JSON_EXISTS(san_uri, '$?(@.type() == \"array\")')),
    CONSTRAINT certificate_inventory_dates_ordered CHECK (not_after > not_before),
    CONSTRAINT certificate_inventory_public_key_size_valid CHECK (
        public_key_size IS NULL OR public_key_size BETWEEN 128 AND 65536
    ),
    CONSTRAINT certificate_inventory_chain_array CHECK (
        JSON_EXISTS(chain_fingerprints, '$?(@.type() == \"array\")')
        AND NOT JSON_EXISTS(chain_fingerprints, '$[16]')
    ),
    CONSTRAINT certificate_inventory_owner_valid CHECK (
        length(trim(owner)) BETWEEN 2 AND 255
    ),
    CONSTRAINT certificate_inventory_environment_valid CHECK (
        REGEXP_LIKE(environment, '^[a-z0-9][a-z0-9_.:+/-]{0,63}$')
    ),
    CONSTRAINT certificate_inventory_source_valid CHECK (
        source IN ('manual', 'discovery', 'import', 'acme', 'internal-pki', 'external-pki')
    ),
    CONSTRAINT certificate_inventory_object_key_valid CHECK (
        object_key IS NULL
        OR REGEXP_LIKE(object_key, '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$')
    ),
    CONSTRAINT certificate_inventory_lifecycle_valid CHECK (
        lifecycle IN ('active', 'retired')
    ),
    CONSTRAINT certificate_inventory_version_valid CHECK (version >= 1),
    CONSTRAINT certificate_inventory_timestamps_ordered CHECK (updated_at >= created_at),
    CONSTRAINT ck_certificate_inventory_san_dns_json CHECK (san_dns IS JSON),
    CONSTRAINT ck_certificate_inventory_san_ip_json CHECK (san_ip IS JSON),
    CONSTRAINT ck_certificate_inventory_san_email_json CHECK (san_email IS JSON),
    CONSTRAINT ck_certificate_inventory_san_uri_json CHECK (san_uri IS JSON),
    CONSTRAINT ck_certificate_inventory_chain_fingerprints_json CHECK (chain_fingerprints IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_certificate_inventory_expiration
    ON certificate_inventory (tenant_id, lifecycle, not_after, fingerprint_sha256);

CREATE INDEX idx_certificate_inventory_owner
    ON certificate_inventory (tenant_id, owner, environment, lifecycle, not_after);

CREATE INDEX idx_certificate_inventory_object
    ON certificate_inventory (tenant_id, object_key, lifecycle, not_after);

CREATE INDEX idx_certificate_inventory_subject
    ON certificate_inventory (tenant_id, subject_dn, issuer_dn);

CREATE TABLE certificate_endpoint_observations (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    protocol VARCHAR2(255 CHAR) NOT NULL,
    host VARCHAR2(255 CHAR) NOT NULL,
    port NUMBER(10) NOT NULL,
    service VARCHAR2(255 CHAR) NOT NULL,
    certificate_fingerprint CHAR(64 CHAR) NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR2(255 CHAR) NOT NULL,
    collector VARCHAR2(255 CHAR) NOT NULL,
    object_key VARCHAR2(128 CHAR) NULL,
    tls_version VARCHAR2(255 CHAR) NULL,
    cipher VARCHAR2(255 CHAR) NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    payload_fingerprint CHAR(64 CHAR) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    FOREIGN KEY (tenant_id, certificate_fingerprint)
        REFERENCES certificate_inventory(tenant_id, fingerprint_sha256),
    CONSTRAINT certificate_endpoint_idempotency_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{2,127}$')
    ),
    CONSTRAINT certificate_endpoint_protocol_valid CHECK (
        REGEXP_LIKE(protocol, '^[a-z0-9][a-z0-9_.:+/-]{0,31}$')
    ),
    CONSTRAINT certificate_endpoint_host_valid CHECK (length(host) BETWEEN 1 AND 253),
    CONSTRAINT certificate_endpoint_port_valid CHECK (port BETWEEN 1 AND 65535),
    CONSTRAINT certificate_endpoint_service_valid CHECK (
        length(trim(service)) BETWEEN 1 AND 128
    ),
    CONSTRAINT certificate_endpoint_fingerprint_valid CHECK (
        REGEXP_LIKE(certificate_fingerprint, '^[a-f0-9]{64}$')
    ),
    CONSTRAINT certificate_endpoint_source_valid CHECK (
        source IN ('manual', 'discovery', 'import', 'acme', 'internal-pki', 'external-pki')
    ),
    CONSTRAINT certificate_endpoint_collector_valid CHECK (
        REGEXP_LIKE(collector, '^[A-Za-z0-9][A-Za-z0-9_.:@/-]{1,127}$')
    ),
    CONSTRAINT certificate_endpoint_object_key_valid CHECK (
        object_key IS NULL
        OR REGEXP_LIKE(object_key, '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$')
    ),
    CONSTRAINT certificate_endpoint_payload_fingerprint_valid CHECK (
        REGEXP_LIKE(payload_fingerprint, '^[a-f0-9]{64}$')
    )
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_certificate_endpoint_certificate
    ON certificate_endpoint_observations (
        tenant_id, certificate_fingerprint, observed_at DESC, id
    );

CREATE INDEX idx_certificate_endpoint_address
    ON certificate_endpoint_observations (tenant_id, host, port, protocol, observed_at DESC);

CREATE INDEX idx_certificate_endpoint_object
    ON certificate_endpoint_observations (tenant_id, object_key, observed_at DESC);

CREATE INDEX idx_audit_events_certificate_pki
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
