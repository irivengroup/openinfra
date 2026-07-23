-- Generated deterministically from installers/migrations/postgresql/0008_source_governance.sql.
-- Source SHA-256: fc3b3c84d2917c5feb6e5502c05df2849d56b5649a6c829268e6119cf16f46b0
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE source_governance_rules (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    name VARCHAR2(255 CHAR) NOT NULL,
    object_kind VARCHAR2(128 CHAR),
    attribute_path VARCHAR2(255 CHAR) NOT NULL,
    authoritative_source VARCHAR2(255 CHAR) NOT NULL,
    priority NUMBER(10) DEFAULT 100 NOT NULL,
    freshness_seconds NUMBER(10),
    conflict_strategy VARCHAR2(255 CHAR) DEFAULT 'reject' NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, name),
    CHECK (REGEXP_LIKE(name, '^[a-z][a-z0-9_.:-]{1,63}$')),
    CHECK (object_kind IS NULL OR object_kind IN ('generic', 'device', 'interface', 'service', 'application')),
    CHECK (attribute_path = '*' OR REGEXP_LIKE(attribute_path, '^[a-z0-9][a-z0-9_:-]{0,63}(\.[a-z0-9][a-z0-9_:-]{0,63}){0,7}$')),
    CHECK (REGEXP_LIKE(authoritative_source, '^[a-z][a-z0-9_.:-]{1,63}$')),
    CHECK (priority >= 0 AND priority <= 1000000),
    CHECK (freshness_seconds IS NULL OR (freshness_seconds >= 60 AND freshness_seconds <= 31622400)),
    CHECK (conflict_strategy IN ('reject', 'accept_with_audit'))
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE INDEX idx_source_governance_rules_kind ON source_governance_rules (tenant_id, object_kind, active, priority DESC);

CREATE INDEX idx_source_governance_rules_attribute ON source_governance_rules (tenant_id, attribute_path, active);

CREATE INDEX idx_source_governance_rules_authority ON source_governance_rules (tenant_id, authoritative_source, active);

CREATE INDEX idx_audit_events_sot_governance ON audit_events (tenant_id, action, created_at DESC);
