from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestGitHubWorkflows:
    def test_javascript_actions_use_node24_compatible_major_versions(self) -> None:
        workflows = tuple(sorted((PROJECT_ROOT / ".github/workflows").glob("*.yml")))
        assert workflows
        content = "\n".join(path.read_text(encoding="utf-8") for path in workflows)

        assert "actions/checkout@v4" not in content
        assert "actions/setup-node@v4" not in content
        assert "actions/setup-python@v5" not in content
        assert "actions/checkout@v6" in content
        assert "actions/setup-node@v6" in content
        assert "actions/setup-python@v6" in content
        assert "actions/dependency-review-action@v5" in content
        assert "github/codeql-action/init@v4" in content
        assert "github/codeql-action/analyze@v4" in content

    def test_dcim_smokes_reuse_canonical_floor_codes(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        physical_start = workflow.index("      - name: Smoke JSON DCIM physical model")
        physical_end = workflow.index(
            "      - name: Smoke JSON DCIM field operations", physical_start
        )
        physical = workflow[physical_start:physical_end]
        cabling_start = workflow.index(
            "      - name: Smoke JSON DCIM cabling and energy foundation"
        )
        cabling_end = workflow.index("      - name: Native runtime asset smoke", cabling_start)
        cabling = workflow[cabling_start:cabling_end]

        for section in (physical, cabling):
            assert '> "$tmpdir/room-definition.json"' in section
            assert 'floor_code="$(python -c' in section
            assert '--floor "$floor_code"' in section
            assert "--floor F01" not in section

    def test_built_wheel_is_installed_and_smoked_from_target_directory(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        assert "- name: Smoke installed wheel layout" in workflow
        assert "python -m pip install --no-deps --target" in workflow
        assert 'PYTHONPATH="$target" python scripts/smoke_installed_wheel.py' in workflow
        smoke = (PROJECT_ROOT / "scripts/smoke_installed_wheel.py").read_text(encoding="utf-8")
        assert "OpenApiDocumentProvider().read_yaml()" in smoke
        assert "EXPECTED_MIGRATION_COUNT = 54" in smoke
        assert "EXPECTED_DATA_PLANE_ROUTES" in smoke
        assert "/api/v1/database/routing" in smoke
        assert "EXPECTED_NETWORK_CONFIG_ROUTES" in smoke
        assert "EXPECTED_FIELD_OPERATION_ROUTES" in smoke
        assert "EXPECTED_SIMULATION_ROUTES" in smoke
        assert "EXPECTED_GREENOPS_ROUTES" in smoke
        assert "EXPECTED_SBOM_ROUTES" in smoke
        assert 'EXPECTED_LAST_MIGRATION = "0054_async_outbox_workers.sql"' in smoke
        for route in (
            "/api/v1/graph/traverse",
            "/api/v1/graph/impact",
            "/api/v1/graph/path",
        ):
            assert route in smoke

    def test_rag_is_a_blocking_ci_regression_gate(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        assert (
            "- name: Governed RAG permissions, citations and resumable jobs regression" in workflow
        )
        for test_path in (
            "tests/unit/test_rag_domain.py",
            "tests/integration/test_rag_services.py",
            "tests/integration/test_rag_cli.py",
            "tests/integration/test_rag_http_api.py",
            "tests/integration/test_rag_migration.py",
            "tests/integration/test_rag_postgresql_repository.py",
            "tests/integration/test_rag_web_contract.py",
        ):
            assert test_path in workflow

    def test_dependency_graph_volumetric_benchmark_is_a_blocking_ci_gate(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        assert "- name: Dependency graph volumetric benchmark" in workflow
        assert "if: matrix.python-version == '3.13'" in workflow
        assert "python -m openinfra.quality.dependency_graph_benchmark" in workflow
        assert "--nodes 5000" in workflow
        assert "--spof-hubs 100" in workflow
        assert "dependency-graph-benchmark.json" in workflow
        assert "GITHUB_STEP_SUMMARY" in workflow

    def test_greenops_is_a_blocking_ci_regression_gate(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        assert "- name: GreenOps energy, carbon and capacity regression" in workflow
        for test_path in (
            "tests/unit/test_greenops_domain.py",
            "tests/unit/test_greenops_edge_cases.py",
            "tests/integration/test_greenops_services.py",
            "tests/integration/test_greenops_cli.py",
            "tests/integration/test_greenops_http_api.py",
            "tests/integration/test_greenops_migration.py",
            "tests/integration/test_greenops_postgresql_repository.py",
            "tests/integration/test_greenops_web_contract.py",
        ):
            assert test_path in workflow

    def test_sbom_is_a_blocking_ci_regression_gate(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        assert "- name: SBOM vulnerability and contextual exposure regression" in workflow
        for test_path in (
            "tests/unit/test_sbom_domain.py",
            "tests/unit/test_sbom_edge_cases.py",
            "tests/integration/test_sbom_services.py",
            "tests/integration/test_sbom_cli.py",
            "tests/integration/test_sbom_http_api.py",
            "tests/integration/test_sbom_migration.py",
            "tests/integration/test_sbom_postgresql_repository.py",
            "tests/integration/test_sbom_web_contract.py",
        ):
            assert test_path in workflow

    def test_multisite_is_a_blocking_ci_regression_gate(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        assert (
            "- name: Pro centralized multisite RBAC and consolidated reports regression" in workflow
        )
        smoke = (PROJECT_ROOT / "scripts/smoke_installed_wheel.py").read_text(encoding="utf-8")
        assert "EXPECTED_MULTISITE_ROUTES" in smoke
        for test_path in (
            "tests/unit/test_multisite_domain.py",
            "tests/integration/test_multisite_services.py",
            "tests/integration/test_multisite_cli.py",
            "tests/integration/test_multisite_http_api.py",
            "tests/integration/test_multisite_migration.py",
            "tests/integration/test_multisite_postgresql_repository.py",
            "tests/integration/test_multisite_web_contract.py",
            "tests/integration/test_enterprise_multisite_discovery_routing.py",
            "tests/integration/test_enterprise_multisite_http_api.py",
        ):
            assert test_path in workflow
        assert "Enterprise regional discovery routing regression" in workflow
        assert (
            "- name: Multisite disaster recovery plans and site-loss drills regression" in workflow
        )
        for test_path in (
            "tests/unit/test_multisite_disaster_recovery_domain.py",
            "tests/integration/test_multisite_disaster_recovery.py",
            "tests/integration/test_multisite_disaster_recovery_cli.py",
            "tests/integration/test_multisite_disaster_recovery_http_api.py",
        ):
            assert test_path in workflow


def test_enterprise_capacity_workflow_covers_all_epic_1801_workloads() -> None:
    workflow = (PROJECT_ROOT / ".github/workflows/enterprise-capacity.yml").read_text(
        encoding="utf-8"
    )
    assert "OPENINFRA_CAPACITY_BENCHMARK_PATHS_JSON" in workflow
    assert "python scripts/run_enterprise_benchmark_suite.py" in workflow
    assert "--benchmarks build/capacity/benchmarks" in workflow
    profile = (PROJECT_ROOT / "docs/operations/enterprise-capacity-profile.json").read_text(
        encoding="utf-8"
    )
    for workload in ("api", "ipam", "imports", "discovery", "database", "graph"):
        assert f'"{workload}"' in profile
