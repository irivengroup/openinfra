-- Generated deterministically from installers/migrations/postgresql/0004_identity_users_groups.sql.
-- Source SHA-256: 307da3c5790a37abcd28f0be0c21ef997f5c42a63157a30444abd38af8eac6ab
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE identity_users (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username VARCHAR2(255 CHAR) NOT NULL,
    display_name VARCHAR2(255 CHAR) NOT NULL,
    email VARCHAR2(255 CHAR),
    roles CLOB DEFAULT '[]' NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, username),
    CONSTRAINT ck_identity_users_roles_json CHECK (roles IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE identity_groups (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR2(255 CHAR) NOT NULL,
    display_name VARCHAR2(255 CHAR) NOT NULL,
    roles CLOB DEFAULT '[]' NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, name),
    CONSTRAINT ck_identity_groups_roles_json CHECK (roles IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE TABLE identity_group_memberships (
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username VARCHAR2(255 CHAR) NOT NULL,
    group_name VARCHAR2(255 CHAR) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, username, group_name),
    FOREIGN KEY (tenant_id, username) REFERENCES identity_users(tenant_id, username)
        ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, group_name) REFERENCES identity_groups(tenant_id, name)
        ON DELETE CASCADE
)
PARTITION BY HASH (tenant_id) PARTITIONS 32;

CREATE INDEX idx_identity_users_email
ON identity_users (tenant_id, email);

CREATE INDEX idx_identity_memberships_group
ON identity_group_memberships (tenant_id, group_name, username);

CREATE INDEX idx_audit_events_identity_actions
ON audit_events (tenant_id, action, created_at DESC);
