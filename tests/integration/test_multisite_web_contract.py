from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    ROOT / "web/src/main.jsx",
    ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js",
)


def test_multisite_is_grouped_under_dcim_with_api_parity() -> None:
    operations = (
        "multisite-grant-upsert",
        "multisite-grant-revoke",
        "multisite-grants",
        "multisite-sites",
        "multisite-report-generate",
        "multisite-reports",
        "multisite-report-get",
        "multisite-dr-plan-configure",
        "multisite-dr-plan-disable",
        "multisite-dr-plans",
        "multisite-dr-plan-get",
        "multisite-dr-drill-execute",
        "multisite-dr-drills",
        "multisite-dr-drill-get",
        "multisite-route-configure",
        "multisite-route-disable",
        "multisite-routes",
        "multisite-route-get",
        "multisite-job-route",
    )
    routes = (
        "/v1/multisite/site-access/grants/upsert",
        "/v1/multisite/site-access/grants/revoke",
        "/v1/multisite/site-access/grants",
        "/v1/multisite/sites",
        "/v1/multisite/reports/generate",
        "/v1/multisite/reports",
        "/v1/multisite/reports/get",
        "/v1/multisite/disaster-recovery/plans/configure",
        "/v1/multisite/disaster-recovery/plans/disable",
        "/v1/multisite/disaster-recovery/plans",
        "/v1/multisite/disaster-recovery/plans/get",
        "/v1/multisite/disaster-recovery/drills/execute",
        "/v1/multisite/disaster-recovery/drills",
        "/v1/multisite/disaster-recovery/drills/get",
        "/v1/multisite/regional-discovery/routes/configure",
        "/v1/multisite/regional-discovery/routes/disable",
        "/v1/multisite/regional-discovery/routes",
        "/v1/multisite/regional-discovery/routes/get",
        "/v1/multisite/regional-discovery/jobs/route",
    )
    for path in SOURCES:
        source = path.read_text(encoding="utf-8")
        for operation in operations:
            assert operation in source
        for route in routes:
            assert route in source
        assert "Pilotage multisite" in source
        assert "id: 'multisite'" not in source and 'id: "multisite"' not in source


def test_multisite_static_forms_use_typed_controls_and_governed_regional_routes() -> None:
    source = SOURCES[1].read_text(encoding="utf-8")
    assert 'name: "access_level"' in source and 'type: "select"' in source
    assert 'name: "site_codes"' in source and 'type: "json"' in source
    assert 'name: "active_only"' in source and 'type: "boolean"' in source
    for field in ("region_code", "site_code", "vrf_code", "collector_id", "job_type"):
        assert f'name: "{field}"' in source
    assert 'name: "max_attempts"' in source and 'type: "number"' in source
    assert "/v1/multisite/agents" not in source
    assert "/v1/multisite/regions" not in source


def test_multisite_dr_forms_are_typed_and_never_expose_automatic_promotion() -> None:
    for path in SOURCES:
        source = path.read_text(encoding="utf-8")
        for field in (
            "replication_mode",
            "rpo_seconds",
            "rto_seconds",
            "max_backup_age_seconds",
            "replication_lag_seconds",
            "backup_age_seconds",
            "measured_rto_seconds",
            "restore_verified",
            "recovery_available",
            "vip_reachable",
            "operator_confirmed",
        ):
            assert field in source
        assert "automatic_promotion" not in source
