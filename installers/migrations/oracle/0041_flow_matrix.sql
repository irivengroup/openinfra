-- Generated deterministically from installers/migrations/postgresql/0041_flow_matrix.sql.
-- Source SHA-256: 8b56ee61d55d6e1f201febfa66322b2a9aaefbad1d96d6f352349f11507374d9
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE flow_declarations (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR2(255 CHAR) NOT NULL,
    source_selector VARCHAR2(255 CHAR) NOT NULL,
    destination_selector VARCHAR2(255 CHAR) NOT NULL,
    protocol VARCHAR2(255 CHAR) NOT NULL,
    destination_port_start NUMBER(10) NULL,
    destination_port_end NUMBER(10) NULL,
    decision VARCHAR2(255 CHAR) NOT NULL,
    priority NUMBER(10) DEFAULT 100 NOT NULL,
    owner VARCHAR2(255 CHAR) NOT NULL,
    justification VARCHAR2(255 CHAR) NOT NULL,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    version NUMBER(10) NOT NULL,
    created_by VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_by VARCHAR2(255 CHAR) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CONSTRAINT flow_declarations_code_valid CHECK (REGEXP_LIKE(code, '^[A-Z0-9][A-Z0-9_.:-]{2,63}$')),
    CONSTRAINT flow_declarations_source_selector_valid CHECK (
        source_selector = 'any'
        OR REGEXP_LIKE(source_selector, '^object:[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$')
        OR REGEXP_LIKE(source_selector, '^cidr:[0-9a-fA-F:.]+/[0-9]{1,3}$')
    ),
    CONSTRAINT flow_declarations_destination_selector_valid CHECK (
        destination_selector = 'any'
        OR REGEXP_LIKE(destination_selector, '^object:[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$')
        OR REGEXP_LIKE(destination_selector, '^cidr:[0-9a-fA-F:.]+/[0-9]{1,3}$')
    ),
    CONSTRAINT flow_declarations_protocol_valid CHECK (
        protocol IN ('any', 'tcp', 'udp', 'sctp', 'icmp', 'icmpv6', 'esp', 'ah', 'gre')
    ),
    CONSTRAINT flow_declarations_ports_valid CHECK (
        (
            protocol IN ('tcp', 'udp', 'sctp')
            AND destination_port_start BETWEEN 1 AND 65535
            AND destination_port_end BETWEEN destination_port_start AND 65535
        )
        OR (
            protocol NOT IN ('tcp', 'udp', 'sctp')
            AND destination_port_start IS NULL
            AND destination_port_end IS NULL
        )
    ),
    CONSTRAINT flow_declarations_decision_valid CHECK (decision IN ('allow', 'deny')),
    CONSTRAINT flow_declarations_priority_valid CHECK (priority BETWEEN 0 AND 1000),
    CONSTRAINT flow_declarations_owner_valid CHECK (length(trim(owner)) BETWEEN 2 AND 128),
    CONSTRAINT flow_declarations_justification_valid CHECK (
        length(trim(justification)) BETWEEN 5 AND 1000
    ),
    CONSTRAINT flow_declarations_validity_ordered CHECK (
        valid_to IS NULL OR valid_to > valid_from
    ),
    CONSTRAINT flow_declarations_status_valid CHECK (status IN ('active', 'retired')),
    CONSTRAINT flow_declarations_version_valid CHECK (version >= 1),
    CONSTRAINT flow_declarations_timestamps_ordered CHECK (updated_at >= created_at)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_flow_declarations_effective
    ON flow_declarations (tenant_id, status, valid_from, valid_to, priority DESC, code);

CREATE INDEX idx_flow_declarations_updated
    ON flow_declarations (tenant_id, updated_at DESC, id);

CREATE TABLE flow_observations (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key VARCHAR2(128 CHAR) NOT NULL,
    source VARCHAR2(255 CHAR) NOT NULL,
    collector VARCHAR2(255 CHAR) NOT NULL,
    source_ip VARCHAR2(64 CHAR) NOT NULL,
    destination_ip VARCHAR2(64 CHAR) NOT NULL,
    source_object_key VARCHAR2(128 CHAR) NULL,
    destination_object_key VARCHAR2(128 CHAR) NULL,
    protocol VARCHAR2(255 CHAR) NOT NULL,
    destination_port NUMBER(10) NULL,
    packets NUMBER(19) NOT NULL,
    bytes_count NUMBER(19) NOT NULL,
    first_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    fingerprint CHAR(64 CHAR) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT flow_observations_idempotency_valid CHECK (
        REGEXP_LIKE(idempotency_key, '^[A-Za-z0-9][A-Za-z0-9_.:/-]{7,127}$')
    ),
    CONSTRAINT flow_observations_source_valid CHECK (
        source IN ('netflow', 'sflow', 'ipfix', 'firewall-log', 'application-log', 'import', 'manual')
    ),
    CONSTRAINT flow_observations_collector_valid CHECK (
        REGEXP_LIKE(collector, '^[a-z0-9][a-z0-9_.:-]{1,127}$')
    ),
    CONSTRAINT flow_observations_source_object_valid CHECK (
        source_object_key IS NULL
        OR REGEXP_LIKE(source_object_key, '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$')
    ),
    CONSTRAINT flow_observations_destination_object_valid CHECK (
        destination_object_key IS NULL
        OR REGEXP_LIKE(destination_object_key, '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$')
    ),
    CONSTRAINT flow_observations_protocol_valid CHECK (
        protocol IN ('tcp', 'udp', 'sctp', 'icmp', 'icmpv6', 'esp', 'ah', 'gre')
    ),
    CONSTRAINT flow_observations_port_valid CHECK (
        (
            protocol IN ('tcp', 'udp', 'sctp')
            AND destination_port BETWEEN 1 AND 65535
        )
        OR (
            protocol NOT IN ('tcp', 'udp', 'sctp')
            AND destination_port IS NULL
        )
    ),
    CONSTRAINT flow_observations_counters_valid CHECK (packets >= 1 AND bytes_count >= 0),
    CONSTRAINT flow_observations_time_ordered CHECK (last_seen >= first_seen),
    CONSTRAINT flow_observations_fingerprint_valid CHECK (REGEXP_LIKE(fingerprint, '^[a-f0-9]{64}$'))
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_flow_observations_window
    ON flow_observations (tenant_id, last_seen DESC, first_seen, id);

CREATE INDEX idx_flow_observations_source
    ON flow_observations (tenant_id, source, last_seen DESC, id);

CREATE INDEX idx_flow_observations_endpoint
    ON flow_observations (
        tenant_id, source_ip, destination_ip, protocol, destination_port, last_seen DESC
    );

CREATE INDEX idx_flow_observations_source_object
    ON flow_observations (tenant_id, source_object_key, last_seen DESC);

CREATE INDEX idx_flow_observations_destination_object
    ON flow_observations (tenant_id, destination_object_key, last_seen DESC);

CREATE INDEX idx_audit_events_flow_matrix
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
