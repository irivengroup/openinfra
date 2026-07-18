-- Generated deterministically from installers/migrations/postgresql/0025_authentication_ldap_ipa_rbac.sql.
-- Source SHA-256: 2a6b265409a4c41e51df7861bef5d69c0744c5ece6dc9aa895fae97c3aba1385
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE auth_provider_configs (
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    provider_mode VARCHAR2(255 CHAR) NOT NULL,
    directory_url VARCHAR2(1000 CHAR) NOT NULL,
    base_dn VARCHAR2(255 CHAR) NOT NULL,
    user_filter VARCHAR2(255 CHAR) NOT NULL,
    group_filter VARCHAR2(255 CHAR) NOT NULL,
    bind_dn_ref VARCHAR2(255 CHAR) NULL,
    bind_password_ref VARCHAR2(255 CHAR) NULL,
    ca_cert_ref VARCHAR2(255 CHAR) NULL,
    tls_required NUMBER(1) DEFAULT 1 NOT NULL,
    nested_groups NUMBER(1) DEFAULT 1 NOT NULL,
    cache_ttl_seconds NUMBER(10) DEFAULT 300 NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, provider_mode),
    CONSTRAINT auth_provider_mode_check CHECK (provider_mode IN ('ldap', 'ipa')),
    CONSTRAINT auth_provider_ldaps_check CHECK (directory_url LIKE 'ldaps://%'),
    CONSTRAINT auth_provider_tls_check CHECK (tls_required = 1),
    CONSTRAINT auth_provider_cache_ttl_check CHECK (cache_ttl_seconds BETWEEN 30 AND 3600),
    CONSTRAINT auth_provider_bind_ref_pair_check CHECK (
        (bind_dn_ref IS NULL AND bind_password_ref IS NULL)
        OR (bind_dn_ref IS NOT NULL AND bind_password_ref IS NOT NULL)
    )
);

CREATE TABLE external_group_role_mappings (
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    provider_mode VARCHAR2(255 CHAR) NOT NULL,
    external_group VARCHAR2(255 CHAR) NOT NULL,
    internal_group_name VARCHAR2(255 CHAR) NOT NULL,
    role_names CLOB NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, provider_mode, external_group),
    CONSTRAINT external_group_provider_check CHECK (provider_mode IN ('ldap', 'ipa')),
    CONSTRAINT external_group_role_names_check CHECK (JSON_EXISTS(role_names, '$[0]')),
    CONSTRAINT external_group_internal_group_check CHECK (
        REGEXP_LIKE(internal_group_name, '^external-[a-f0-9]{20}$')
    ),
    CONSTRAINT ck_external_group_role_mappings_role_names_json CHECK (role_names IS JSON)
);

CREATE INDEX idx_external_group_role_mappings_tenant_active
    ON external_group_role_mappings (tenant_id, provider_mode, active);

CREATE TABLE auth_permission_audit_events (
    tenant_id VARCHAR2(128 CHAR) NOT NULL,
    event_id VARCHAR2(128 CHAR) NOT NULL,
    subject VARCHAR2(255 CHAR) NOT NULL,
    provider_mode VARCHAR2(255 CHAR) NOT NULL,
    action VARCHAR2(255 CHAR) NOT NULL,
    effective_roles CLOB NOT NULL,
    mapped_groups CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, created_at, event_id),
    CONSTRAINT auth_permission_audit_provider_check CHECK (
        provider_mode IN ('standard', 'ldap', 'ipa')
    ),
    CONSTRAINT auth_permission_audit_roles_check CHECK (JSON_EXISTS(effective_roles, '$[0]')),
    CONSTRAINT ck_auth_permission_audit_events_effective_roles_json CHECK (effective_roles IS JSON),
    CONSTRAINT ck_auth_permission_audit_events_mapped_groups_json CHECK (mapped_groups IS JSON)
);
