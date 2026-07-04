from __future__ import annotations

import pytest

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.data_import import (
    ImportCandidate,
    ImportFieldMapping,
    ImportFormat,
    ImportJobStatus,
    ImportMapping,
    ImportReport,
    ImportRowImpact,
    ImportRowIssue,
)


def _mapping() -> ImportMapping:
    return ImportMapping.from_dict(
        {"key": "Key", "kind": "Kind", "display_name": "Name", "source": "Source"}
    )


class TestDataImportDomain:
    def test_mapping_and_report_serialization(self) -> None:
        mapping = _mapping()
        impact = ImportRowImpact.create(1, "create", "device/a", "device")
        issue = ImportRowIssue.create(2, "key", "missing value", Severity.ERROR)
        report = ImportReport.create(
            tenant_id=TenantId.from_value("default"),
            import_format=ImportFormat.from_value(".csv"),
            dry_run=True,
            mapping=mapping,
            total_rows=2,
            impacts=(impact,),
            dlq=(issue,),
            status=ImportJobStatus.FAILED,
            job_id=EntityId.from_value("00000000-0000-0000-0000-000000000001"),
        )

        assert mapping.source_fields() == ("Name", "Key", "Kind", "Source")
        assert ImportFieldMapping.create("key", "Key").as_dict() == {
            "target_field": "key",
            "source_field": "Key",
        }
        assert report.as_dict()["invalid_rows"] == 1
        assert report.as_dict()["dlq"][0]["message"] == "missing value"

    def test_candidate_normalizes_tags_and_validates_source(self) -> None:
        candidate = ImportCandidate.create(
            row_number=1,
            key="Device/SRV-001",
            kind="DEVICE",
            display_name="  Server   1 ",
            source="CSV_IMPORT",
            tags=(" Prod ", "Linux"),
            attributes={"serial": "abc"},
        )

        assert candidate.key == "device/srv-001"
        assert candidate.display_name == "Server 1"
        assert candidate.tags == ("prod", "linux")

    @pytest.mark.parametrize(
        ("factory", "message"),
        [
            (lambda: ImportFormat.from_value("yaml"), "format"),
            (lambda: ImportFieldMapping.create("bad field", "x"), "target field"),
            (lambda: ImportFieldMapping.create("key", " "), "source field"),
            (lambda: ImportMapping.from_json("[1]"), "JSON object"),
            (lambda: ImportMapping.from_json("{"), "valid JSON"),
            (lambda: ImportMapping.from_dict({"display_name": "a", "key": "b"}), "kind"),
            (lambda: ImportRowIssue.create(0, "row", "bad"), "row number"),
            (lambda: ImportRowIssue.create(1, "row", " "), "message"),
            (lambda: ImportRowImpact.create(1, "merge", "device/a", "device"), "action"),
            (lambda: ImportRowImpact.create(0, "create", "device/a", "device"), "row number"),
            (lambda: ImportRowImpact.create(1, "create", " ", "device"), "object key"),
            (
                lambda: ImportCandidate.create(0, "device/a", "device", "A", "manual", (), {}),
                "row number",
            ),
            (
                lambda: ImportReport.create(
                    TenantId.from_value("default"),
                    ImportFormat.CSV,
                    True,
                    _mapping(),
                    -1,
                    (),
                    (),
                    ImportJobStatus.FAILED,
                ),
                "total rows",
            ),
            (
                lambda: ImportReport.create(
                    TenantId.from_value("default"),
                    ImportFormat.CSV,
                    True,
                    _mapping(),
                    0,
                    (),
                    (ImportRowIssue.create(1, "row", "bad"),),
                    ImportJobStatus.FAILED,
                ),
                "exceeds total",
            ),
            (
                lambda: ImportReport.create(
                    TenantId.from_value("default"),
                    ImportFormat.CSV,
                    True,
                    _mapping(),
                    1,
                    (),
                    (ImportRowIssue.create(1, "row", "bad"),),
                    ImportJobStatus.VALIDATED,
                ),
                "cannot contain invalid rows",
            ),
        ],
    )
    def test_validation_errors_are_explicit(self, factory: object, message: str) -> None:
        with pytest.raises(ValidationError, match=message):
            factory()
