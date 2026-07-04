from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.domain.data_import import ImportFormat
from openinfra.infrastructure.import_parsers import ImportDatasetParser


class TestImportParsers:
    def test_json_parser_accepts_plain_list_and_stringifies_values(self, tmp_path: Path) -> None:
        path = tmp_path / "rows.json"
        path.write_text(
            json.dumps([
                {"name": "srv", "enabled": True, "metadata": {"serial": "A"}, "empty": None}
            ]),
            encoding="utf-8",
        )

        rows = ImportDatasetParser().parse(path, ImportFormat.JSON)

        assert rows == (
            {
                "name": "srv",
                "enabled": "True",
                "metadata": '{"serial": "A"}',
                "empty": "",
            },
        )

    def test_csv_parser_rejects_empty_header(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.csv"
        path.write_text("", encoding="utf-8")

        with pytest.raises(ValidationError, match="empty"):
            ImportDatasetParser().parse(path, ImportFormat.CSV)

    def test_parser_rejects_missing_and_oversized_files(self, tmp_path: Path) -> None:
        parser = ImportDatasetParser()
        with pytest.raises(ValidationError, match="does not exist"):
            parser.parse(tmp_path / "missing.csv", ImportFormat.CSV)
        path = tmp_path / "large.csv"
        path.write_text("a\n1\n", encoding="utf-8")
        parser._MAX_BYTES = 1
        with pytest.raises(ValidationError, match="exceeds"):
            parser.parse(path, ImportFormat.CSV)

    def test_json_parser_rejects_invalid_row_shape(self, tmp_path: Path) -> None:
        path = tmp_path / "rows.json"
        path.write_text(json.dumps({"rows": ["bad"]}), encoding="utf-8")
        with pytest.raises(ValidationError, match="rows must be objects"):
            ImportDatasetParser().parse(path, ImportFormat.JSON)
        path.write_text(json.dumps({"items": []}), encoding="utf-8")
        with pytest.raises(ValidationError, match="list"):
            ImportDatasetParser().parse(path, ImportFormat.JSON)

    def test_xlsx_parser_supports_shared_strings_and_rejects_invalid_files(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "shared.xlsx"
        _write_shared_string_xlsx(path)

        rows = ImportDatasetParser().parse(path, ImportFormat.XLSX)

        assert rows[0]["asset_key"] == "device/shared-1"
        assert rows[0]["name"] == "Shared Server"
        invalid = tmp_path / "invalid.xlsx"
        invalid.write_text("not a zip", encoding="utf-8")
        with pytest.raises(ValidationError, match="invalid"):
            ImportDatasetParser().parse(invalid, ImportFormat.XLSX)
        no_sheet = tmp_path / "no-sheet.xlsx"
        with zipfile.ZipFile(no_sheet, "w") as workbook:
            workbook.writestr("xl/workbook.xml", "<workbook />")
        with pytest.raises(ValidationError, match="no worksheet"):
            ImportDatasetParser().parse(no_sheet, ImportFormat.XLSX)
        bad_shared = tmp_path / "bad-shared.xlsx"
        _write_bad_shared_index_xlsx(bad_shared)
        with pytest.raises(ValidationError, match="shared string index"):
            ImportDatasetParser().parse(bad_shared, ImportFormat.XLSX)


def _write_shared_string_xlsx(path: Path) -> None:
    shared = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<sst xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <si><t>asset_key</t></si><si><t>name</t></si>
  <si><t>device/shared-1</t></si><si><t>Shared Server</t></si>
</sst>
"""
    sheet = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <sheetData>
    <row><c r=\"A1\" t=\"s\"><v>0</v></c><c r=\"B1\" t=\"s\"><v>1</v></c></row>
    <row><c r=\"A2\" t=\"s\"><v>2</v></c><c r=\"B2\" t=\"s\"><v>3</v></c></row>
  </sheetData>
</worksheet>
"""
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr("xl/sharedStrings.xml", shared)
        workbook.writestr("xl/worksheets/sheet1.xml", sheet)


def _write_bad_shared_index_xlsx(path: Path) -> None:
    shared = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<sst xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <si><t>header</t></si>
</sst>
"""
    sheet = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <sheetData><row><c r=\"A1\" t=\"s\"><v>2</v></c></row></sheetData>
</worksheet>
"""
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr("xl/sharedStrings.xml", shared)
        workbook.writestr("xl/worksheets/sheet1.xml", sheet)


def test_parser_edge_cases_for_empty_csv_and_blank_xlsx(tmp_path: Path) -> None:
    csv_file = tmp_path / "headerless.csv"
    csv_file.write_text("\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="header"):
        ImportDatasetParser().parse(csv_file, ImportFormat.CSV)

    no_rows = tmp_path / "no-rows.xlsx"
    with zipfile.ZipFile(no_rows, "w") as workbook:
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" />',
        )
    with pytest.raises(ValidationError, match="header row"):
        ImportDatasetParser().parse(no_rows, ImportFormat.XLSX)

    blank_header = tmp_path / "blank-header.xlsx"
    with zipfile.ZipFile(blank_header, "w") as workbook:
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData><row><c r="A1"><v></v></c></row></sheetData></worksheet>""",
        )
    with pytest.raises(ValidationError, match="header row is empty"):
        ImportDatasetParser().parse(blank_header, ImportFormat.XLSX)

    gap = tmp_path / "gap.xlsx"
    with zipfile.ZipFile(gap, "w") as workbook:
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
<row><c r="B1" t="inlineStr"><is><t>name</t></is></c></row>
<row><c r="B2" t="inlineStr"><is><t>Gap Server</t></is></c></row>
</sheetData></worksheet>""",
        )
    assert ImportDatasetParser().parse(gap, ImportFormat.XLSX) == ({"name": "Gap Server"},)
