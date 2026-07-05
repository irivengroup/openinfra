BEGIN;

CREATE TABLE IF NOT EXISTS access_policy_rules (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id),
    name text NOT NULL,
    permission text NOT NULL,
    effect text NOT NULL CHECK (effect IN ('allow', 'deny')),
    subjects text[] NOT NULL DEFAULT ARRAY['*']::text[],
    roles text[] NOT NULL DEFAULT ARRAY[]::text[],
    site_codes text[] NOT NULL DEFAULT ARRAY[]::text[],
    environments text[] NOT NULL DEFAULT ARRAY[]::text[],
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, name),
    UNIQUE (tenant_id, id),
    CHECK (array_length(subjects, 1) IS NOT NULL OR array_length(roles, 1) IS NOT NULL)
) PARTITION BY LIST (tenant_id);

CREATE TABLE IF NOT EXISTS access_policy_rules_default
    PARTITION OF access_policy_rules DEFAULT;

CREATE INDEX IF NOT EXISTS idx_access_policy_rules_permission_active
    ON access_policy_rules (tenant_id, permission, active, name);

CREATE INDEX IF NOT EXISTS idx_access_policy_rules_subjects_gin
    ON access_policy_rules USING gin (subjects);

CREATE INDEX IF NOT EXISTS idx_access_policy_rules_roles_gin
    ON access_policy_rules USING gin (roles);

CREATE INDEX IF NOT EXISTS idx_access_policy_rules_sites_gin
    ON access_policy_rules USING gin (site_codes);

CREATE INDEX IF NOT EXISTS idx_access_policy_rules_environments_gin
    ON access_policy_rules USING gin (environments);

CREATE INDEX IF NOT EXISTS idx_audit_events_access_policy
    ON audit_events (tenant_id, action, created_at DESC)
    WHERE action LIKE 'access.policy.%';

COMMIT;
