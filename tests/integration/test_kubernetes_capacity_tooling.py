from __future__ import annotations

from pathlib import Path

from scripts.validate_kubernetes_capacity import KubernetesCapacityProjectValidator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_capacity_validator_and_release_tooling_are_integrated() -> None:
    report = KubernetesCapacityProjectValidator(PROJECT_ROOT).validate()
    assert report["complete"] is True
    assert report["epic"] == "EPIC-2105"
    assert report["max_trend_snapshots"] == 96
    assert report["max_trend_resources"] == 1_000_000
    assert report["migration_count"] == 57

    workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    quality_gate = (PROJECT_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
    verify_artifact = (PROJECT_ROOT / "scripts/verify_artifact.py").read_text(encoding="utf-8")
    smoke = (PROJECT_ROOT / "scripts/smoke_installed_wheel.py").read_text(encoding="utf-8")

    assert "scripts/validate_kubernetes_capacity.py --project-root . --enforce" in workflow
    assert '"scripts/validate_kubernetes_capacity.py"' in quality_gate
    assert '"src/openinfra/domain/kubernetes_capacity.py"' in verify_artifact
    assert '"scripts/validate_kubernetes_capacity.py"' in verify_artifact
    assert '"/api/v1/kubernetes/topologies/capacity"' in smoke
    assert '"/api/v1/kubernetes/topologies/capacity-trend"' in smoke
