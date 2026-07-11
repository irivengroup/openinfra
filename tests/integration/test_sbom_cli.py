from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI


def _write_sbom(path: Path, version: str) -> None:
    path.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "components": [
                    {
                        "bom-ref": f"pkg:pypi/requests@{version}",
                        "name": "requests",
                        "version": version,
                        "purl": f"pkg:pypi/requests@{version}",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_sbom_cli_complete_cycle(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "c" * 40
    app = ApplicationFactory().create_json_application(state, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "sbom-admin", ("admin",), token)
    )
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]
    ids: list[str] = []
    for release, version in (("0.29.98", "2.31.0"), ("0.29.99", "2.32.0")):
        sbom = tmp_path / f"sbom-{release}.json"
        _write_sbom(sbom, version)
        assert (
            cli.run(
                [
                    "sbom",
                    "import",
                    *common,
                    "--application",
                    "openinfra",
                    "--release",
                    release,
                    "--environment",
                    "production",
                    "--source-name",
                    "pytest",
                    "--file",
                    str(sbom),
                    "--source-uri",
                    f"https://example.invalid/{release}.json",
                ]
            )
            == 0
        )
        ids.append(str(json.loads(capsys.readouterr().out)["id"]))  # type: ignore[attr-defined]

    assert cli.run(["sbom", "documents", *common, "--application", "openinfra"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 2  # type: ignore[attr-defined]
    assert cli.run(["sbom", "document", *common, "--document-id", ids[1]]) == 0
    assert json.loads(capsys.readouterr().out)["release"] == "0.29.99"  # type: ignore[attr-defined]

    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"scanner":"pytest"}', encoding="utf-8")
    assert (
        cli.run(
            [
                "sbom",
                "vulnerability-import",
                *common,
                "--cve-id",
                "CVE-2026-12345",
                "--component-name",
                "requests",
                "--component-version",
                "2.32.0",
                "--component-purl",
                "pkg:pypi/requests@2.32.0",
                "--cvss-score",
                "8.2",
                "--known-exploited",
                "--exploit-maturity",
                "weaponized",
                "--source-name",
                "scanner-x",
                "--published-at",
                "2026-06-01T00:00:00Z",
                "--modified-at",
                "2026-07-01T00:00:00Z",
                "--reference",
                "https://example.invalid/CVE-2026-12345",
                "--metadata-file",
                str(metadata),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["cve_id"] == "CVE-2026-12345"  # type: ignore[attr-defined]
    assert cli.run(["sbom", "vulnerabilities", *common, "--known-exploited"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "sbom",
                "exposure-upsert",
                *common,
                "--application",
                "openinfra",
                "--environment",
                "production",
                "--internet-exposed",
                "--flow-exposed",
                "--business-criticality",
                "5",
                "--control",
                "waf",
                "--asset-id",
                "server-001",
                "--service-id",
                "portal",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["internet_exposed"] is True  # type: ignore[attr-defined]
    assert (
        cli.run(
            [
                "sbom",
                "exposure",
                *common,
                "--application",
                "openinfra",
                "--environment",
                "production",
            ]
        )
        == 0
    )
    capsys.readouterr()  # type: ignore[attr-defined]
    assert cli.run(["sbom", "exposures", *common]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]

    assert cli.run(["sbom", "assess", *common, "--document-id", ids[1]]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["priority"] == "critical"  # type: ignore[attr-defined]
    assert (
        cli.run(["sbom", "findings", *common, "--document-id", ids[1], "--priority", "critical"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["items"]  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "sbom",
                "compare",
                *common,
                "--base-document-id",
                ids[0],
                "--target-document-id",
                ids[1],
            ]
        )
        == 0
    )
    comparison = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    comparison_id = str(comparison["id"])
    assert comparison["summary"]["changed"] == 1
    assert cli.run(["sbom", "comparison", *common, "--comparison-id", comparison_id]) == 0
    capsys.readouterr()  # type: ignore[attr-defined]
    assert cli.run(["sbom", "comparisons", *common]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == comparison_id  # type: ignore[attr-defined]

    output = tmp_path / "risk.csv"
    assert (
        cli.run(
            [
                "sbom",
                "risk-export",
                *common,
                "--document-id",
                ids[1],
                "--format",
                "csv",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert "CVE-2026-12345" in output.read_text(encoding="utf-8")
