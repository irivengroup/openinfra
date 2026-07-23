-- Generated deterministically from installers/migrations/postgresql/0005_access_policy_abac.sql.
-- Source SHA-256: 2eddb2a170f6c9568dbe05b2c0ad53b38d6467044759abdb96e0b0699a80e3dc
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE access_policy_rules (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id),
    name VARCHAR2(255 CHAR) NOT NULL,
    permission VARCHAR2(255 CHAR) NOT NULL,
    effect VARCHAR2(255 CHAR) NOT NULL CHECK (effect IN ('allow', 'deny')),
    subjects CLOB DEFAULT '["*"]' NOT NULL,
    roles CLOB DEFAULT '[]' NOT NULL,
    site_codes CLOB DEFAULT '[]' NOT NULL,
    environments CLOB DEFAULT '[]' NOT NULL,
    active NUMBER(1) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, name),
    UNIQUE (tenant_id, id),
    CHECK (JSON_EXISTS(subjects, '$[0]') OR JSON_EXISTS(roles, '$[0]')),
    CONSTRAINT ck_access_policy_rules_subjects_json CHECK (subjects IS JSON),
    CONSTRAINT ck_access_policy_rules_roles_json CHECK (roles IS JSON),
    CONSTRAINT ck_access_policy_rules_site_codes_json CHECK (site_codes IS JSON),
    CONSTRAINT ck_access_policy_rules_environments_json CHECK (environments IS JSON)
);

CREATE INDEX idx_access_policy_rules_permission_active
    ON access_policy_rules (tenant_id, permission, active, name);

CREATE INDEX idx_audit_events_access_policy
    ON audit_events (tenant_id, action, created_at DESC);
