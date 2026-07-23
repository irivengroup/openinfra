-- Generated deterministically from installers/migrations/postgresql/0048_sbom_vulnerabilities_exposure.sql.
-- Source SHA-256: 07bd7c97f1f2d298dad39cbe026a956371e0f142a5a409c3e049b2f4a0959502
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE TABLE sbom_documents (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    application VARCHAR2(255 CHAR) NOT NULL,
    release VARCHAR2(255 CHAR) NOT NULL,
    environment VARCHAR2(255 CHAR) NOT NULL,
    format VARCHAR2(255 CHAR) NOT NULL,
    source_hash CHAR(64 CHAR) NOT NULL,
    fingerprint CHAR(64 CHAR) NOT NULL,
    document_version NUMBER(10) NOT NULL,
    component_count NUMBER(10) NOT NULL,
    imported_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint),
    CONSTRAINT sbom_document_format_valid CHECK (format IN ('cyclonedx','spdx')),
    CONSTRAINT sbom_document_hash_valid CHECK (REGEXP_LIKE(source_hash, '^[a-f0-9]{64}$')),
    CONSTRAINT sbom_document_fingerprint_valid CHECK (REGEXP_LIKE(fingerprint, '^[a-f0-9]{64}$')),
    CONSTRAINT sbom_document_version_valid CHECK (document_version > 0),
    CONSTRAINT sbom_document_component_count_valid CHECK (component_count > 0),
    CONSTRAINT sbom_document_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_sbom_documents_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE sbom_vulnerabilities (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cve_id VARCHAR2(128 CHAR) NOT NULL,
    identity_key VARCHAR2(128 CHAR) NOT NULL,
    cvss_score NUMBER(3,1) NOT NULL,
    known_exploited NUMBER(1) NOT NULL,
    imported_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, identity_key),
    CONSTRAINT sbom_vulnerability_cve_valid CHECK (REGEXP_LIKE(cve_id, '^CVE-[0-9]{4}-[0-9]{4,19}$')),
    CONSTRAINT sbom_vulnerability_cvss_valid CHECK (cvss_score >= 0 AND cvss_score <= 10),
    CONSTRAINT sbom_vulnerability_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_sbom_vulnerabilities_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE sbom_exposure_contexts (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    application VARCHAR2(255 CHAR) NOT NULL,
    environment VARCHAR2(255 CHAR) NOT NULL,
    internet_exposed NUMBER(1) NOT NULL,
    flow_exposed NUMBER(1) NOT NULL,
    business_criticality NUMBER(5) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, application, environment),
    CONSTRAINT sbom_exposure_criticality_valid CHECK (business_criticality BETWEEN 1 AND 5),
    CONSTRAINT sbom_exposure_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_sbom_exposure_contexts_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE sbom_risk_findings (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id VARCHAR2(36 CHAR) NOT NULL,
    cve_id VARCHAR2(128 CHAR) NOT NULL,
    priority VARCHAR2(255 CHAR) NOT NULL,
    status VARCHAR2(255 CHAR) NOT NULL,
    contextual_score NUMBER(3,1) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT sbom_finding_priority_valid CHECK (priority IN ('low','medium','high','critical')),
    CONSTRAINT sbom_finding_status_valid CHECK (status IN ('open','accepted','mitigated','false-positive')),
    CONSTRAINT sbom_finding_score_valid CHECK (contextual_score >= 0 AND contextual_score <= 10),
    CONSTRAINT sbom_finding_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_sbom_risk_findings_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE sbom_comparisons (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    base_document_id VARCHAR2(36 CHAR) NOT NULL,
    target_document_id VARCHAR2(36 CHAR) NOT NULL,
    input_digest CHAR(64 CHAR) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload CLOB NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, input_digest),
    CONSTRAINT sbom_comparison_documents_distinct CHECK (base_document_id <> target_document_id),
    CONSTRAINT sbom_comparison_digest_valid CHECK (REGEXP_LIKE(input_digest, '^[a-f0-9]{64}$')),
    CONSTRAINT sbom_comparison_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT ck_sbom_comparisons_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE TABLE sbom_event_outbox (
    id VARCHAR2(36 CHAR) NOT NULL,
    tenant_id VARCHAR2(128 CHAR) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id VARCHAR2(36 CHAR) NOT NULL,
    event_name VARCHAR2(255 CHAR) NOT NULL,
    payload CLOB NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    attempt_count NUMBER(10) DEFAULT 0 NOT NULL,
    last_error VARCHAR2(255 CHAR),
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT sbom_event_name_valid CHECK (REGEXP_LIKE(event_name, '^[a-z][a-z0-9_.-]{2,120}$')),
    CONSTRAINT sbom_event_payload_object CHECK (JSON_EXISTS(payload, '$?(@.type() == \"object\")')),
    CONSTRAINT sbom_event_attempt_count_valid CHECK (attempt_count >= 0),
    CONSTRAINT ck_sbom_event_outbox_payload_json CHECK (payload IS JSON)
)
PARTITION BY HASH (tenant_id) PARTITIONS 16;

CREATE INDEX idx_sbom_documents_listing
    ON sbom_documents (tenant_id, application, environment, format, imported_at DESC, id DESC);

CREATE INDEX idx_sbom_documents_release
    ON sbom_documents (tenant_id, application, release, environment, document_version DESC);

CREATE INDEX idx_sbom_vulnerabilities_listing
    ON sbom_vulnerabilities (tenant_id, known_exploited, cvss_score DESC, cve_id, id);

CREATE INDEX idx_sbom_exposure_listing
    ON sbom_exposure_contexts (tenant_id, application, environment, updated_at DESC);

CREATE INDEX idx_sbom_findings_listing
    ON sbom_risk_findings (
        tenant_id, document_id, priority, status, contextual_score DESC, generated_at DESC, id DESC
    );

CREATE INDEX idx_sbom_findings_cve
    ON sbom_risk_findings (tenant_id, cve_id, contextual_score DESC);

CREATE INDEX idx_sbom_comparisons_listing
    ON sbom_comparisons (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_sbom_event_outbox_pending
    ON sbom_event_outbox (tenant_id, occurred_at, id);

CREATE INDEX idx_audit_events_sbom
    ON audit_events (tenant_id, target_type, target_id, created_at DESC);
