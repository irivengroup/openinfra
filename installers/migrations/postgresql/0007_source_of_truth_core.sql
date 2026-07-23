BEGIN;

CREATE TABLE IF NOT EXISTS source_objects (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    object_key text NOT NULL,
    kind text NOT NULL,
    display_name text NOT NULL,
    attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
    tags text[] NOT NULL DEFAULT ARRAY[]::text[],
    source_system text NOT NULL,
    version bigint NOT NULL DEFAULT 1,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, object_key),
    CHECK (version > 0),
    CHECK (object_key ~ '^[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]$'),
    CHECK (kind IN ('generic', 'device', 'interface', 'service', 'application')),
    CHECK (status IN ('active', 'retired'))
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS source_objects_p00 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 0);
CREATE TABLE IF NOT EXISTS source_objects_p01 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 1);
CREATE TABLE IF NOT EXISTS source_objects_p02 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 2);
CREATE TABLE IF NOT EXISTS source_objects_p03 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 3);
CREATE TABLE IF NOT EXISTS source_objects_p04 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 4);
CREATE TABLE IF NOT EXISTS source_objects_p05 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 5);
CREATE TABLE IF NOT EXISTS source_objects_p06 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 6);
CREATE TABLE IF NOT EXISTS source_objects_p07 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 7);
CREATE TABLE IF NOT EXISTS source_objects_p08 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 8);
CREATE TABLE IF NOT EXISTS source_objects_p09 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 9);
CREATE TABLE IF NOT EXISTS source_objects_p10 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 10);
CREATE TABLE IF NOT EXISTS source_objects_p11 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 11);
CREATE TABLE IF NOT EXISTS source_objects_p12 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 12);
CREATE TABLE IF NOT EXISTS source_objects_p13 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 13);
CREATE TABLE IF NOT EXISTS source_objects_p14 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 14);
CREATE TABLE IF NOT EXISTS source_objects_p15 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 15);
CREATE TABLE IF NOT EXISTS source_objects_p16 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 16);
CREATE TABLE IF NOT EXISTS source_objects_p17 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 17);
CREATE TABLE IF NOT EXISTS source_objects_p18 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 18);
CREATE TABLE IF NOT EXISTS source_objects_p19 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 19);
CREATE TABLE IF NOT EXISTS source_objects_p20 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 20);
CREATE TABLE IF NOT EXISTS source_objects_p21 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 21);
CREATE TABLE IF NOT EXISTS source_objects_p22 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 22);
CREATE TABLE IF NOT EXISTS source_objects_p23 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 23);
CREATE TABLE IF NOT EXISTS source_objects_p24 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 24);
CREATE TABLE IF NOT EXISTS source_objects_p25 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 25);
CREATE TABLE IF NOT EXISTS source_objects_p26 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 26);
CREATE TABLE IF NOT EXISTS source_objects_p27 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 27);
CREATE TABLE IF NOT EXISTS source_objects_p28 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 28);
CREATE TABLE IF NOT EXISTS source_objects_p29 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 29);
CREATE TABLE IF NOT EXISTS source_objects_p30 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 30);
CREATE TABLE IF NOT EXISTS source_objects_p31 PARTITION OF source_objects FOR VALUES WITH (MODULUS 32, REMAINDER 31);

CREATE TABLE IF NOT EXISTS source_object_snapshots (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    object_key text NOT NULL,
    object_id uuid NOT NULL,
    version bigint NOT NULL,
    payload jsonb NOT NULL,
    changed_by text NOT NULL,
    changed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, object_key, version),
    CHECK (version > 0)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p00 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 0);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p01 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 1);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p02 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 2);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p03 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 3);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p04 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 4);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p05 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 5);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p06 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 6);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p07 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 7);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p08 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 8);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p09 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 9);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p10 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 10);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p11 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 11);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p12 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 12);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p13 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 13);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p14 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 14);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p15 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 15);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p16 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 16);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p17 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 17);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p18 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 18);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p19 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 19);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p20 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 20);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p21 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 21);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p22 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 22);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p23 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 23);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p24 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 24);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p25 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 25);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p26 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 26);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p27 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 27);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p28 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 28);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p29 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 29);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p30 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 30);
CREATE TABLE IF NOT EXISTS source_object_snapshots_p31 PARTITION OF source_object_snapshots FOR VALUES WITH (MODULUS 32, REMAINDER 31);

CREATE TABLE IF NOT EXISTS source_relations (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    relation_type text NOT NULL,
    source_key text NOT NULL,
    target_key text NOT NULL,
    provenance text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    CHECK (source_key <> target_key),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
) PARTITION BY HASH (tenant_id);
CREATE TABLE IF NOT EXISTS source_relations_p00 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 0);
CREATE TABLE IF NOT EXISTS source_relations_p01 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 1);
CREATE TABLE IF NOT EXISTS source_relations_p02 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 2);
CREATE TABLE IF NOT EXISTS source_relations_p03 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 3);
CREATE TABLE IF NOT EXISTS source_relations_p04 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 4);
CREATE TABLE IF NOT EXISTS source_relations_p05 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 5);
CREATE TABLE IF NOT EXISTS source_relations_p06 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 6);
CREATE TABLE IF NOT EXISTS source_relations_p07 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 7);
CREATE TABLE IF NOT EXISTS source_relations_p08 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 8);
CREATE TABLE IF NOT EXISTS source_relations_p09 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 9);
CREATE TABLE IF NOT EXISTS source_relations_p10 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 10);
CREATE TABLE IF NOT EXISTS source_relations_p11 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 11);
CREATE TABLE IF NOT EXISTS source_relations_p12 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 12);
CREATE TABLE IF NOT EXISTS source_relations_p13 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 13);
CREATE TABLE IF NOT EXISTS source_relations_p14 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 14);
CREATE TABLE IF NOT EXISTS source_relations_p15 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 15);
CREATE TABLE IF NOT EXISTS source_relations_p16 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 16);
CREATE TABLE IF NOT EXISTS source_relations_p17 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 17);
CREATE TABLE IF NOT EXISTS source_relations_p18 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 18);
CREATE TABLE IF NOT EXISTS source_relations_p19 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 19);
CREATE TABLE IF NOT EXISTS source_relations_p20 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 20);
CREATE TABLE IF NOT EXISTS source_relations_p21 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 21);
CREATE TABLE IF NOT EXISTS source_relations_p22 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 22);
CREATE TABLE IF NOT EXISTS source_relations_p23 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 23);
CREATE TABLE IF NOT EXISTS source_relations_p24 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 24);
CREATE TABLE IF NOT EXISTS source_relations_p25 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 25);
CREATE TABLE IF NOT EXISTS source_relations_p26 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 26);
CREATE TABLE IF NOT EXISTS source_relations_p27 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 27);
CREATE TABLE IF NOT EXISTS source_relations_p28 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 28);
CREATE TABLE IF NOT EXISTS source_relations_p29 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 29);
CREATE TABLE IF NOT EXISTS source_relations_p30 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 30);
CREATE TABLE IF NOT EXISTS source_relations_p31 PARTITION OF source_relations FOR VALUES WITH (MODULUS 32, REMAINDER 31);

CREATE INDEX IF NOT EXISTS idx_source_objects_kind ON source_objects (tenant_id, kind, object_key);
CREATE INDEX IF NOT EXISTS idx_source_objects_tags ON source_objects USING gin (tags);
CREATE INDEX IF NOT EXISTS idx_source_objects_attributes ON source_objects USING gin (attributes jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_source_snapshots_lookup ON source_object_snapshots (tenant_id, object_key, version DESC);
CREATE INDEX IF NOT EXISTS idx_source_relations_source ON source_relations (tenant_id, source_key, relation_type, active);
CREATE INDEX IF NOT EXISTS idx_source_relations_target ON source_relations (tenant_id, target_key, relation_type, active);
CREATE INDEX IF NOT EXISTS idx_audit_events_sot ON audit_events (tenant_id, action, created_at DESC) WHERE action LIKE 'sot.%';

COMMIT;
