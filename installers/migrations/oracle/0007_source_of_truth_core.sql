-- Generated deterministically from installers/migrations/postgresql/0007_source_of_truth_core.sql.
-- Source SHA-256: 77443df6b166a968a936d1860d571dde4a64ba1bf4dad3ab4de242a5dc51ab02
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE source_objects (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    object_key VARCHAR2(128 CHAR) NOT NULL,
    kind VARCHAR2(255 CHAR) NOT NULL,
    display_name VARCHAR2(255 CHAR) NOT NULL,
    attributes CLOB DEFAULT '{}' NOT NULL,
    tags CLOB DEFAULT '[]' NOT NULL,
    source_system VARCHAR2(255 CHAR) NOT NULL,
    version NUMBER(19) DEFAULT 1 NOT NULL,
    status VARCHAR2(255 CHAR) DEFAULT 'active' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, object_key),
    CHECK (version > 0),
    CHECK (REGEXP_LIKE(object_key, '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$')),
    CHECK (kind IN ('generic', 'device', 'interface', 'service', 'application')),
    CHECK (status IN ('active', 'retired')),
    CONSTRAINT ck_source_objects_attributes_json CHECK (attributes IS JSON),
    CONSTRAINT ck_source_objects_tags_json CHECK (tags IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE source_object_snapshots (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    object_key VARCHAR2(128 CHAR) NOT NULL,
    object_id VARCHAR2(36 CHAR) NOT NULL,
    version NUMBER(19) NOT NULL,
    payload CLOB NOT NULL,
    changed_by VARCHAR2(255 CHAR) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, object_key, version),
    CHECK (version > 0),
    CONSTRAINT ck_source_object_snapshots_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE source_relations (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    relation_type VARCHAR2(128 CHAR) NOT NULL,
    source_key VARCHAR2(128 CHAR) NOT NULL,
    target_key VARCHAR2(128 CHAR) NOT NULL,
    provenance VARCHAR2(255 CHAR) NOT NULL,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CHECK (source_key <> target_key),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE INDEX idx_source_objects_kind ON source_objects (tenant_id, kind, object_key);

CREATE INDEX idx_source_snapshots_lookup ON source_object_snapshots (tenant_id, object_key, version DESC);

CREATE INDEX idx_source_relations_source ON source_relations (tenant_id, source_key, relation_type, active);

CREATE INDEX idx_source_relations_target ON source_relations (tenant_id, target_key, relation_type, active);

CREATE INDEX idx_audit_events_sot ON audit_events (tenant_id, action, created_at DESC);
