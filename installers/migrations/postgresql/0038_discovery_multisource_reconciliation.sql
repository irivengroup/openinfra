-- OpenInfra v0.29.82 - P14 / EPIC-1405 multisource discovery reconciliation

BEGIN;

CREATE TABLE IF NOT EXISTS discovery_evidence (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source text NOT NULL,
    source_ref text NOT NULL,
    scope text NOT NULL,
    external_id text NOT NULL,
    object_key text NOT NULL,
    object_kind text NOT NULL,
    confidence numeric(7,6) NOT NULL,
    completeness numeric(7,6) NOT NULL,
    observed_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    payload_hash char(64) NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT discovery_evidence_source_valid CHECK (
        source IN (
            'snmp', 'ssh', 'winrm', 'vmware', 'proxmox', 'hyperv', 'kubernetes',
            'aws', 'azure', 'gcp', 'openstack', 'cloud', 'import', 'manual'
        )
    ),
    CONSTRAINT discovery_evidence_source_ref_not_blank CHECK (length(trim(source_ref)) >= 2),
    CONSTRAINT discovery_evidence_scope_valid CHECK (
        scope ~ '^[a-z0-9][a-z0-9_.:/-]{1,127}$'
    ),
    CONSTRAINT discovery_evidence_external_id_not_blank CHECK (length(trim(external_id)) >= 1),
    CONSTRAINT discovery_evidence_object_key_valid CHECK (
        object_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,255}$'
    ),
    CONSTRAINT discovery_evidence_object_kind_valid CHECK (
        object_kind ~ '^[a-z][a-z0-9.-]{1,63}$'
    ),
    CONSTRAINT discovery_evidence_confidence_valid CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT discovery_evidence_completeness_valid CHECK (completeness BETWEEN 0 AND 1),
    CONSTRAINT discovery_evidence_payload_hash_valid CHECK (payload_hash ~ '^[a-f0-9]{64}$'),
    CONSTRAINT discovery_evidence_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS discovery_evidence_p00 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS discovery_evidence_p01 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS discovery_evidence_p02 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS discovery_evidence_p03 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS discovery_evidence_p04 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS discovery_evidence_p05 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS discovery_evidence_p06 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS discovery_evidence_p07 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS discovery_evidence_p08 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS discovery_evidence_p09 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS discovery_evidence_p10 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS discovery_evidence_p11 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS discovery_evidence_p12 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS discovery_evidence_p13 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS discovery_evidence_p14 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS discovery_evidence_p15 PARTITION OF discovery_evidence
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_discovery_evidence_object
    ON discovery_evidence (tenant_id, object_key, object_kind, received_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_discovery_evidence_source
    ON discovery_evidence (tenant_id, source, source_ref, observed_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_discovery_evidence_payload_gin
    ON discovery_evidence USING gin (payload jsonb_path_ops);

CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    object_key text NOT NULL,
    object_kind text NOT NULL,
    evidence_ids uuid[] NOT NULL,
    source_count integer NOT NULL,
    confidence_score numeric(7,6) NOT NULL,
    freshness_score numeric(7,6) NOT NULL,
    completeness_score numeric(7,6) NOT NULL,
    overall_score numeric(7,6) NOT NULL,
    status text NOT NULL,
    conflicts jsonb NOT NULL,
    merged_payload jsonb NOT NULL,
    evaluated_at timestamptz NOT NULL,
    evaluated_by text NOT NULL,
    signature char(64) NOT NULL,
    resolution jsonb NULL,
    rsot_write_executed boolean NOT NULL DEFAULT false,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, signature),
    CONSTRAINT discovery_reconciliation_object_key_valid CHECK (
        object_key ~ '^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,255}$'
    ),
    CONSTRAINT discovery_reconciliation_object_kind_valid CHECK (
        object_kind ~ '^[a-z][a-z0-9.-]{1,63}$'
    ),
    CONSTRAINT discovery_reconciliation_evidence_count CHECK (
        array_length(evidence_ids, 1) >= 2
    ),
    CONSTRAINT discovery_reconciliation_source_count CHECK (source_count >= 2),
    CONSTRAINT discovery_reconciliation_confidence_valid CHECK (confidence_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_freshness_valid CHECK (freshness_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_completeness_valid CHECK (completeness_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_overall_valid CHECK (overall_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_status_valid CHECK (
        status IN ('ready', 'conflict', 'resolved')
    ),
    CONSTRAINT discovery_reconciliation_conflicts_array CHECK (jsonb_typeof(conflicts) = 'array'),
    CONSTRAINT discovery_reconciliation_payload_object CHECK (
        jsonb_typeof(merged_payload) = 'object'
    ),
    CONSTRAINT discovery_reconciliation_actor_not_blank CHECK (length(trim(evaluated_by)) >= 1),
    CONSTRAINT discovery_reconciliation_signature_valid CHECK (signature ~ '^[a-f0-9]{64}$'),
    CONSTRAINT discovery_reconciliation_no_direct_rsot_write CHECK (rsot_write_executed = false)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p00 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p01 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p02 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p03 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p04 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p05 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p06 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p07 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p08 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p09 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p10 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p11 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p12 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p13 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p14 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_cases_p15 PARTITION OF discovery_reconciliation_cases
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

CREATE INDEX IF NOT EXISTS idx_discovery_reconciliation_status
    ON discovery_reconciliation_cases (tenant_id, status, overall_score DESC, id);

CREATE INDEX IF NOT EXISTS idx_discovery_reconciliation_object
    ON discovery_reconciliation_cases (tenant_id, object_key, evaluated_at DESC, id);

CREATE INDEX IF NOT EXISTS idx_audit_events_discovery_reconciliation
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN ('discovery_evidence', 'discovery_reconciliation_case');

COMMIT;
