from __future__ import annotations

import csv
import json
import zipfile
from io import BytesIO, StringIO

import pytest

from openinfra.application.export_services import ExportArtifactStreamBuilder
from openinfra.domain.common import ValidationError
from openinfra.domain.data_export import ExportFormat


def _row(index: int) -> dict[str, object]:
    return {
        "key": f"device/{index:05d}",
        "kind": "device",
        "display_name": f"Device {index}",
        "source": "pytest",
        "tags": ["prod", "dc-a"],
        "version": 1,
        "status": "active",
        "created_at": "2026-07-12T12:00:00+00:00",
        "updated_at": "2026-07-12T12:00:00+00:00",
        "attributes": {"serial": f"SN-{index:05d}"},
    }


def test_stream_builder_serializes_one_shot_json_and_spools_to_disk() -> None:
    consumed: list[int] = []

    def rows() -> object:
        for index in range(25):
            consumed.append(index)
            yield _row(index)

    result = ExportArtifactStreamBuilder(spool_threshold_bytes=128).serialize(
        ExportFormat.JSON, rows()
    )
    payload = json.loads(result.content)

    assert consumed == list(range(25))
    assert result.total_rows == 25
    assert result.spooled_to_disk is True
    assert payload[0]["key"] == "device/00000"
    assert payload[-1]["key"] == "device/00024"


def test_stream_builder_preserves_csv_and_xlsx_formats() -> None:
    builder = ExportArtifactStreamBuilder(spool_threshold_bytes=64)
    csv_result = builder.serialize(ExportFormat.CSV, (_row(index) for index in range(3)))
    csv_rows = tuple(csv.DictReader(StringIO(csv_result.content.decode("utf-8"))))
    assert [row["key"] for row in csv_rows] == [
        "device/00000",
        "device/00001",
        "device/00002",
    ]
    assert csv_result.total_rows == 3

    xlsx_result = builder.serialize(ExportFormat.XLSX, (_row(index) for index in range(2)))
    with zipfile.ZipFile(BytesIO(xlsx_result.content)) as workbook:
        worksheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "device/00000" in worksheet
    assert "device/00001" in worksheet
    assert xlsx_result.total_rows == 2


def test_stream_builder_validates_threshold_and_rows() -> None:
    with pytest.raises(ValidationError, match="threshold"):
        ExportArtifactStreamBuilder(0)
    invalid = _row(1)
    invalid["tags"] = "prod"
    with pytest.raises(ValidationError, match="tags are invalid"):
        ExportArtifactStreamBuilder().serialize(ExportFormat.CSV, [invalid])
