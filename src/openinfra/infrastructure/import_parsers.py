from __future__ import annotations

import csv
import json
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from openinfra.domain.common import ValidationError
from openinfra.domain.data_import import ImportFormat


class ImportDatasetParser:
    _MAX_BYTES = 50 * 1024 * 1024

    def parse(self, path: Path, import_format: ImportFormat) -> tuple[dict[str, str], ...]:
        return tuple(self.iter_rows(path, import_format))

    def iter_rows(self, path: Path, import_format: ImportFormat) -> Iterator[dict[str, str]]:
        self._assert_safe_file(path)
        if import_format == ImportFormat.CSV:
            yield from self._iter_csv(path)
            return
        if import_format == ImportFormat.JSON:
            yield from self._parse_json(path)
            return
        if import_format == ImportFormat.XLSX:
            yield from self._parse_xlsx(path)
            return
        raise ValidationError("unsupported import format")

    def _assert_safe_file(self, path: Path) -> None:
        if not path.is_file():
            raise ValidationError("import file does not exist: " + str(path))
        size = path.stat().st_size
        if size <= 0:
            raise ValidationError("import file is empty")
        if size > self._MAX_BYTES:
            raise ValidationError("import file exceeds 50 MiB limit")

    def _parse_csv(self, path: Path) -> tuple[dict[str, str], ...]:
        return tuple(self._iter_csv(path))

    def _iter_csv(self, path: Path) -> Iterator[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValidationError("CSV import requires a header row")
            for row in reader:
                yield self._normalize_row(row)

    def _parse_json(self, path: Path) -> tuple[dict[str, str], ...]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows_payload: object
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            rows_payload = payload["rows"]
        else:
            rows_payload = payload
        if not isinstance(rows_payload, list):
            raise ValidationError("JSON import must be a list or an object containing rows")
        rows: list[dict[str, str]] = []
        for item in rows_payload:
            if not isinstance(item, dict):
                raise ValidationError("JSON import rows must be objects")
            rows.append({str(key): self._stringify(value) for key, value in item.items()})
        return tuple(rows)

    def _parse_xlsx(self, path: Path) -> tuple[dict[str, str], ...]:
        try:
            with zipfile.ZipFile(path) as workbook:
                shared_strings = self._xlsx_shared_strings(workbook)
                sheet_name = self._first_sheet_name(workbook)
                xml = workbook.read(sheet_name)
        except (KeyError, zipfile.BadZipFile) as exc:
            raise ValidationError("XLSX import file is invalid") from exc
        worksheet = self._parse_xml(xml, "XLSX worksheet XML is invalid")
        rows = self._xlsx_rows(worksheet, shared_strings)
        if not rows:
            raise ValidationError("XLSX import requires a header row")
        headers = [cell.strip() for cell in rows[0]]
        if not any(headers):
            raise ValidationError("XLSX import header row is empty")
        parsed: list[dict[str, str]] = []
        for raw_row in rows[1:]:
            row = {
                header: raw_row[index].strip() if index < len(raw_row) else ""
                for index, header in enumerate(headers)
                if header
            }
            if any(value for value in row.values()):
                parsed.append(row)
        return tuple(parsed)

    def _xlsx_shared_strings(self, workbook: zipfile.ZipFile) -> tuple[str, ...]:
        try:
            xml = workbook.read("xl/sharedStrings.xml")
        except KeyError:
            return ()
        root = self._parse_xml(xml, "XLSX shared strings XML is invalid")
        values: list[str] = []
        for item in root.iter():
            if item.tag.endswith("}si") or item.tag == "si":
                pieces = [node.text or "" for node in item.iter() if node.tag.endswith("}t")]
                values.append("".join(pieces))
        return tuple(values)

    def _parse_xml(self, payload: bytes, error_message: str) -> Any:
        try:
            return ElementTree.fromstring(payload)
        except (ElementTree.ParseError, DefusedXmlException) as exc:
            raise ValidationError(error_message) from exc

    def _first_sheet_name(self, workbook: zipfile.ZipFile) -> str:
        names = sorted(
            name
            for name in workbook.namelist()
            if re.fullmatch(r"xl/worksheets/sheet[0-9]+\.xml", name)
        )
        if not names:
            raise ValidationError("XLSX import contains no worksheet")
        return names[0]

    def _xlsx_rows(
        self,
        worksheet: Any,
        shared_strings: tuple[str, ...],
    ) -> list[list[str]]:
        parsed_rows: list[list[str]] = []
        for row in self._children(worksheet, "row"):
            values: list[str] = []
            for cell in self._children(row, "c"):
                index = self._column_index(cell.attrib.get("r", ""))
                while len(values) < index:
                    values.append("")
                values.append(self._xlsx_cell_value(cell, shared_strings))
            if values:
                parsed_rows.append(values)
        return parsed_rows

    def _children(self, node: Any, local_name: str) -> tuple[Any, ...]:
        return tuple(
            child
            for child in node.iter()
            if child.tag.endswith("}" + local_name) or child.tag == local_name
        )

    def _xlsx_cell_value(
        self,
        cell: Any,
        shared_strings: tuple[str, ...],
    ) -> str:
        cell_type = cell.attrib.get("t")
        value_node = next((child for child in self._children(cell, "v")), None)
        inline_node = next((child for child in self._children(cell, "t")), None)
        if value_node is not None:
            raw_value = value_node.text
        elif inline_node is not None:
            raw_value = inline_node.text
        else:
            raw_value = ""
        if raw_value is None:
            return ""
        if cell_type == "s":
            index = int(str(raw_value))
            if index >= len(shared_strings):
                raise ValidationError("XLSX shared string index is invalid")
            return shared_strings[index]
        return str(raw_value)

    def _column_index(self, reference: str) -> int:
        letters = "".join(char for char in reference if char.isalpha()).upper()
        if not letters:
            return 0
        index = 0
        for char in letters:
            index = index * 26 + (ord(char) - ord("A") + 1)
        return index - 1

    def _normalize_row(self, row: dict[str, str | None]) -> dict[str, str]:
        return {str(key): (value or "").strip() for key, value in row.items() if key is not None}

    def _stringify(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, dict | list):
            return json.dumps(value, sort_keys=True)
        return str(value)
