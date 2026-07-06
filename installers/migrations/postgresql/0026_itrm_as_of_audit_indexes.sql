-- OpenInfra v0.29.23 - ITRM as-of and object audit indexes.
-- Non-destructive migration: accelerates historical object reconstruction, relation validity
-- lookups and object-scoped audit reads without modifying existing rows.

CREATE INDEX IF NOT EXISTS idx_source_snapshots_as_of
    ON source_object_snapshots (tenant_id, object_key, changed_at DESC, version DESC);

CREATE INDEX IF NOT EXISTS idx_source_relations_as_of_source
    ON source_relations (tenant_id, source_key, relation_type, active, valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_source_relations_as_of_target
    ON source_relations (tenant_id, target_key, relation_type, active, valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_audit_events_itrm_object_target
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type = 'source_object';
