-- OpenInfra v0.29.89 - P15 / EPIC-1502 declared and observed network flow matrix

BEGIN;

CREATE TABLE IF NOT EXISTS flow_declarations (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code text NOT NULL,
    source_selector text NOT NULL,
    destination_selector text NOT NULL,
    protocol text NOT NULL,
    destination_port_start integer NULL,
    destination_port_end integer NULL,
    decision text NOT NULL,
    priority integer NOT NULL DEFAULT 100,
    owner text NOT NULL,
    justification text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz NULL,
    status text NOT NULL,
    version integer NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, code),
    CONSTRAINT flow_declarations_code_valid CHECK (code ~ '^[A-Z0-9][A-Z0-9_.:-]{2,63}$'),
    CONSTRAINT flow_declarations_source_selector_valid CHECK (
        source_selector = 'any'
        OR source_selector ~ '^object:[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$'
        OR source_selector ~ '^cidr:[0-9a-fA-F:.]+/[0-9]{1,3}$'
    ),
    CONSTRAINT flow_declarations_destination_selector_valid CHECK (
        destination_selector = 'any'
        OR destination_selector ~ '^object:[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$'
        OR destination_selector ~ '^cidr:[0-9a-fA-F:.]+/[0-9]{1,3}$'
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
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS flow_declarations_p00 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS flow_declarations_p01 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS flow_declarations_p02 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS flow_declarations_p03 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS flow_declarations_p04 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS flow_declarations_p05 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS flow_declarations_p06 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS flow_declarations_p07 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS flow_declarations_p08 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS flow_declarations_p09 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS flow_declarations_p10 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS flow_declarations_p11 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS flow_declarations_p12 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS flow_declarations_p13 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS flow_declarations_p14 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS flow_declarations_p15 PARTITION OF flow_declarations
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_flow_declarations_effective
    ON flow_declarations (tenant_id, status, valid_from, valid_to, priority DESC, code);

CREATE INDEX IF NOT EXISTS idx_flow_declarations_updated
    ON flow_declarations (tenant_id, updated_at DESC, id);

CREATE TABLE IF NOT EXISTS flow_observations (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    source text NOT NULL,
    collector text NOT NULL,
    source_ip inet NOT NULL,
    destination_ip inet NOT NULL,
    source_object_key text NULL,
    destination_object_key text NULL,
    protocol text NOT NULL,
    destination_port integer NULL,
    packets bigint NOT NULL,
    bytes_count bigint NOT NULL,
    first_seen timestamptz NOT NULL,
    last_seen timestamptz NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    fingerprint char(64) NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT flow_observations_idempotency_valid CHECK (
        idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:/-]{7,127}$'
    ),
    CONSTRAINT flow_observations_source_valid CHECK (
        source IN ('netflow', 'sflow', 'ipfix', 'firewall-log', 'application-log', 'import', 'manual')
    ),
    CONSTRAINT flow_observations_collector_valid CHECK (
        collector ~ '^[a-z0-9][a-z0-9_.:-]{1,127}$'
    ),
    CONSTRAINT flow_observations_source_object_valid CHECK (
        source_object_key IS NULL
        OR source_object_key ~ '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$'
    ),
    CONSTRAINT flow_observations_destination_object_valid CHECK (
        destination_object_key IS NULL
        OR destination_object_key ~ '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$'
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
    CONSTRAINT flow_observations_fingerprint_valid CHECK (fingerprint ~ '^[a-f0-9]{64}$')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS flow_observations_p00 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS flow_observations_p01 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS flow_observations_p02 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS flow_observations_p03 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS flow_observations_p04 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS flow_observations_p05 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS flow_observations_p06 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS flow_observations_p07 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS flow_observations_p08 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS flow_observations_p09 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS flow_observations_p10 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS flow_observations_p11 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS flow_observations_p12 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS flow_observations_p13 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS flow_observations_p14 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS flow_observations_p15 PARTITION OF flow_observations
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_flow_observations_window
    ON flow_observations (tenant_id, last_seen DESC, first_seen, id);

CREATE INDEX IF NOT EXISTS idx_flow_observations_source
    ON flow_observations (tenant_id, source, last_seen DESC, id);

CREATE INDEX IF NOT EXISTS idx_flow_observations_endpoint
    ON flow_observations (
        tenant_id, source_ip, destination_ip, protocol, destination_port, last_seen DESC
    );

CREATE INDEX IF NOT EXISTS idx_flow_observations_source_object
    ON flow_observations (tenant_id, source_object_key, last_seen DESC)
    WHERE source_object_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_flow_observations_destination_object
    ON flow_observations (tenant_id, destination_object_key, last_seen DESC)
    WHERE destination_object_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_flow_observations_last_seen_brin
    ON flow_observations USING brin (last_seen) WITH (pages_per_range = 64);

CREATE INDEX IF NOT EXISTS idx_audit_events_flow_matrix
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('flow_declaration', 'flow_observation', 'flow_matrix');

COMMIT;
