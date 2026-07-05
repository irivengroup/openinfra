BEGIN;

CREATE TABLE IF NOT EXISTS identity_users (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username text NOT NULL,
    display_name text NOT NULL,
    email text,
    roles text[] NOT NULL DEFAULT '{}',
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, username)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS identity_users_p00 PARTITION OF identity_users
FOR VALUES WITH (MODULUS 32, REMAINDER 0);

CREATE TABLE IF NOT EXISTS identity_groups (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name text NOT NULL,
    display_name text NOT NULL,
    roles text[] NOT NULL DEFAULT '{}',
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, name)
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS identity_groups_p00 PARTITION OF identity_groups
FOR VALUES WITH (MODULUS 32, REMAINDER 0);

CREATE TABLE IF NOT EXISTS identity_group_memberships (
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username text NOT NULL,
    group_name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, username, group_name),
    FOREIGN KEY (tenant_id, username) REFERENCES identity_users(tenant_id, username)
        ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, group_name) REFERENCES identity_groups(tenant_id, name)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS identity_group_memberships_p00 PARTITION OF identity_group_memberships
FOR VALUES WITH (MODULUS 32, REMAINDER 0);

CREATE INDEX IF NOT EXISTS idx_identity_users_email
ON identity_users (tenant_id, email)
WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_identity_users_roles_gin
ON identity_users USING gin (roles);

CREATE INDEX IF NOT EXISTS idx_identity_groups_roles_gin
ON identity_groups USING gin (roles);

CREATE INDEX IF NOT EXISTS idx_identity_memberships_group
ON identity_group_memberships (tenant_id, group_name, username);

CREATE INDEX IF NOT EXISTS idx_audit_events_identity_actions
ON audit_events (tenant_id, action, created_at DESC)
WHERE action LIKE 'identity.%';

COMMIT;
