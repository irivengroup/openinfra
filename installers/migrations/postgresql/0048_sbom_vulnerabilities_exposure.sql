-- OpenInfra v0.29.99 - P16 / EPIC-1605 SBOM, vulnerabilities and contextual exposure
BEGIN;

CREATE TABLE IF NOT EXISTS sbom_documents (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    application text NOT NULL,
    release text NOT NULL,
    environment text NOT NULL,
    format text NOT NULL,
    source_hash char(64) NOT NULL,
    fingerprint char(64) NOT NULL,
    document_version integer NOT NULL,
    component_count integer NOT NULL,
    imported_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, fingerprint),
    CONSTRAINT sbom_document_format_valid CHECK (format IN ('cyclonedx','spdx')),
    CONSTRAINT sbom_document_hash_valid CHECK (source_hash ~ '^[a-f0-9]{64}$'),
    CONSTRAINT sbom_document_fingerprint_valid CHECK (fingerprint ~ '^[a-f0-9]{64}$'),
    CONSTRAINT sbom_document_version_valid CHECK (document_version > 0),
    CONSTRAINT sbom_document_component_count_valid CHECK (component_count > 0),
    CONSTRAINT sbom_document_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS sbom_vulnerabilities (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cve_id text NOT NULL,
    identity_key text NOT NULL,
    cvss_score numeric(3,1) NOT NULL,
    known_exploited boolean NOT NULL,
    imported_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, identity_key),
    CONSTRAINT sbom_vulnerability_cve_valid CHECK (cve_id ~ '^CVE-[0-9]{4}-[0-9]{4,19}$'),
    CONSTRAINT sbom_vulnerability_cvss_valid CHECK (cvss_score >= 0 AND cvss_score <= 10),
    CONSTRAINT sbom_vulnerability_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS sbom_exposure_contexts (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    application text NOT NULL,
    environment text NOT NULL,
    internet_exposed boolean NOT NULL,
    flow_exposed boolean NOT NULL,
    business_criticality smallint NOT NULL,
    updated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, application, environment),
    CONSTRAINT sbom_exposure_criticality_valid CHECK (business_criticality BETWEEN 1 AND 5),
    CONSTRAINT sbom_exposure_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS sbom_risk_findings (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id uuid NOT NULL,
    cve_id text NOT NULL,
    priority text NOT NULL,
    status text NOT NULL,
    contextual_score numeric(3,1) NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT sbom_finding_priority_valid CHECK (priority IN ('low','medium','high','critical')),
    CONSTRAINT sbom_finding_status_valid CHECK (status IN ('open','accepted','mitigated','false-positive')),
    CONSTRAINT sbom_finding_score_valid CHECK (contextual_score >= 0 AND contextual_score <= 10),
    CONSTRAINT sbom_finding_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS sbom_comparisons (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    base_document_id uuid NOT NULL,
    target_document_id uuid NOT NULL,
    input_digest char(64) NOT NULL,
    generated_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, input_digest),
    CONSTRAINT sbom_comparison_documents_distinct CHECK (base_document_id <> target_document_id),
    CONSTRAINT sbom_comparison_digest_valid CHECK (input_digest ~ '^[a-f0-9]{64}$'),
    CONSTRAINT sbom_comparison_payload_object CHECK (jsonb_typeof(payload) = 'object')
) PARTITION BY HASH (tenant_id);

CREATE TABLE IF NOT EXISTS sbom_event_outbox (
    id uuid NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    aggregate_id uuid NOT NULL,
    event_name text NOT NULL,
    payload jsonb NOT NULL,
    occurred_at timestamptz NOT NULL,
    published_at timestamptz,
    attempt_count integer NOT NULL DEFAULT 0,
    last_error text,
    PRIMARY KEY (tenant_id, id),
    CONSTRAINT sbom_event_name_valid CHECK (event_name ~ '^[a-z][a-z0-9_.-]{2,120}$'),
    CONSTRAINT sbom_event_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT sbom_event_attempt_count_valid CHECK (attempt_count >= 0)
) PARTITION BY HASH (tenant_id);

DO $partitioning$
DECLARE
    table_name text;
    partition_index integer;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'sbom_documents',
        'sbom_vulnerabilities',
        'sbom_exposure_contexts',
        'sbom_risk_findings',
        'sbom_comparisons',
        'sbom_event_outbox'
    ]
    LOOP
        FOR partition_index IN 0..15 LOOP
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
                table_name || '_p' || lpad(partition_index::text, 2, '0'),
                table_name,
                partition_index
            );
        END LOOP;
    END LOOP;
END
$partitioning$;

CREATE INDEX IF NOT EXISTS idx_sbom_documents_listing
    ON sbom_documents (tenant_id, application, environment, format, imported_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_sbom_documents_release
    ON sbom_documents (tenant_id, application, release, environment, document_version DESC);
CREATE INDEX IF NOT EXISTS idx_sbom_documents_payload
    ON sbom_documents USING gin (payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_sbom_vulnerabilities_listing
    ON sbom_vulnerabilities (tenant_id, known_exploited, cvss_score DESC, cve_id, id);
CREATE INDEX IF NOT EXISTS idx_sbom_vulnerabilities_payload
    ON sbom_vulnerabilities USING gin (payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_sbom_exposure_listing
    ON sbom_exposure_contexts (tenant_id, application, environment, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sbom_findings_listing
    ON sbom_risk_findings (
        tenant_id, document_id, priority, status, contextual_score DESC, generated_at DESC, id DESC
    );
CREATE INDEX IF NOT EXISTS idx_sbom_findings_cve
    ON sbom_risk_findings (tenant_id, cve_id, contextual_score DESC);
CREATE INDEX IF NOT EXISTS idx_sbom_comparisons_listing
    ON sbom_comparisons (tenant_id, generated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_sbom_event_outbox_pending
    ON sbom_event_outbox (tenant_id, occurred_at, id) WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sbom_event_outbox_occurred_brin
    ON sbom_event_outbox USING brin (occurred_at) WITH (pages_per_range = 64);
CREATE INDEX IF NOT EXISTS idx_audit_events_sbom
    ON audit_events (tenant_id, target_type, target_id, created_at DESC)
    WHERE target_type IN (
        'sbom_document','sbom_vulnerability','sbom_exposure','sbom_comparison'
    );

COMMIT;
