-- Generated deterministically from installers/migrations/postgresql/0026_itrm_as_of_audit_indexes.sql.
-- Source SHA-256: 87e72cf601e507e5536ade7c2b99cbe4a4cf9d72a50cdd0afcb4441c49e175f4
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE INDEX idx_source_snapshots_as_of
    ON source_object_snapshots (tenant_id, object_key, changed_at DESC, version DESC);

CREATE INDEX idx_source_relations_as_of_source
    ON source_relations (tenant_id, source_key, relation_type, active, valid_from, valid_to);

CREATE INDEX idx_source_relations_as_of_target
    ON source_relations (tenant_id, target_key, relation_type, active, valid_from, valid_to);

CREATE INDEX idx_audit_events_itrm_object_target
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
