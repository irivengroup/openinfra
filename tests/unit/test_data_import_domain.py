from __future__ import annotations

import pytest

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.data_import import (
    BulkImportCheckpoint,
    BulkImportMetrics,
    BulkImportReport,
    ImportCandidate,
    ImportFieldMapping,
    ImportFormat,
    ImportJobStatus,
    ImportMapping,
    ImportReport,
    ImportRowImpact,
    ImportRowIssue,
    LegacyMigrationSource,
    MigrationGap,
    MigrationPlanReport,
    MigrationTemplate,
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


def test_bulk_import_report_and_checkpoint_contracts_are_serializable() -> None:
    mapping = _mapping()
    checkpoint = BulkImportCheckpoint.create(
        tenant_id=TenantId.from_value("default"),
        next_row_number=11,
        total_rows=10,
        valid_rows=9,
        invalid_rows=1,
        create_count=8,
        update_count=1,
        batches_completed=2,
        status=ImportJobStatus.FAILED,
    )
    metrics = BulkImportMetrics.create(
        batch_size=5,
        checkpoint_interval=10,
        batches_completed=2,
        copy_strategy="json-streaming-batch-checkpoint",
        resumed_from_row=6,
    )
    report = BulkImportReport.create(
        tenant_id=TenantId.from_value("default"),
        import_format=ImportFormat.CSV,
        dry_run=False,
        status=ImportJobStatus.FAILED,
        total_rows=10,
        valid_rows=9,
        invalid_rows=1,
        create_count=8,
        update_count=1,
        mapping=mapping,
        metrics=metrics,
        checkpoint=checkpoint,
        impact_sample=(ImportRowImpact.create(1, "create", "device/a", "device"),),
        dlq_sample=(ImportRowIssue.create(10, "key", "required field is empty"),),
    )

    payload = report.as_dict()

    assert payload["checkpoint"]["next_row_number"] == 11
    assert payload["metrics"]["resumed_from_row"] == 6
    assert payload["impact_sample"][0]["action"] == "create"
    assert payload["dlq_sample"][0]["field"] == "key"


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: BulkImportCheckpoint.create(
                TenantId.from_value("default"), 0, 0, 0, 0, 0, 0, 0, ImportJobStatus.QUEUED
            ),
            "next row",
        ),
        (
            lambda: BulkImportCheckpoint.create(
                TenantId.from_value("default"), 1, 2, 2, 1, 0, 0, 0, ImportJobStatus.QUEUED
            ),
            "row counters",
        ),
        (lambda: BulkImportMetrics.create(0, 1, 0, "x"), "batch size"),
        (lambda: BulkImportMetrics.create(1, 0, 0, "x"), "checkpoint interval"),
        (lambda: BulkImportMetrics.create(1, 1, -1, "x"), "batches completed"),
        (lambda: BulkImportMetrics.create(1, 1, 0, " "), "copy strategy"),
    ],
)
def test_bulk_import_validation_errors_are_explicit(factory: object, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        factory()


def test_bulk_import_additional_validation_branches() -> None:
    tenant = TenantId.from_value("default")
    mapping = _mapping()
    checkpoint = BulkImportCheckpoint.create(tenant, 2, 1, 1, 0, 1, 0, 1, ImportJobStatus.VALIDATED)
    metrics = BulkImportMetrics.create(1, 1, 1, "json")

    with pytest.raises(ValidationError, match="object kind"):
        ImportRowImpact.create(1, "create", "device/a", "unknown")
    with pytest.raises(ValidationError, match="cannot be negative"):
        BulkImportCheckpoint.create(tenant, 1, -1, 0, 0, 0, 0, 0, ImportJobStatus.QUEUED)
    with pytest.raises(ValidationError, match="impact counters"):
        BulkImportCheckpoint.create(tenant, 1, 1, 1, 0, 2, 0, 0, ImportJobStatus.QUEUED)
    with pytest.raises(ValidationError, match="resumed row"):
        BulkImportMetrics.create(1, 1, 0, "json", 0)
    with pytest.raises(ValidationError, match="cannot be negative"):
        BulkImportReport.create(
            tenant,
            ImportFormat.CSV,
            True,
            ImportJobStatus.FAILED,
            -1,
            0,
            0,
            0,
            0,
            mapping,
            metrics,
            checkpoint,
            (),
            (),
        )
    with pytest.raises(ValidationError, match="row counters"):
        BulkImportReport.create(
            tenant,
            ImportFormat.CSV,
            True,
            ImportJobStatus.FAILED,
            2,
            2,
            1,
            0,
            0,
            mapping,
            metrics,
            checkpoint,
            (),
            (),
        )
    with pytest.raises(ValidationError, match="impact counters"):
        BulkImportReport.create(
            tenant,
            ImportFormat.CSV,
            True,
            ImportJobStatus.FAILED,
            1,
            1,
            0,
            2,
            0,
            mapping,
            metrics,
            checkpoint,
            (),
            (),
        )
    other_checkpoint = BulkImportCheckpoint.create(
        tenant, 2, 1, 1, 0, 1, 0, 1, ImportJobStatus.VALIDATED
    )
    with pytest.raises(ValidationError, match="job mismatch"):
        BulkImportReport.create(
            tenant,
            ImportFormat.CSV,
            True,
            ImportJobStatus.VALIDATED,
            1,
            1,
            0,
            1,
            0,
            mapping,
            metrics,
            other_checkpoint,
            (),
            (),
            job_id=checkpoint.job_id,
        )
    with pytest.raises(ValidationError, match="tenant mismatch"):
        BulkImportReport.create(
            TenantId.from_value("other"),
            ImportFormat.CSV,
            True,
            ImportJobStatus.VALIDATED,
            1,
            1,
            0,
            1,
            0,
            mapping,
            metrics,
            checkpoint,
            (),
            (),
            job_id=checkpoint.job_id,
        )


def test_legacy_migration_template_and_plan_are_serializable() -> None:
    mapping = ImportMapping.from_dict(
        {
            "key": "name",
            "kind": "literal:device",
            "display_name": "name",
            "source": "literal:netbox_migration",
        }
    )
    template = MigrationTemplate.create(
        LegacyMigrationSource.from_value("netbox"),
        "NetBox devices",
        "1.0",
        mapping,
        ("name",),
        ("serial",),
        ("Use name as stable key.",),
    )
    import_report = ImportReport.create(
        TenantId.from_value("default"),
        ImportFormat.CSV,
        True,
        mapping,
        1,
        (ImportRowImpact.create(1, "create", "srv-1", "device"),),
        (),
        ImportJobStatus.VALIDATED,
    )
    plan = MigrationPlanReport.create(
        TenantId.from_value("default"),
        LegacyMigrationSource.NETBOX,
        ImportFormat.CSV,
        template,
        (MigrationGap.create("unmapped-source", "extra", "not mapped"),),
        import_report,
        "Run the bulk import with checkpoints.",
    )

    payload = plan.as_dict()

    assert payload["source"] == "netbox"
    assert payload["status"] == "validated"
    assert payload["gaps"][0]["category"] == "unmapped-source"
    assert payload["template"]["mapping"]["kind"] == "literal:device"


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: LegacyMigrationSource.from_value("unknown"), "migration source"),
        (
            lambda: MigrationGap.create("bad", "field", "message"),
            "category",
        ),
        (
            lambda: MigrationTemplate.create(
                LegacyMigrationSource.CSV,
                " ",
                "1.0",
                _mapping(),
                ("key",),
            ),
            "name",
        ),
        (
            lambda: MigrationTemplate.create(
                LegacyMigrationSource.CSV,
                "CSV",
                " ",
                _mapping(),
                ("key",),
            ),
            "version",
        ),
    ],
)
def test_legacy_migration_validation_errors(factory: object, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        factory()


def test_legacy_migration_plan_validation_guards() -> None:
    tenant = TenantId.from_value("default")
    other = TenantId.from_value("other")
    mapping = _mapping()
    template = MigrationTemplate.create(
        LegacyMigrationSource.CSV,
        "CSV",
        "1.0",
        mapping,
        ("key",),
    )
    dry_report = ImportReport.create(
        tenant,
        ImportFormat.CSV,
        True,
        mapping,
        0,
        (),
        (),
        ImportJobStatus.VALIDATED,
    )
    applied_report = ImportReport.create(
        tenant,
        ImportFormat.CSV,
        False,
        mapping,
        0,
        (),
        (),
        ImportJobStatus.APPLIED,
    )

    with pytest.raises(ValidationError, match="field is mandatory"):
        MigrationGap.create("unmapped-source", " ", "message")
    with pytest.raises(ValidationError, match="message is mandatory"):
        MigrationGap.create("unmapped-source", "field", " ")
    with pytest.raises(ValidationError, match="at least one source column"):
        MigrationTemplate.create(LegacyMigrationSource.CSV, "CSV", "1.0", mapping, ())
    with pytest.raises(ValidationError, match="resume strategy"):
        MigrationPlanReport.create(
            tenant, LegacyMigrationSource.CSV, ImportFormat.CSV, template, (), dry_report, " "
        )
    with pytest.raises(ValidationError, match="tenant mismatch"):
        MigrationPlanReport.create(
            other, LegacyMigrationSource.CSV, ImportFormat.CSV, template, (), dry_report, "Resume"
        )
    with pytest.raises(ValidationError, match="format mismatch"):
        MigrationPlanReport.create(
            tenant, LegacyMigrationSource.CSV, ImportFormat.JSON, template, (), dry_report, "Resume"
        )
    with pytest.raises(ValidationError, match="dry-run"):
        MigrationPlanReport.create(
            tenant,
            LegacyMigrationSource.CSV,
            ImportFormat.CSV,
            template,
            (),
            applied_report,
            "Resume",
        )
