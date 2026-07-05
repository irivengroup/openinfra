BEGIN;

CREATE TABLE IF NOT EXISTS source_governance_rules (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    name text NOT NULL,
    object_kind text,
    attribute_path text NOT NULL,
    authoritative_source text NOT NULL,
    priority integer NOT NULL DEFAULT 100,
    freshness_seconds integer,
    conflict_strategy text NOT NULL DEFAULT 'reject',
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, name),
    CHECK (name ~ '^[a-z][a-z0-9_.:-]{1,63}$'),
    CHECK (object_kind IS NULL OR object_kind IN ('generic', 'device', 'interface', 'service', 'application')),
    CHECK (attribute_path = '*' OR attribute_path ~ '^[a-z0-9][a-z0-9_:-]{0,63}(\.[a-z0-9][a-z0-9_:-]{0,63}){0,7}$'),
    CHECK (authoritative_source ~ '^[a-z][a-z0-9_.:-]{1,63}$'),
    CHECK (priority >= 0 AND priority <= 1000000),
    CHECK (freshness_seconds IS NULL OR (freshness_seconds >= 60 AND freshness_seconds <= 31622400)),
    CHECK (conflict_strategy IN ('reject', 'accept_with_audit'))
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS source_governance_rules_p00 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 0);
CREATE TABLE IF NOT EXISTS source_governance_rules_p01 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 1);
CREATE TABLE IF NOT EXISTS source_governance_rules_p02 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 2);
CREATE TABLE IF NOT EXISTS source_governance_rules_p03 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 3);
CREATE TABLE IF NOT EXISTS source_governance_rules_p04 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 4);
CREATE TABLE IF NOT EXISTS source_governance_rules_p05 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 5);
CREATE TABLE IF NOT EXISTS source_governance_rules_p06 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 6);
CREATE TABLE IF NOT EXISTS source_governance_rules_p07 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 7);
CREATE TABLE IF NOT EXISTS source_governance_rules_p08 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 8);
CREATE TABLE IF NOT EXISTS source_governance_rules_p09 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 9);
CREATE TABLE IF NOT EXISTS source_governance_rules_p10 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 10);
CREATE TABLE IF NOT EXISTS source_governance_rules_p11 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 11);
CREATE TABLE IF NOT EXISTS source_governance_rules_p12 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 12);
CREATE TABLE IF NOT EXISTS source_governance_rules_p13 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 13);
CREATE TABLE IF NOT EXISTS source_governance_rules_p14 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 14);
CREATE TABLE IF NOT EXISTS source_governance_rules_p15 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 15);
CREATE TABLE IF NOT EXISTS source_governance_rules_p16 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 16);
CREATE TABLE IF NOT EXISTS source_governance_rules_p17 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 17);
CREATE TABLE IF NOT EXISTS source_governance_rules_p18 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 18);
CREATE TABLE IF NOT EXISTS source_governance_rules_p19 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 19);
CREATE TABLE IF NOT EXISTS source_governance_rules_p20 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 20);
CREATE TABLE IF NOT EXISTS source_governance_rules_p21 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 21);
CREATE TABLE IF NOT EXISTS source_governance_rules_p22 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 22);
CREATE TABLE IF NOT EXISTS source_governance_rules_p23 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 23);
CREATE TABLE IF NOT EXISTS source_governance_rules_p24 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 24);
CREATE TABLE IF NOT EXISTS source_governance_rules_p25 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 25);
CREATE TABLE IF NOT EXISTS source_governance_rules_p26 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 26);
CREATE TABLE IF NOT EXISTS source_governance_rules_p27 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 27);
CREATE TABLE IF NOT EXISTS source_governance_rules_p28 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 28);
CREATE TABLE IF NOT EXISTS source_governance_rules_p29 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 29);
CREATE TABLE IF NOT EXISTS source_governance_rules_p30 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 30);
CREATE TABLE IF NOT EXISTS source_governance_rules_p31 PARTITION OF source_governance_rules FOR VALUES WITH (MODULUS 32, REMAINDER 31);

CREATE INDEX IF NOT EXISTS idx_source_governance_rules_kind ON source_governance_rules (tenant_id, object_kind, active, priority DESC);
CREATE INDEX IF NOT EXISTS idx_source_governance_rules_attribute ON source_governance_rules (tenant_id, attribute_path, active);
CREATE INDEX IF NOT EXISTS idx_source_governance_rules_authority ON source_governance_rules (tenant_id, authoritative_source, active);
CREATE INDEX IF NOT EXISTS idx_audit_events_sot_governance ON audit_events (tenant_id, action, created_at DESC) WHERE action LIKE 'sot.governance.%';

COMMIT;
