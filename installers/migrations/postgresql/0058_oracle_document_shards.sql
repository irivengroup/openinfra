CREATE TABLE IF NOT EXISTS openinfra_document_shards (
    shard_key text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    version bigint NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (shard_key)
) PARTITION BY HASH (shard_key);

CREATE TABLE IF NOT EXISTS openinfra_document_shards_p00 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 0);
CREATE TABLE IF NOT EXISTS openinfra_document_shards_p01 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 1);
CREATE TABLE IF NOT EXISTS openinfra_document_shards_p02 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 2);
CREATE TABLE IF NOT EXISTS openinfra_document_shards_p03 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 3);
CREATE TABLE IF NOT EXISTS openinfra_document_shards_p04 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 4);
CREATE TABLE IF NOT EXISTS openinfra_document_shards_p05 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 5);
CREATE TABLE IF NOT EXISTS openinfra_document_shards_p06 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 6);
CREATE TABLE IF NOT EXISTS openinfra_document_shards_p07 PARTITION OF openinfra_document_shards FOR VALUES WITH (MODULUS 8, REMAINDER 7);

CREATE INDEX idx_openinfra_document_shards_updated
    ON openinfra_document_shards (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_oracle_shards
    ON audit_events (tenant_id, target_type, created_at DESC);
