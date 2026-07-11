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
