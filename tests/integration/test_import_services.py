from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.import_services import ImportDatasetCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import GetSourceObjectCommand
from openinfra.domain.common import NotFoundError, ValidationError
from openinfra.infrastructure.import_parsers import ImportDatasetParser
from openinfra.domain.data_import import ImportFormat


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
            roles=("sot:operator", "audit:reader"),
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


def test_import_service_rejects_limits_and_reports_row_mapping_errors(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _bootstrap(app)
    csv_file = tmp_path / "bad-mapping.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,empty_attr\n"
        "device/bad-1,device,Bad 1,csv_import,\n",
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
