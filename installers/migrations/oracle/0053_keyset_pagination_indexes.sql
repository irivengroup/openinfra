-- Generated deterministically from installers/migrations/postgresql/0053_keyset_pagination_indexes.sql.
-- Source SHA-256: d4bbd48196f8975b75afab37bd7f631169dac46417adec12cc37fa1689180ad3
-- Do not edit manually; run scripts/generate_oracle_migrations.py.

CREATE INDEX idx_api_tokens_cursor
    ON api_tokens (tenant_id, created_at ASC, id ASC);

CREATE INDEX idx_access_policy_rules_cursor
    ON access_policy_rules (tenant_id, name ASC, id ASC);

CREATE INDEX idx_source_governance_rules_cursor
    ON source_governance_rules (tenant_id, priority DESC, name ASC, id ASC);

CREATE INDEX idx_source_objects_cursor
    ON source_objects (tenant_id, object_key ASC);

CREATE INDEX idx_source_relations_cursor
    ON source_relations (tenant_id, created_at DESC, id DESC);

CREATE INDEX idx_field_operation_sheets_cursor
    ON field_operation_sheets (tenant_id, updated_at DESC, id DESC);

CREATE INDEX idx_offline_sync_packages_cursor
    ON offline_sync_packages (tenant_id, created_at DESC, id DESC);

CREATE INDEX idx_simulation_scenarios_cursor
    ON simulation_scenarios (tenant_id, updated_at DESC, id DESC);

CREATE INDEX idx_simulation_reports_cursor
    ON simulation_impact_reports (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_simulation_comparisons_cursor
    ON simulation_scenario_comparisons (tenant_id, created_at DESC, id DESC);

CREATE INDEX idx_finops_allocation_rules_cursor
    ON finops_allocation_rules (tenant_id, priority ASC, id ASC);

CREATE INDEX idx_finops_import_jobs_cursor
    ON finops_import_jobs (tenant_id, submitted_at DESC, id DESC);

CREATE INDEX idx_finops_cost_records_cursor
    ON finops_cost_records (tenant_id, period_start DESC, id DESC);

CREATE INDEX idx_finops_budgets_cursor
    ON finops_budgets (tenant_id, period_start DESC, id DESC);

CREATE INDEX idx_finops_periods_cursor
    ON finops_financial_periods (tenant_id, period_start DESC, id DESC);

CREATE INDEX idx_finops_anomalies_cursor
    ON finops_cost_anomalies (tenant_id, detected_at DESC, id DESC);

CREATE INDEX idx_finops_forecasts_cursor
    ON finops_forecasts (tenant_id, period_start DESC, id DESC);

CREATE INDEX idx_finops_reports_cursor
    ON finops_reports (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_greenops_sources_cursor
    ON greenops_measurement_sources (tenant_id, code ASC, id ASC);

CREATE INDEX idx_greenops_factors_cursor
    ON greenops_carbon_factors (tenant_id, period_start DESC, created_at DESC, id DESC);

CREATE INDEX idx_greenops_measurements_cursor
    ON greenops_energy_measurements (tenant_id, period_start DESC, id DESC);

CREATE INDEX idx_greenops_anomalies_cursor
    ON greenops_anomalies (tenant_id, detected_at DESC, id DESC);

CREATE INDEX idx_greenops_forecasts_cursor
    ON greenops_forecasts (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_greenops_candidates_cursor
    ON greenops_consolidation_candidates (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_greenops_scores_cursor
    ON greenops_scores (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_greenops_reports_cursor
    ON greenops_reports (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_sbom_documents_cursor
    ON sbom_documents (tenant_id, imported_at DESC, id DESC);

CREATE INDEX idx_sbom_vulnerabilities_cursor
    ON sbom_vulnerabilities (tenant_id, cvss_score DESC, cve_id ASC, id ASC);

CREATE INDEX idx_sbom_contexts_cursor
    ON sbom_exposure_contexts (tenant_id, application ASC, environment ASC, id ASC);

CREATE INDEX idx_sbom_findings_cursor
    ON sbom_risk_findings (tenant_id, contextual_score DESC, generated_at DESC, id DESC);

CREATE INDEX idx_sbom_comparisons_cursor
    ON sbom_comparisons (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_rag_documents_cursor
    ON rag_documents (tenant_id, indexed_at DESC, id DESC);

CREATE INDEX idx_rag_answers_cursor
    ON rag_answers (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_rag_jobs_cursor
    ON rag_jobs (tenant_id, created_at DESC, id DESC);

CREATE INDEX idx_multisite_grants_cursor
    ON multisite_site_access_grants (tenant_id, subject ASC, site_code ASC, id ASC);

CREATE INDEX idx_multisite_reports_cursor
    ON multisite_reports (tenant_id, generated_at DESC, id DESC);

CREATE INDEX idx_multisite_routes_cursor
    ON multisite_regional_discovery_routes
       (tenant_id, region_code ASC, site_code ASC, vrf_code ASC, id ASC);

CREATE INDEX idx_multisite_dr_plans_cursor
    ON multisite_dr_plans (tenant_id, primary_site_code ASC, recovery_site_code ASC, id ASC);

CREATE INDEX idx_multisite_dr_drills_cursor
    ON multisite_dr_drills (tenant_id, executed_at DESC, id DESC);

CREATE INDEX idx_certificate_inventory_cursor
    ON certificate_inventory
       (tenant_id, not_after ASC, subject_dn ASC, fingerprint_sha256 ASC);

CREATE INDEX idx_certificate_endpoints_cursor
    ON certificate_endpoint_observations (tenant_id, observed_at DESC, id DESC);

CREATE INDEX idx_flow_declarations_cursor
    ON flow_declarations (tenant_id, code ASC, id ASC);

CREATE INDEX idx_flow_observations_cursor
    ON flow_observations (tenant_id, last_seen DESC, id DESC);

CREATE INDEX idx_network_baselines_cursor
    ON network_config_baselines (tenant_id, code ASC, id ASC);

CREATE INDEX idx_network_observations_cursor
    ON network_config_observations
       (tenant_id, observed_at DESC, received_at DESC, id DESC);

CREATE INDEX idx_audit_events_cursor
    ON audit_events (tenant_id, created_at DESC, id DESC);
