-- Generated deterministically from installers/migrations/postgresql/0038_discovery_multisource_reconciliation.sql.
-- Source SHA-256: 676af9b02a37ab503b3debc920dce8c8ab4081c0f3dc0caf118650db32a5597b
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE discovery_evidence (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source VARCHAR2(255 CHAR) NOT NULL,
    source_ref VARCHAR2(255 CHAR) NOT NULL,
    scope VARCHAR2(255 CHAR) NOT NULL,
    external_id VARCHAR2(128 CHAR) NOT NULL,
    object_key VARCHAR2(128 CHAR) NOT NULL,
    object_kind VARCHAR2(128 CHAR) NOT NULL,
    confidence NUMBER(7,6) NOT NULL,
    completeness NUMBER(7,6) NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    payload_hash CHAR(64 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT discovery_evidence_source_valid CHECK (
        source IN (
            'snmp', 'ssh', 'winrm', 'vmware', 'proxmox', 'hyperv', 'kubernetes',
            'aws', 'azure', 'gcp', 'openstack', 'cloud', 'import', 'manual'
        )
    ),
    CONSTRAINT discovery_evidence_source_ref_not_blank CHECK (length(trim(source_ref)) >= 2),
    CONSTRAINT discovery_evidence_scope_valid CHECK (
        REGEXP_LIKE(scope, '^[a-z0-9][a-z0-9_.:/-]{1,127}$')
    ),
    CONSTRAINT discovery_evidence_external_id_not_blank CHECK (length(trim(external_id)) >= 1),
    CONSTRAINT discovery_evidence_object_key_valid CHECK (
        REGEXP_LIKE(object_key, '^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,255}$')
    ),
    CONSTRAINT discovery_evidence_object_kind_valid CHECK (
        REGEXP_LIKE(object_kind, '^[a-z][a-z0-9.-]{1,63}$')
    ),
    CONSTRAINT discovery_evidence_confidence_valid CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT discovery_evidence_completeness_valid CHECK (completeness BETWEEN 0 AND 1),
    CONSTRAINT discovery_evidence_payload_hash_valid CHECK (REGEXP_LIKE(payload_hash, '^[a-f0-9]{64}$')),
    CONSTRAINT discovery_evidence_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_discovery_evidence_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_discovery_evidence_object
    ON discovery_evidence (tenant_id, object_key, object_kind, received_at DESC, id);

CREATE INDEX idx_discovery_evidence_source
    ON discovery_evidence (tenant_id, source, source_ref, observed_at DESC, id);

CREATE TABLE discovery_reconciliation_cases (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    object_key VARCHAR2(128 CHAR) NOT NULL,
    object_kind VARCHAR2(128 CHAR) NOT NULL,
    evidence_ids VARCHAR2(36 CHAR)[] NOT NULL,
    source_count NUMBER(10) NOT NULL,
    confidence_score NUMBER(7,6) NOT NULL,
    freshness_score NUMBER(7,6) NOT NULL,
    completeness_score NUMBER(7,6) NOT NULL,
    overall_score NUMBER(7,6) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    conflicts CLOB NOT NULL,
    merged_payload CLOB NOT NULL,
    evaluated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    evaluated_by VARCHAR2(255 CHAR) NOT NULL,
    signature CHAR(64 CHAR) NOT NULL,
    resolution CLOB NULL,
    rsot_write_executed NUMBER(1) DEFAULT 0 NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, signature),
    CONSTRAINT discovery_reconciliation_object_key_valid CHECK (
        REGEXP_LIKE(object_key, '^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,255}$')
    ),
    CONSTRAINT discovery_reconciliation_object_kind_valid CHECK (
        REGEXP_LIKE(object_kind, '^[a-z][a-z0-9.-]{1,63}$')
    ),
    CONSTRAINT discovery_reconciliation_evidence_count CHECK (
        JSON_EXISTS(evidence_ids, '$[1]')
    ),
    CONSTRAINT discovery_reconciliation_source_count CHECK (source_count >= 2),
    CONSTRAINT discovery_reconciliation_confidence_valid CHECK (confidence_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_freshness_valid CHECK (freshness_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_completeness_valid CHECK (completeness_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_overall_valid CHECK (overall_score BETWEEN 0 AND 1),
    CONSTRAINT discovery_reconciliation_status_valid CHECK (
        status IN ('ready', 'conflict', 'resolved')
    ),
    CONSTRAINT discovery_reconciliation_conflicts_array CHECK (JSON_EXISTS(conflicts, '$?(@.type() == \"array\")')),
    CONSTRAINT discovery_reconciliation_payload_object CHECK (
        JSON_EXISTS(merged_payload, '$?(@.type() == \"object\")')
    ),
    CONSTRAINT discovery_reconciliation_actor_not_blank CHECK (length(trim(evaluated_by)) >= 1),
    CONSTRAINT discovery_reconciliation_signature_valid CHECK (REGEXP_LIKE(signature, '^[a-f0-9]{64}$')),
    CONSTRAINT discovery_reconciliation_no_direct_rsot_write CHECK (rsot_write_executed = 0),
    CONSTRAINT ck_discovery_reconciliation_cases_conflicts_json CHECK (conflicts IS JSON),
    CONSTRAINT ck_discovery_reconciliation_cases_merged_payload_json CHECK (merged_payload IS JSON),
    CONSTRAINT ck_discovery_reconciliation_cases_resolution_json CHECK (resolution IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_discovery_reconciliation_status
    ON discovery_reconciliation_cases (tenant_id, status, overall_score DESC, id);

CREATE INDEX idx_discovery_reconciliation_object
    ON discovery_reconciliation_cases (tenant_id, object_key, evaluated_at DESC, id);

CREATE INDEX idx_audit_events_discovery_reconciliation
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
