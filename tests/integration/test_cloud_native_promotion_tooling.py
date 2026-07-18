from __future__ import annotations

import json
from pathlib import Path

from scripts.assemble_cloud_native_promotion_evidence import CloudNativePromotionAssembler
from scripts.validate_cloud_native_promotion import CloudNativePromotionProjectValidator

from openinfra import __version__
from openinfra.quality.cloud_native_promotion import CloudNativePromotionPolicy

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_epic_2106_project_contract_is_complete() -> None:
    report = CloudNativePromotionProjectValidator(PROJECT_ROOT).validate()

    assert report["complete"] is True
    assert report["gate_id"] == "GATE-10"
    assert report["required_evidence_count"] == 7
    assert report["max_resources_per_snapshot"] == 50_000
    assert report["migration_count"] == 58


def test_gate_10_is_integrated_into_ci_quality_packaging_and_wheel_smoke() -> None:
    ci = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow = (PROJECT_ROOT / ".github/workflows/cloud-native-promotion.yml").read_text(
        encoding="utf-8"
    )
    quality_gate = (PROJECT_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
    verifier = (PROJECT_ROOT / "scripts/verify_artifact.py").read_text(encoding="utf-8")
    smoke = (PROJECT_ROOT / "scripts/smoke_installed_wheel.py").read_text(encoding="utf-8")
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "validate_cloud_native_promotion.py --project-root . --enforce" in ci
    assert "tests/unit/test_cloud_native_promotion.py" in ci
    assert "--resources 50000" in workflow
    assert '"scripts/validate_cloud_native_promotion.py"' in quality_gate
    assert '"scripts/validate_cloud_native_promotion.py"' in verifier
    assert "CloudNativePromotionPolicy" in smoke
    assert "CLOUD_NATIVE_PROMOTION.md" in pyproject
    assert '"docs/release" = "openinfra/docs/release"' in pyproject


def test_assembler_copies_all_seven_reports_and_pins_hashes(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    sources: dict[str, Path] = {}
    epic_by_id = {
        "epic-2101-topology": "EPIC-2101",
        "epic-2102-exposure": "EPIC-2102",
        "epic-2103-security": "EPIC-2103",
        "epic-2104-gitops": "EPIC-2104",
        "epic-2105-capacity": "EPIC-2105",
        "epic-2106-runtime": "EPIC-2106",
        "epic-2106-contract": "EPIC-2106",
    }
    for identifier, report_kind in CloudNativePromotionPolicy.EXPECTED_EVIDENCE.items():
        path = source_root / f"{identifier}.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "report_kind": report_kind,
                    "release_version": __version__,
                    "generated_at": "2026-07-16T12:00:00+00:00",
                    "phase": "P21",
                    "epic": epic_by_id[identifier],
                    "release": "REL-11",
                }
            ),
            encoding="utf-8",
        )
        sources[identifier] = path

    evidence_root = tmp_path / "evidence"
    manifest = CloudNativePromotionAssembler.assemble(
        candidate_id=f"openinfra-{__version__}",
        source_commit="b" * 40,
        sources=sources,
        evidence_root=evidence_root,
    )

    assert manifest["gate_id"] == "GATE-10"
    assert len(manifest["evidence"]) == 7
    assert len(list(evidence_root.glob("*.json"))) == 7
    assert all(len(item["sha256"]) == 64 for item in manifest["evidence"])
