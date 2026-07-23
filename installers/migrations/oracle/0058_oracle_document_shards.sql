-- Generated deterministically from installers/migrations/postgresql/0058_oracle_document_shards.sql.
-- Source SHA-256: 8ac0977a2b7f461a3b7e8eea304ae5cbdcd4b0b29b4c38711654b75a3a45a3d3
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE openinfra_document_shards (
    shard_key VARCHAR2(128 CHAR) NOT NULL,
    payload CLOB DEFAULT '{}' NOT NULL,
    version NUMBER(19) DEFAULT 0 NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (shard_key),
    CONSTRAINT ck_openinfra_document_shards_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (shard_key) PARTITIONS 8;

CREATE INDEX idx_openinfra_document_shards_updated
    ON openinfra_document_shards (updated_at DESC);

CREATE INDEX idx_audit_events_oracle_shards
    ON audit_events (tenant_id, target_type, created_at DESC);
