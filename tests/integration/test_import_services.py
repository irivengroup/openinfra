from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.import_services import (
    BulkImportDatasetCommand,
    BulkImportRollbackCommand,
    ImportDatasetCommand,
    MigrationGuideCommand,
    MigrationTemplateCommand,
    PlanMigrationCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    GetSourceObjectCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.common import NotFoundError, TenantId, ValidationError
from openinfra.domain.data_import import BulkImportCheckpoint, ImportFormat, ImportJobStatus
from openinfra.infrastructure.import_parsers import ImportDatasetParser

_MAPPING = json.dumps(
    {
        "key": "asset_key",
        "kind": "kind",
        "display_name": "name",
        "source": "source",
        "tags": "tags",
        "attributes.serial": "serial",
        "attributes.critical": "critical",
    }
)


def _bootstrap(app: Any) -> str:
    token = "i" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="import-admin",
            roles=("rsot:operator", "audit:reader"),
            token=token,
        )
    )
    return token


class TestGenericImportService:
    def test_csv_dry_run_returns_impact_without_mutating_sot(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        csv_file = tmp_path / "devices.csv"
        csv_file.write_text(
            "asset_key,kind,name,source,tags,serial,critical\n"
            "device/srv-101,device,Server 101,csv_import,prod;linux,SN101,true\n",
            encoding="utf-8",
        )

        report = app.import_service.import_dataset(
            ImportDatasetCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                file_path=csv_file,
                format="csv",
                mapping_json=_MAPPING,
                dry_run=True,
            )
        )

        assert report.status.value == "validated"
        assert report.total_rows == 1
        assert report.impacts[0].action == "create"
        with pytest.raises(ValidationError, match="import job not found"):
            app.import_service.get_report("default", "missing")
        persisted = app.import_service.get_report("default", report.job_id.value)
        assert persisted.as_dict()["create_count"] == 1
        with pytest.raises(NotFoundError, match="source object not found"):
            app.source_of_truth_service.get_object(
                GetSourceObjectCommand("default", token, "device/srv-101")
            )

    def test_csv_apply_is_atomic_when_any_row_is_invalid(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        csv_file = tmp_path / "devices-invalid.csv"
        csv_file.write_text(
            "asset_key,kind,name,source,tags,serial,critical\n"
            "device/srv-201,device,Server 201,csv_import,prod,SN201,true\n"
            ",device,Missing Key,csv_import,prod,SN202,false\n",
            encoding="utf-8",
        )

        report = app.import_service.import_dataset(
            ImportDatasetCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                file_path=csv_file,
                format="csv",
                mapping_json=_MAPPING,
                dry_run=False,
            )
        )

        assert report.status.value == "failed"
        assert report.invalid_rows == 1
        assert report.dlq[0].row_number == 2
        with pytest.raises(NotFoundError, match="source object not found"):
            app.source_of_truth_service.get_object(
                GetSourceObjectCommand("default", token, "device/srv-201")
            )

    def test_json_apply_creates_and_updates_sot_objects(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        json_file = tmp_path / "devices.json"
        json_file.write_text(
            json.dumps(
                {
                    "rows": [
                        {
                            "asset_key": "device/srv-301",
                            "kind": "device",
                            "name": "Server 301",
                            "source": "json_import",
                            "tags": "prod,linux",
                            "serial": "SN301",
                            "critical": "false",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        first = app.import_service.import_dataset(
            ImportDatasetCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                file_path=json_file,
                format="json",
                mapping_json=_MAPPING,
                dry_run=False,
            )
        )
        second = app.import_service.import_dataset(
            ImportDatasetCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                file_path=json_file,
                format="json",
                mapping_json=_MAPPING,
                dry_run=False,
            )
        )
        current = app.source_of_truth_service.get_object(
            GetSourceObjectCommand("default", token, "device/srv-301")
        )

        assert first.impacts[0].action == "create"
        assert second.impacts[0].action == "update"
        assert current["attributes"]["serial"] == "SN301"
        assert current["version"] == 2


class TestImportDatasetParser:
    def test_xlsx_parser_reads_first_worksheet(self, tmp_path: Path) -> None:
        xlsx_file = tmp_path / "devices.xlsx"
        _write_minimal_xlsx(xlsx_file)

        rows = ImportDatasetParser().parse(xlsx_file, ImportFormat.XLSX)

        assert rows == (
            {
                "asset_key": "device/srv-401",
                "kind": "device",
                "name": "Server 401",
            },
        )


def _write_minimal_xlsx(path: Path) -> None:
    worksheet = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <sheetData>
    <row r=\"1\">
      <c r=\"A1\" t=\"inlineStr\"><is><t>asset_key</t></is></c>
      <c r=\"B1\" t=\"inlineStr\"><is><t>kind</t></is></c>
      <c r=\"C1\" t=\"inlineStr\"><is><t>name</t></is></c>
    </row>
    <row r=\"2\">
      <c r=\"A2\" t=\"inlineStr\"><is><t>device/srv-401</t></is></c>
      <c r=\"B2\" t=\"inlineStr\"><is><t>device</t></is></c>
      <c r=\"C2\" t=\"inlineStr\"><is><t>Server 401</t></is></c>
    </row>
  </sheetData>
</worksheet>
"""
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr("xl/worksheets/sheet1.xml", worksheet)


def test_import_parser_enforces_format_specific_size_and_xlsx_archive_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = ImportDatasetParser()
    csv_file = tmp_path / "oversized.csv"
    csv_file.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValidationError, match="1 MiB limit"):
        tuple(parser.iter_rows(csv_file, ImportFormat.CSV, max_bytes=1024 * 1024))

    workbook = tmp_path / "unsafe.xlsx"
    with zipfile.ZipFile(workbook, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", "<worksheet />")
        archive.writestr("extra.xml", "<extra />")
    monkeypatch.setattr(parser, "_MAX_XLSX_ENTRIES", 1)
    with pytest.raises(ValidationError, match="too many entries"):
        tuple(parser.iter_rows(workbook, ImportFormat.XLSX))


def test_import_parser_rejects_oversized_xlsx_xml_before_decompression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = ImportDatasetParser()
    workbook = tmp_path / "oversized-sheet.xlsx"
    with zipfile.ZipFile(workbook, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", "<worksheet>oversized</worksheet>")
    monkeypatch.setattr(parser, "_MAX_XLSX_XML_BYTES", 8)

    with pytest.raises(ValidationError, match="worksheet exceeds"):
        tuple(parser.iter_rows(workbook, ImportFormat.XLSX))


def test_import_service_rejects_limits_and_reports_row_mapping_errors(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "bad-mapping.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,empty_attr\ndevice/bad-1,device,Bad 1,csv_import,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="batch size"):
        app.import_service.import_dataset(
            ImportDatasetCommand(
                "default",
                "pytest",
                token,
                csv_file,
                "csv",
                _MAPPING,
                True,
                0,
            )
        )
    app.import_service._MAX_ROWS = 0
    with pytest.raises(ValidationError, match="exceeds"):
        app.import_service.import_dataset(
            ImportDatasetCommand("default", "pytest", token, csv_file, "csv", _MAPPING, True)
        )
    app.import_service._MAX_ROWS = 1_000_000

    mapping_with_missing_column = json.dumps(
        {
            "key": "asset_key",
            "kind": "kind",
            "display_name": "name",
            "source": "source",
            "tags": "missing_tags",
            "attributes.empty": "empty_attr",
        }
    )
    report = app.import_service.import_dataset(
        ImportDatasetCommand(
            "default",
            "pytest",
            token,
            csv_file,
            "csv",
            mapping_with_missing_column,
            True,
        )
    )

    messages = [issue.message for issue in report.dlq]
    assert "missing source column: missing_tags" in messages
    assert report.status.value == "failed"


def test_bulk_import_streams_batches_checkpoints_and_persists_report(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "bulk-devices.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial,critical\n"
        "device/bulk-001,device,Bulk 001,csv_import,prod,SN001,true\n"
        "device/bulk-002,device,Bulk 002,csv_import,prod,SN002,true\n"
        ",device,Bulk Missing,csv_import,prod,SN003,true\n"
        "device/bulk-004,device,Bulk 004,csv_import,prod,SN004,false\n"
        "device/bulk-005,device,Bulk 005,csv_import,prod,SN005,false\n",
        encoding="utf-8",
    )

    report = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            file_path=csv_file,
            format="csv",
            mapping_json=_MAPPING,
            dry_run=False,
            batch_size=2,
            checkpoint_interval=2,
            sample_limit=2,
        )
    )

    persisted = app.import_service.get_bulk_report("default", report.job_id.value)
    checkpoint = app.import_service.get_bulk_checkpoint("default", report.job_id.value)
    progress = app.import_service.get_bulk_progress("default", report.job_id.value)
    created = app.source_of_truth_service.get_object(
        GetSourceObjectCommand("default", token, "device/bulk-004")
    )

    assert report.status.value == "failed"
    assert report.total_rows == 5
    assert report.valid_rows == 4
    assert report.invalid_rows == 1
    assert report.metrics.batch_size == 2
    assert report.metrics.batches_completed == 2
    assert report.metrics.copy_strategy == "json-streaming-batch-checkpoint"
    assert report.checkpoint.next_row_number == 6
    assert len(report.impact_sample) == 2
    assert len(report.dlq_sample) == 1
    assert persisted.as_dict() == report.as_dict()
    assert checkpoint.next_row_number == 6
    assert progress.as_dict() == {
        "job_id": report.job_id.value,
        "tenant_id": "default",
        "status": "failed",
        "next_row_number": 6,
        "processed_rows": 5,
        "valid_rows": 4,
        "invalid_rows": 1,
        "create_count": 4,
        "update_count": 0,
        "batches_completed": 2,
        "resumable": True,
        "final_report_available": True,
    }
    assert created["attributes"]["serial"] == "SN004"


def test_bulk_import_resume_skips_rows_before_checkpoint(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "resume.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial,critical\n"
        "device/resume-001,device,Resume 001,csv_import,prod,SN001,true\n"
        "device/resume-002,device,Resume 002,csv_import,prod,SN002,true\n"
        "device/resume-003,device,Resume 003,csv_import,prod,SN003,false\n"
        "device/resume-004,device,Resume 004,csv_import,prod,SN004,false\n",
        encoding="utf-8",
    )
    checkpoint = BulkImportCheckpoint.create(
        tenant_id=TenantId.from_value("default"),
        next_row_number=3,
        total_rows=2,
        valid_rows=2,
        invalid_rows=0,
        create_count=2,
        update_count=0,
        batches_completed=1,
        status=ImportJobStatus.QUEUED,
    )
    app.import_repository.save_bulk_import_checkpoint(checkpoint)
    initial_progress = app.import_service.get_bulk_progress("default", checkpoint.job_id.value)

    report = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            file_path=csv_file,
            format="csv",
            mapping_json=_MAPPING,
            dry_run=True,
            batch_size=2,
            checkpoint_interval=2,
            resume_job_id=checkpoint.job_id.value,
            sample_limit=10,
        )
    )

    assert initial_progress.processed_rows == 2
    assert initial_progress.resumable is True
    assert initial_progress.final_report_available is False
    assert report.job_id == checkpoint.job_id
    assert report.total_rows == 4
    assert report.valid_rows == 4
    assert report.metrics.resumed_from_row == 3
    assert [impact.row_number for impact in report.impact_sample] == [3, 4]


def test_bulk_import_rejects_invalid_controls(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "one.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial,critical\n"
        "device/one,device,One,csv_import,prod,SN001,true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="batch size"):
        app.import_service.bulk_import_dataset(
            BulkImportDatasetCommand("default", "pytest", token, csv_file, "csv", _MAPPING, True, 0)
        )
    with pytest.raises(ValidationError, match="checkpoint interval"):
        app.import_service.bulk_import_dataset(
            BulkImportDatasetCommand(
                "default", "pytest", token, csv_file, "csv", _MAPPING, True, 10, 0
            )
        )
    with pytest.raises(ValidationError, match="sample limit"):
        app.import_service.bulk_import_dataset(
            BulkImportDatasetCommand(
                "default", "pytest", token, csv_file, "csv", _MAPPING, True, 10, 10, None, -1
            )
        )


def test_bulk_import_update_resume_errors_limits_and_mapping_edges(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "update.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial,critical\n"
        "device/bulk-update-1,device,Bulk Update 1,csv_import,prod,SN1,true\n",
        encoding="utf-8",
    )

    first = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            "default", "pytest", token, csv_file, "csv", _MAPPING, False, 5, 5, None, 5
        )
    )
    second = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            "default", "pytest", token, csv_file, "csv", _MAPPING, False, 5, 5, None, 5
        )
    )
    assert first.create_count == 1
    assert second.update_count == 1
    assert second.metrics.batches_completed == 1

    invalid_mapping = json.dumps(
        {
            "key": "asset_key",
            "kind": "kind",
            "display_name": "name",
            "source": "source",
            "attributes.-bad": "serial",
        }
    )
    invalid_report = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            "default", "pytest", token, csv_file, "csv", invalid_mapping, True, 5, 5, None, 5
        )
    )
    assert invalid_report.invalid_rows == 1
    assert "invalid attribute key" in invalid_report.dlq_sample[0].message

    invalid_kind = tmp_path / "invalid-kind.csv"
    invalid_kind.write_text(
        "asset_key,kind,name,source,tags,serial,critical\n"
        "device/bad-kind,unknown,Bad,csv_import,prod,SN1,true\n",
        encoding="utf-8",
    )
    report = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            "default", "pytest", token, invalid_kind, "csv", _MAPPING, True, 5, 5, None, 5
        )
    )
    assert report.invalid_rows == 1
    assert "object kind" in report.dlq_sample[0].message

    with pytest.raises(ValidationError, match="bulk import job not found"):
        app.import_service.get_bulk_report("default", "00000000-0000-0000-0000-000000000000")
    with pytest.raises(ValidationError, match="bulk import checkpoint not found"):
        app.import_service.get_bulk_checkpoint("default", "00000000-0000-0000-0000-000000000000")
    with pytest.raises(ValidationError, match="bulk import checkpoint not found"):
        app.import_service.bulk_import_dataset(
            BulkImportDatasetCommand(
                "default",
                "pytest",
                token,
                csv_file,
                "csv",
                _MAPPING,
                True,
                5,
                5,
                "00000000-0000-0000-0000-000000000000",
            )
        )

    applied_checkpoint = BulkImportCheckpoint.create(
        tenant_id=TenantId.from_value("default"),
        next_row_number=2,
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        create_count=1,
        update_count=0,
        batches_completed=1,
        status=ImportJobStatus.APPLIED,
    )
    app.import_repository.save_bulk_import_checkpoint(applied_checkpoint)
    with pytest.raises(ValidationError, match="already applied"):
        app.import_service.bulk_import_dataset(
            BulkImportDatasetCommand(
                "default",
                "pytest",
                token,
                csv_file,
                "csv",
                _MAPPING,
                True,
                5,
                5,
                applied_checkpoint.job_id.value,
            )
        )

    app.import_service._MAX_ROWS = 0
    with pytest.raises(ValidationError, match="exceeds"):
        app.import_service.bulk_import_dataset(
            BulkImportDatasetCommand(
                "default", "pytest", token, csv_file, "csv", _MAPPING, True, 5, 5, None, 5
            )
        )
    app.import_service._MAX_ROWS = 1_000_000


def test_legacy_migration_guides_cover_all_supported_sources(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")

    for source in ("device42", "netbox", "nautobot", "glpi", "csv"):
        guide = app.import_service.get_migration_guide(MigrationGuideCommand(source))
        payload = guide.as_dict()
        assert payload["source"] == source
        assert payload["template"]["source"] == source
        assert payload["steps"][0]["command"].endswith(f"--source {source}")
        assert payload["steps"][-1]["phase"] == "rollback"
        assert payload["required_controls"]
        assert payload["rollback_controls"]
        assert payload["success_criteria"]
        assert payload["native_ticketing_enabled"] is False
        assert payload["rsot_authoritative"] is True


def test_legacy_migration_plan_uses_template_and_reports_gaps(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "netbox.csv"
    csv_file.write_text(
        "name,status,serial,extra\nsw-01,active,SN-SW01,ignored\n",
        encoding="utf-8",
    )

    template = app.import_service.get_migration_template(MigrationTemplateCommand("netbox"))
    guide = app.import_service.get_migration_guide(MigrationGuideCommand("netbox"))
    report = app.import_service.plan_migration(
        PlanMigrationCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            source="netbox",
            file_path=csv_file,
            format="csv",
            sample_limit=10,
        )
    )
    persisted = app.import_service.get_migration_plan("default", report.job_id.value)

    assert template.as_dict()["mapping"]["source"] == "literal:netbox_migration"
    assert guide.as_dict()["steps"][0]["phase"] == "extract"
    assert guide.as_dict()["success_criteria"]
    assert report.status.value == "validated"
    assert report.total_rows == 1
    assert report.import_report.impacts[0].object_key == "sw-01"
    assert any(gap.field == "extra" for gap in report.gaps)
    assert persisted.as_dict()["resume_strategy"].startswith("Run import bulk-dataset")
    with pytest.raises(NotFoundError, match="source object not found"):
        app.source_of_truth_service.get_object(GetSourceObjectCommand("default", token, "sw-01"))


def test_legacy_migration_plan_fails_on_missing_required_source_column(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "device42-missing.csv"
    csv_file.write_text("serial_no,asset_no\nSN1,A1\n", encoding="utf-8")

    report = app.import_service.plan_migration(
        PlanMigrationCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            source="device42",
            file_path=csv_file,
            format="csv",
        )
    )

    assert report.status.value == "failed"
    assert any(gap.category == "missing-required" for gap in report.gaps)
    assert report.import_report.invalid_rows == 1


def test_legacy_migration_plan_limit_not_found_and_corrupt_store_errors(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "netbox-limit.csv"
    csv_file.write_text("name\nsw-limit\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="migration plan not found"):
        app.import_service.get_migration_plan("default", "missing")

    app.import_service._MAX_ROWS = 0
    with pytest.raises(ValidationError, match="migration dataset exceeds"):
        app.import_service.plan_migration(
            PlanMigrationCommand("default", "pytest", token, "netbox", csv_file, "csv")
        )
    app.import_service._MAX_ROWS = 1_000_000

    report = app.import_service.plan_migration(
        PlanMigrationCommand("default", "pytest", token, "netbox", csv_file, "csv", sample_limit=0)
    )
    key = "default:" + report.job_id.value
    app.store.data["migration_plans"][key]["template"]["mapping"] = []
    with pytest.raises(ValidationError, match="template mapping"):
        app.import_service.get_migration_plan("default", report.job_id.value)
    app.store.data["migration_plans"][key]["template"]["mapping"] = {"key": "name"}
    app.store.data["migration_plans"][key]["template"]["required_columns"] = "name"
    with pytest.raises(ValidationError, match="required columns"):
        app.import_service.get_migration_plan("default", report.job_id.value)
    app.store.data["migration_plans"][key]["template"]["required_columns"] = ["name"]
    app.store.data["migration_plans"][key]["gaps"] = {}
    with pytest.raises(ValidationError, match="plan details"):
        app.import_service.get_migration_plan("default", report.job_id.value)


def test_bulk_import_rollback_plan_and_apply_retires_created_objects(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "rollback-created.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial,critical\n"
        "device/rollback-created-1,device,Rollback Created,csv_import,prod,SN-RB,true\n",
        encoding="utf-8",
    )
    imported = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            "default", "pytest", token, csv_file, "csv", _MAPPING, False, 10, 10, None, 10
        )
    )

    plan = app.import_service.bulk_import_rollback(
        BulkImportRollbackCommand(
            "default",
            "pytest",
            token,
            imported.job_id.value,
            csv_file,
            "csv",
            _MAPPING,
            True,
            "fail",
        )
    )
    applied = app.import_service.bulk_import_rollback(
        BulkImportRollbackCommand(
            "default",
            "pytest",
            token,
            imported.job_id.value,
            csv_file,
            "csv",
            _MAPPING,
            False,
            "fail",
        )
    )
    current = app.source_of_truth_service.get_object(
        GetSourceObjectCommand("default", token, "device/rollback-created-1")
    )

    assert plan.status.value == "validated"
    assert plan.items[0].action.value == "retire-created"
    assert plan.items[0].status == "planned"
    assert applied.status.value == "applied"
    assert applied.items[0].status == "applied"
    assert current["status"] == "retired"


def test_bulk_import_rollback_restores_previous_version_and_blocks_conflicts(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "rollback-update.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial,critical\n"
        "device/rollback-update-1,device,Rollback Updated,csv_import,prod,SN-NEW,true\n",
        encoding="utf-8",
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="device/rollback-update-1",
            kind="device",
            display_name="Rollback Original",
            attributes_json=json.dumps({"serial": "SN-OLD", "critical": False}),
            tags=("legacy",),
            source="manual",
        )
    )
    imported = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            "default", "pytest", token, csv_file, "csv", _MAPPING, False, 10, 10, None, 10
        )
    )
    applied = app.import_service.bulk_import_rollback(
        BulkImportRollbackCommand(
            "default",
            "pytest",
            token,
            imported.job_id.value,
            csv_file,
            "csv",
            _MAPPING,
            False,
            "fail",
        )
    )
    restored = app.source_of_truth_service.get_object(
        GetSourceObjectCommand("default", token, "device/rollback-update-1")
    )

    assert applied.items[0].action.value == "restore-previous-version"
    assert applied.items[0].target_version == 1
    assert restored["display_name"] == "Rollback Original"
    assert restored["attributes"]["serial"] == "SN-OLD"
    assert restored["tags"] == ["legacy"]

    conflict_import = app.import_service.bulk_import_dataset(
        BulkImportDatasetCommand(
            "default", "pytest", token, csv_file, "csv", _MAPPING, False, 10, 10, None, 10
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="device/rollback-update-1",
            kind="device",
            display_name="Concurrent Manual Change",
            attributes_json=json.dumps({"serial": "SN-MANUAL"}),
            tags=("manual",),
            source="manual",
        )
    )
    blocked = app.import_service.bulk_import_rollback(
        BulkImportRollbackCommand(
            "default",
            "pytest",
            token,
            conflict_import.job_id.value,
            csv_file,
            "csv",
            _MAPPING,
            False,
            "fail",
        )
    )

    assert blocked.status.value == "failed"
    assert blocked.dry_run is True
    assert blocked.items[0].action.value == "conflict"
    assert blocked.items[0].status == "blocked"
