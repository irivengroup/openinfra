CREATE TABLE IF NOT EXISTS auth_provider_configs (
    tenant_id text NOT NULL,
    provider_mode text NOT NULL,
    directory_url text NOT NULL,
    base_dn text NOT NULL,
    user_filter text NOT NULL,
    group_filter text NOT NULL,
    bind_dn_ref text NULL,
    bind_password_ref text NULL,
    ca_cert_ref text NULL,
    tls_required boolean NOT NULL DEFAULT true,
    nested_groups boolean NOT NULL DEFAULT true,
    cache_ttl_seconds integer NOT NULL DEFAULT 300,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, provider_mode),
    CONSTRAINT auth_provider_mode_check CHECK (provider_mode IN ('ldap', 'ipa')),
    CONSTRAINT auth_provider_ldaps_check CHECK (directory_url LIKE 'ldaps://%'),
    CONSTRAINT auth_provider_tls_check CHECK (tls_required = true),
    CONSTRAINT auth_provider_cache_ttl_check CHECK (cache_ttl_seconds BETWEEN 30 AND 3600),
    CONSTRAINT auth_provider_bind_ref_pair_check CHECK (
        (bind_dn_ref IS NULL AND bind_password_ref IS NULL)
        OR (bind_dn_ref IS NOT NULL AND bind_password_ref IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS external_group_role_mappings (
    tenant_id text NOT NULL,
    provider_mode text NOT NULL,
    external_group text NOT NULL,
    internal_group_name text NOT NULL,
    role_names text[] NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, provider_mode, external_group),
    CONSTRAINT external_group_provider_check CHECK (provider_mode IN ('ldap', 'ipa')),
    CONSTRAINT external_group_role_names_check CHECK (cardinality(role_names) > 0),
    CONSTRAINT external_group_internal_group_check CHECK (
        internal_group_name ~ '^external-[a-f0-9]{20}$'
    )
);

CREATE INDEX IF NOT EXISTS idx_external_group_role_mappings_tenant_active
    ON external_group_role_mappings (tenant_id, provider_mode, active);

CREATE TABLE IF NOT EXISTS auth_permission_audit_events (
    tenant_id text NOT NULL,
    event_id text NOT NULL,
    subject text NOT NULL,
    provider_mode text NOT NULL,
    action text NOT NULL,
    effective_roles text[] NOT NULL,
    mapped_groups text[] NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, created_at, event_id),
    CONSTRAINT auth_permission_audit_provider_check CHECK (
        provider_mode IN ('standard', 'ldap', 'ipa')
    ),
    CONSTRAINT auth_permission_audit_roles_check CHECK (cardinality(effective_roles) > 0)
) PARTITION BY RANGE (created_at);

CREATE TABLE IF NOT EXISTS auth_permission_audit_events_default
    PARTITION OF auth_permission_audit_events DEFAULT;
