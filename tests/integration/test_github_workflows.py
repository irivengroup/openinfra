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
