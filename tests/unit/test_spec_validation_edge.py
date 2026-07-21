from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.spec_validation import ContractualSpecValidator


def test_contractual_spec_validator_reports_all_invalid_document_edges(tmp_path: Path) -> None:
    validator = ContractualSpecValidator()
    with pytest.raises(ValidationError, match="missing required spec file"):
        validator.assert_valid(tmp_path)

    (tmp_path / "03-Technique").mkdir()
    (tmp_path / "04-Donnees").mkdir()
    (tmp_path / "08-RFC-ADR").mkdir()
    (tmp_path / "11-Matrices").mkdir()
    (tmp_path / "00-README.md").write_text("invalid", encoding="utf-8")
    (tmp_path / "03-Technique/02-PostgreSQL-Cluster.md").write_text("cluster", encoding="utf-8")
    (tmp_path / "04-Donnees/Partitions.md").write_text("partitions", encoding="utf-8")
    (tmp_path / "08-RFC-ADR/ADR-0005-No-Integrated-ITSM.md").write_text(
        "ITSM intégré", encoding="utf-8"
    )
    (tmp_path / "11-Matrices/Exigences.csv").write_text("id,name\n", encoding="utf-8")
    (tmp_path / "11-Matrices/Tests.csv").write_text("id,name\n", encoding="utf-8")
    (tmp_path / "VERSION").write_text("9.9.9\n", encoding="utf-8")

    report = validator.validate(tmp_path)
    assert report.valid is False
    assert "unsupported specification version" in report.as_text()
    assert "csv file is empty" in report.as_text()
    assert "does not explicitly exclude" in report.as_text()


def test_contractual_spec_validator_keeps_cdc_410_compatibility(tmp_path: Path) -> None:
    required_files = {
        "00-README.md": "OpenInfra CDC 4.10",
        "03-Technique/02-PostgreSQL-Cluster.md": "cluster",
        "04-Donnees/Partitions.md": "partitions",
        "08-RFC-ADR/ADR-0005-No-Integrated-ITSM.md": "Aucune ITSM intégrée",
        "11-Matrices/Exigences.csv": "id,name\nREQ-1,Requirement\n",
        "11-Matrices/Tests.csv": "id,name\nTST-1,Test\n",
        "VERSION": "4.10.0\n",
    }
    for relative, content in required_files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    report = ContractualSpecValidator().assert_valid(tmp_path)

    assert report.version == "4.10.0"
    assert report.requirements == 1
    assert report.tests == 1
