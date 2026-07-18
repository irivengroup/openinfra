#!/usr/bin/env python3
"""Deterministically convert the OpenInfra PostgreSQL migration catalog to Oracle 19c.

The converter intentionally supports the SQL constructs present in OpenInfra migrations.  It
fails closed when a PostgreSQL-only construct survives conversion, so a new migration cannot be
promoted until its Oracle representation is explicit and reviewable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openinfra.infrastructure.postgresql import PostgreSQLStatementSplitter  # noqa: E402

UUID_DEFAULT: Final[str] = (
    "LOWER(REGEXP_REPLACE(RAWTOHEX(SYS_GUID()), "
    "'(.{8})(.{4})(.{4})(.{4})(.{12})', '\\1-\\2-\\3-\\4-\\5'))"
)
ORACLE_RESERVED_COLUMNS: Final[set[str]] = {"resource", "rows"}
LARGE_TEXT_COLUMNS: Final[set[str]] = {
    "body",
    "content",
    "ddl",
    "details",
    "diff",
    "error",
    "error_message",
    "evidence",
    "explanation",
    "instructions",
    "manifest",
    "notes",
    "output",
    "query",
    "raw_payload",
    "report",
    "response",
    "script",
    "sql",
    "stacktrace",
    "template",
    "text",
}
POSTGRESQL_RESIDUAL_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("PostgreSQL cast", re.compile(r"::")),
    ("PostgreSQL dollar quote", re.compile(r"\$[A-Za-z_]*\$")),
    ("PostgreSQL ON CONFLICT", re.compile(r"\bON\s+CONFLICT\b", re.I)),
    ("PostgreSQL JSON operator", re.compile(r"(?:->>|->|#>>|#>)")),
    ("PostgreSQL array", re.compile(r"\bARRAY\s*\[", re.I)),
    ("PostgreSQL extension", re.compile(r"\bCREATE\s+EXTENSION\b", re.I)),
    ("PostgreSQL partition child", re.compile(r"\bPARTITION\s+OF\b", re.I)),
    ("PostgreSQL index method", re.compile(r"\bUSING\s+(?:GIN|GIST|BRIN)\b", re.I)),
    ("PostgreSQL boolean literal", re.compile(r"\b(?:TRUE|FALSE)\b", re.I)),
    ("PostgreSQL type", re.compile(r"\b(?:JSONB|TIMESTAMPTZ|BYTEA|TSVECTOR)\b", re.I)),
    ("PostgreSQL IF NOT EXISTS", re.compile(r"\bIF\s+NOT\s+EXISTS\b", re.I)),
    ("PostgreSQL IF EXISTS", re.compile(r"\bIF\s+EXISTS\b", re.I)),
    ("PostgreSQL trim", re.compile(r"\bBTRIM\s*\(", re.I)),
    ("PostgreSQL current time", re.compile(r"\bNOW\s*\(", re.I)),
    (
        "PostgreSQL array function",
        re.compile(r"\b(?:ARRAY_LENGTH|CARDINALITY|JSONB_ARRAY_LENGTH)\s*\(", re.I),
    ),
    ("PostgreSQL interval", re.compile(r"\bINTERVAL\s+'\d+\s+DAYS?'", re.I)),
    ("PostgreSQL NOT VALID", re.compile(r"\bNOT\s+VALID\b", re.I)),
    ("PostgreSQL ON DELETE RESTRICT", re.compile(r"\bON\s+DELETE\s+RESTRICT\b", re.I)),
    ("Oracle DEFAULT ordering", re.compile(r"\bNOT\s+NULL\s+DEFAULT\b", re.I)),
)


@dataclass(frozen=True, slots=True)
class ConvertedMigration:
    name: str
    source_sha256: str
    oracle_sha256: str
    statement_count: int
    output: str


class ConversionError(RuntimeError):
    """Raised when a source migration cannot be represented safely for Oracle."""


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _strip_leading_comments(statement: str) -> str:
    lines = statement.splitlines()
    while lines and (not lines[0].strip() or lines[0].lstrip().startswith("--")):
        lines.pop(0)
    return "\n".join(lines).strip()


def _split_top_level(payload: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    single = False
    double = False
    index = 0
    while index < len(payload):
        char = payload[index]
        nxt = payload[index + 1] if index + 1 < len(payload) else ""
        if single:
            if char == "'" and nxt == "'":
                index += 2
                continue
            if char == "'":
                single = False
            index += 1
            continue
        if double:
            if char == '"' and nxt == '"':
                index += 2
                continue
            if char == '"':
                double = False
            index += 1
            continue
        if char == "'":
            single = True
        elif char == '"':
            double = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == delimiter and depth == 0:
            parts.append(payload[start:index].strip())
            start = index + 1
        index += 1
    parts.append(payload[start:].strip())
    return [part for part in parts if part]


def _find_matching_parenthesis(payload: str, opening_index: int) -> int:
    depth = 0
    single = False
    double = False
    index = opening_index
    while index < len(payload):
        char = payload[index]
        nxt = payload[index + 1] if index + 1 < len(payload) else ""
        if single:
            if char == "'" and nxt == "'":
                index += 2
                continue
            if char == "'":
                single = False
            index += 1
            continue
        if double:
            if char == '"' and nxt == '"':
                index += 2
                continue
            if char == '"':
                double = False
            index += 1
            continue
        if char == "'":
            single = True
        elif char == '"':
            double = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ConversionError("unbalanced parenthesis in migration statement")


def _column_name(definition: str) -> str | None:
    stripped = definition.strip()
    if not stripped:
        return None
    first = stripped.split(None, 1)[0].strip('"').lower()
    if first.upper() in {"PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "CONSTRAINT"}:
        return None
    return first


def _text_type(column: str) -> str:
    normalized = column.lower()
    if normalized in LARGE_TEXT_COLUMNS or any(
        token in normalized
        for token in ("payload", "metadata", "document", "artifact", "snapshot", "configuration")
    ):
        return "CLOB"
    if any(token in normalized for token in ("url", "uri", "endpoint")):
        return "VARCHAR2(1000 CHAR)"
    if any(token in normalized for token in ("description", "message", "reason", "summary")):
        return "VARCHAR2(1000 CHAR)"
    if normalized in {"name", "display_name", "legal_name", "title"} or normalized.endswith(
        "_name"
    ):
        return "VARCHAR2(255 CHAR)"
    if normalized.endswith(("_id", "_key", "_code", "_type", "_kind", "_status")):
        return "VARCHAR2(128 CHAR)"
    return "VARCHAR2(255 CHAR)"


def _replace_type(definition: str) -> str:
    column = _column_name(definition)
    prefix = ""
    value = definition
    if column is not None:
        first, separator, remainder = definition.strip().partition(" ")
        rendered_name = f'"{column.upper()}"' if column in ORACLE_RESERVED_COLUMNS else first
        prefix = rendered_name + separator
        value = remainder
    value = re.sub(r"\bdouble\s+precision\b", "BINARY_DOUBLE", value, flags=re.I)
    value = re.sub(
        r"\btimestamp\s+with\s+time\s+zone\b", "TIMESTAMP WITH TIME ZONE", value, flags=re.I
    )
    value = re.sub(r"\btimestamptz\b", "TIMESTAMP WITH TIME ZONE", value, flags=re.I)
    value = re.sub(r"\btimestamp\s+without\s+time\s+zone\b", "TIMESTAMP", value, flags=re.I)
    value = re.sub(r"\buuid\b", "VARCHAR2(36 CHAR)", value, flags=re.I)
    value = re.sub(r"\bjsonb\b", "CLOB", value, flags=re.I)
    value = re.sub(r"\bjson\b", "CLOB", value, flags=re.I)
    value = re.sub(r"\bbytea\b", "BLOB", value, flags=re.I)
    value = re.sub(r"\bcidr\b", "VARCHAR2(64 CHAR)", value, flags=re.I)
    value = re.sub(r"\binet\b", "VARCHAR2(64 CHAR)", value, flags=re.I)
    value = re.sub(r"\bmacaddr\b", "VARCHAR2(17 CHAR)", value, flags=re.I)
    value = re.sub(
        r"\bbigserial\b", "NUMBER(19) GENERATED BY DEFAULT AS IDENTITY", value, flags=re.I
    )
    value = re.sub(r"\bserial\b", "NUMBER(10) GENERATED BY DEFAULT AS IDENTITY", value, flags=re.I)
    value = re.sub(r"\bbigint\b", "NUMBER(19)", value, flags=re.I)
    value = re.sub(r"\bsmallint\b", "NUMBER(5)", value, flags=re.I)
    value = re.sub(r"\binteger\b", "NUMBER(10)", value, flags=re.I)
    value = re.sub(r"\bnumeric\s*\(([^\)]*)\)", r"NUMBER(\1)", value, flags=re.I)
    value = re.sub(r"\bnumeric\b", "NUMBER", value, flags=re.I)
    value = re.sub(r"\bdecimal\s*\(([^\)]*)\)", r"NUMBER(\1)", value, flags=re.I)
    value = re.sub(r"\bdecimal\b", "NUMBER", value, flags=re.I)
    value = re.sub(r"\breal\b", "BINARY_FLOAT", value, flags=re.I)
    value = re.sub(r"\bboolean\b", "NUMBER(1)", value, flags=re.I)
    value = re.sub(r"\btext\s*\[\s*\]", "CLOB", value, flags=re.I)
    value = re.sub(r"\binteger\s*\[\s*\]", "CLOB", value, flags=re.I)
    if column is not None:
        value = re.sub(r"\btext\b", _text_type(column), value, flags=re.I)
    value = re.sub(r"\bchar\s*\((\d+)\)", r"CHAR(\1 CHAR)", value, flags=re.I)
    value = re.sub(
        r"\bvarchar\s*\((\d+)\)",
        lambda match: f"VARCHAR2({min(int(match.group(1)), 1000)} CHAR)",
        value,
        flags=re.I,
    )
    value = re.sub(r"\btsvector\b", "CLOB", value, flags=re.I)
    value = re.sub(
        r"\bNOT\s+NULL\s+DEFAULT\s+(.+?)(?=\s+(?:PRIMARY|UNIQUE|REFERENCES|CHECK|CONSTRAINT)\b|$)",
        r"DEFAULT \1 NOT NULL",
        value,
        flags=re.I | re.S,
    )
    return prefix + value


def _quote_reserved_columns(payload: str) -> str:
    value = payload
    for column in ORACLE_RESERVED_COLUMNS:
        value = re.sub(
            rf'(?<!["A-Za-z0-9_]){column}(?!["A-Za-z0-9_])',
            f'"{column.upper()}"',
            value,
            flags=re.I,
        )
    return value


def _replace_outside_literals(payload: str, replacements: dict[str, str]) -> str:
    output: list[str] = []
    token: list[str] = []
    single = False
    index = 0

    def flush() -> None:
        if not token:
            return
        raw = "".join(token)
        output.append(replacements.get(raw.lower(), raw))
        token.clear()

    while index < len(payload):
        char = payload[index]
        nxt = payload[index + 1] if index + 1 < len(payload) else ""
        if single:
            output.append(char)
            if char == "'" and nxt == "'":
                output.append(nxt)
                index += 2
                continue
            if char == "'":
                single = False
            index += 1
            continue
        if char == "'":
            flush()
            output.append(char)
            single = True
        elif char.isalnum() or char == "_":
            token.append(char)
        else:
            flush()
            output.append(char)
        index += 1
    flush()
    return "".join(output)


def _common_expression_conversion(payload: str) -> str:
    value = payload

    def convert_array(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        if not body:
            return "'[]'"
        items = _split_top_level(body)
        values: list[str] = []
        for item in items:
            literal = item.strip()
            if not re.fullmatch(r"'(?:''|[^'])*'", literal):
                raise ConversionError("non-literal PostgreSQL ARRAY cannot be converted safely")
            values.append(literal[1:-1].replace("''", "'"))
        return "'" + json.dumps(values, ensure_ascii=False, separators=(",", ":")) + "'"

    value = re.sub(
        r"ARRAY\s*\[(.*?)\]\s*::(?:CLOB|text\s*\[\s*\])", convert_array, value, flags=re.I | re.S
    )
    value = re.sub(
        r"'([^']*)'::(?:jsonb|json|text|uuid|date|numeric|CLOB)", r"'\1'", value, flags=re.I
    )
    value = re.sub(
        r"\b([A-Za-z_][A-Za-z0-9_.]*)::(?:text|uuid|date|numeric)\b", r"\1", value, flags=re.I
    )
    value = re.sub(
        r"::\s*(?:text|uuid|date|numeric(?:\s*\([^\)]*\))?|jsonb|json)\b", "", value, flags=re.I
    )
    value = re.sub(r"\bgen_random_uuid\s*\(\s*\)", lambda _: UUID_DEFAULT, value, flags=re.I)
    value = re.sub(r"\bnow\s*\(\s*\)", "SYSTIMESTAMP", value, flags=re.I)
    value = re.sub(r"\bcurrent_timestamp\b", "SYSTIMESTAMP", value, flags=re.I)
    value = re.sub(r"\bbtrim\s*\(", "TRIM(", value, flags=re.I)
    value = re.sub(
        r"TRIM\s*\(([^\)]+)\)\s*=\s*''",
        r"TRIM(\1) IS NULL",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"TRIM\s*\(([^\)]+)\)\s*<>\s*''",
        r"TRIM(\1) IS NOT NULL",
        value,
        flags=re.I,
    )
    value = re.sub(r"\bDEFAULT\s+''", "DEFAULT ' '", value, flags=re.I)
    value = re.sub(r"\s+NOT\s+VALID\b", "", value, flags=re.I)
    value = re.sub(r"\s+ON\s+DELETE\s+RESTRICT\b", "", value, flags=re.I)
    value = re.sub(
        r"\brepeat\s*\(\s*('(?:''|[^'])*')\s*,\s*([^\)]+)\)", r"RPAD(\1, \2, \1)", value, flags=re.I
    )
    value = _replace_outside_literals(value, {"true": "1", "false": "0"})
    value = re.sub(r"\binterval\s+'(\d+)\s+days?'", r"INTERVAL '\1' DAY", value, flags=re.I)
    return value


def _convert_checks(payload: str) -> str:
    value = payload
    value = re.sub(
        r"([A-Za-z_][A-Za-z0-9_.\"]*)\s*->>\s*'([^']+)'",
        r"JSON_VALUE(\1, '$.\2')",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"jsonb_typeof\s*\(\s*([A-Za-z_][A-Za-z0-9_.\"]*)\s*\)\s*=\s*'object'",
        r"JSON_EXISTS(\1, '$?(@.type() == \"object\")')",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"jsonb_typeof\s*\(\s*([A-Za-z_][A-Za-z0-9_.\"]*)\s*\)\s*=\s*'array'",
        r"JSON_EXISTS(\1, '$?(@.type() == \"array\")')",
        value,
        flags=re.I,
    )

    def convert_array_minimum(match: re.Match[str]) -> str:
        identifier = match.group(1)
        minimum = int(match.group(2))
        return f"JSON_EXISTS({identifier}, '$[{minimum - 1}]')"

    value = re.sub(
        r'array_length\s*\(\s*((?:"[A-Za-z_][A-Za-z0-9_]*"|[A-Za-z_][A-Za-z0-9_.]*))\s*,\s*1\s*\)\s*>=\s*(\d+)',
        convert_array_minimum,
        value,
        flags=re.I,
    )
    value = re.sub(
        r"array_length\s*\(\s*((?:\"[A-Za-z_][A-Za-z0-9_]*\"|[A-Za-z_][A-Za-z0-9_.]*))\s*,\s*1\s*\)\s+IS\s+NOT\s+NULL",
        r"JSON_EXISTS(\1, '$[0]')",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"cardinality\s*\(\s*([A-Za-z_][A-Za-z0-9_.\"]*)\s*\)\s*>\s*0",
        r"JSON_EXISTS(\1, '$[0]')",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"jsonb_array_length\s*\(\s*([A-Za-z_][A-Za-z0-9_.\"]*)\s*\)\s*>=\s*1",
        r"JSON_EXISTS(\1, '$[0]')",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"jsonb_array_length\s*\(\s*([A-Za-z_][A-Za-z0-9_.\"]*)\s*\)\s*<=\s*16",
        r"NOT JSON_EXISTS(\1, '$[16]')",
        value,
        flags=re.I,
    )
    value = re.sub(r"octet_length\s*\(\s*([^\)]+)\s*\)", r"LENGTH(\1)", value, flags=re.I)
    value = re.sub(
        r"([A-Za-z_][A-Za-z0-9_.\"]*)\s*!~\s*('(?:''|[^'])*')",
        r"NOT REGEXP_LIKE(\1, \2)",
        value,
    )
    value = re.sub(
        r"([A-Za-z_][A-Za-z0-9_.\"]*)\s*~\s*('(?:''|[^'])*')",
        r"REGEXP_LIKE(\1, \2)",
        value,
    )
    return value


def _partition_counts(source: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for child in re.finditer(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+\w+\s+PARTITION\s+OF\s+(\w+)\s+"
        r"FOR\s+VALUES\s+WITH\s*\(\s*MODULUS\s+(\d+)",
        source,
        re.I,
    ):
        counts[child.group(1).lower()] = int(child.group(2))
    for block in re.finditer(r"DO\s+\$[A-Za-z_]*\$(.*?)\$[A-Za-z_]*\$\s*;", source, re.I | re.S):
        body = block.group(1)
        upper = re.search(r"FOR\s+partition_index\s+IN\s+0\.\.(\d+)\s+LOOP", body, re.I)
        if upper is None:
            continue
        partition_count = int(upper.group(1)) + 1
        for table_name in re.findall(r"'([a-z][a-z0-9_]*)'", body, re.I):
            if "PARTITION OF " in body.upper() and not table_name.lower().startswith(
                "create table"
            ):
                counts.setdefault(table_name.lower(), partition_count)
        for table_name in re.findall(r"PARTITION\s+OF\s+([a-z][a-z0-9_]*)", body, re.I):
            counts[table_name.lower()] = partition_count
    return counts


def _convert_create_table(statement: str, partition_counts: dict[str, int]) -> tuple[str, ...]:
    if re.search(r"\bPARTITION\s+OF\b", statement, re.I):
        return ()
    if re.match(r"CREATE\s+TEMP\s+TABLE\b", statement, re.I):
        value = re.sub(
            r"^CREATE\s+TEMP\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+COMMIT\s+DROP\s+AS",
            r"CREATE GLOBAL TEMPORARY TABLE \1 ON COMMIT PRESERVE ROWS AS",
            statement,
            flags=re.I,
        )
        value = re.sub(r"::text\b", "", value, flags=re.I)
        return (_common_expression_conversion(value).rstrip(";"),)

    match = re.match(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", statement, re.I
    )
    if match is None:
        raise ConversionError("unsupported CREATE TABLE syntax")
    table_name = match.group(1)
    opening = statement.find("(", match.start())
    closing = _find_matching_parenthesis(statement, opening)
    body = statement[opening + 1 : closing]
    suffix = statement[closing + 1 :].strip().rstrip(";")
    converted_parts: list[str] = []
    json_columns: list[str] = []
    for part in _split_top_level(body):
        column = _column_name(part)
        converted = _common_expression_conversion(part)
        if column is not None:
            converted = _replace_type(converted)
        if re.search(r"\b(?:text|integer)\s*\[\s*\]", part, re.I):
            converted = re.sub(r"DEFAULT\s+'\{\}'", "DEFAULT '[]'", converted, flags=re.I)
        converted = _convert_checks(converted)
        if column is None:
            converted = _quote_reserved_columns(converted)
        if (
            column
            and re.search(r"\bCLOB\b", converted, re.I)
            and re.search(r"\b(?:JSONB|JSON|TEXT\s*\[|INTEGER\s*\[)", part, re.I)
        ):
            json_columns.append(column)
        if "GENERATED ALWAYS AS" in converted.upper() and "CLOB" in converted.upper():
            generated_name = converted.split(None, 1)[0]
            converted = f"{generated_name} CLOB"
        converted_parts.append(converted)
    existing_constraints = "\n".join(converted_parts).upper()
    for column in json_columns:
        constraint_name = f"ck_{table_name}_{column}_json"
        if constraint_name.upper() not in existing_constraints:
            quoted = f'"{column.upper()}"' if column in ORACLE_RESERVED_COLUMNS else column
            converted_parts.append(f"CONSTRAINT {constraint_name} CHECK ({quoted} IS JSON)")
    suffix_value = ""
    partition_match = re.search(r"PARTITION\s+BY\s+HASH\s*\(\s*([^\)]+)\s*\)", suffix, re.I)
    if partition_match is not None:
        count = partition_counts.get(table_name.lower(), 16)
        key = _common_expression_conversion(partition_match.group(1).strip())
        suffix_value = f"\nPARTITION BY HASH ({key}) PARTITIONS {count}"
    output = (
        f"CREATE TABLE {table_name} (\n    "
        + ",\n    ".join(converted_parts)
        + f"\n){suffix_value}"
    )
    return (output,)


def _convert_alter_table(statement: str) -> tuple[str, ...]:
    value = statement.rstrip().rstrip(";")
    match = re.match(r"ALTER\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)", value, re.I | re.S)
    if match is None:
        raise ConversionError("unsupported ALTER TABLE syntax")
    table_name = match.group(1)
    operation = match.group(2).strip()
    if re.match(r"ADD\s+COLUMN\b", operation, re.I):
        definitions = re.split(
            r",\s*ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?", operation, flags=re.I
        )
        definitions[0] = re.sub(
            r"^ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?", "", definitions[0], flags=re.I
        )
        outputs = []
        for definition in definitions:
            converted = _convert_checks(
                _replace_type(_common_expression_conversion(definition.strip()))
            )
            outputs.append(f"ALTER TABLE {table_name} ADD ({converted})")
        return tuple(outputs)
    set_not_null = re.match(r"ALTER\s+COLUMN\s+(\w+)\s+SET\s+NOT\s+NULL", operation, re.I)
    if set_not_null:
        column = _common_expression_conversion(set_not_null.group(1))
        return (f"ALTER TABLE {table_name} MODIFY ({column} NOT NULL)",)
    drop_not_null = re.match(r"ALTER\s+COLUMN\s+(\w+)\s+DROP\s+NOT\s+NULL", operation, re.I)
    if drop_not_null:
        column = _common_expression_conversion(drop_not_null.group(1))
        return (f"ALTER TABLE {table_name} MODIFY ({column} NULL)",)
    operation = re.sub(r"DROP\s+CONSTRAINT\s+IF\s+EXISTS", "DROP CONSTRAINT", operation, flags=re.I)
    operation = re.sub(
        r"VALIDATE\s+CONSTRAINT", "ENABLE VALIDATE CONSTRAINT", operation, flags=re.I
    )
    operation = _convert_checks(_replace_type(_common_expression_conversion(operation)))
    operation = _quote_reserved_columns(operation)
    return (f"ALTER TABLE {table_name} {operation}",)


def _convert_index_predicate(predicate: str) -> str:
    value = _quote_reserved_columns(_common_expression_conversion(predicate.strip()))
    if re.fullmatch(r'(?:(?:"[A-Za-z_][A-Za-z0-9_]*")|(?:[A-Za-z_][A-Za-z0-9_]*))', value):
        return f"{value} = 1"
    return value


def _convert_index(statement: str) -> tuple[str, ...]:
    value = statement.rstrip().rstrip(";")
    if re.search(r"\bUSING\s+(?:GIN|GIST|BRIN)\b", value, re.I):
        return ()
    value = re.sub(r"\bIF\s+NOT\s+EXISTS\b\s*", "", value, flags=re.I)
    value = re.sub(r"\s+WITH\s*\([^\)]*\)\s*$", "", value, flags=re.I | re.S)
    where_match = re.search(r"\s+WHERE\s+(.+)$", value, re.I | re.S)
    predicate = where_match.group(1).strip() if where_match is not None else None
    if where_match is not None:
        value = value[: where_match.start()].rstrip()
    value = _quote_reserved_columns(_common_expression_conversion(value))
    value = re.sub(
        r"\(\s*\(?\s*([A-Za-z_][A-Za-z0-9_.]*)\s*->>\s*'([^']+)'\s*\)?\s*\)",
        r"(JSON_VALUE(\1, '$.\2' RETURNING VARCHAR2(64 CHAR)))",
        value,
        flags=re.I,
    )
    if predicate is not None and re.match(r"CREATE\s+UNIQUE\s+INDEX", value, re.I):
        match = re.match(
            r"(CREATE\s+UNIQUE\s+INDEX\s+\w+\s+ON\s+\w+)\s*\((.*)\)$",
            value,
            re.I | re.S,
        )
        if match is None:
            raise ConversionError("unsupported partial unique index syntax")
        condition = _convert_index_predicate(predicate)
        expressions = []
        for item in _split_top_level(match.group(2)):
            expression = item.strip()
            if not re.fullmatch(r'(?:"[A-Za-z_][A-Za-z0-9_]*"|[A-Za-z_][A-Za-z0-9_]*)', expression):
                raise ConversionError("partial unique index contains a non-column expression")
            expressions.append(f"CASE WHEN {condition} THEN {expression} END")
        value = f"{match.group(1)} ({', '.join(expressions)})"
    return (value,)


def _merge_do_nothing(table: str, columns: list[str], values: list[str], key: str) -> str:
    aliases = [f"{value} AS {column}" for column, value in zip(columns, values, strict=True)]
    insert_columns = ", ".join(columns)
    insert_values = ", ".join(f"source.{column}" for column in columns)
    return (  # nosec B608 - identifiers are parsed from trusted migrations
        f"MERGE INTO {table} target\n"  # noqa: S608  # nosec B608
        f"USING (SELECT {', '.join(aliases)} FROM dual) source\n"
        f"ON (target.{key} = source.{key})\n"
        "WHEN NOT MATCHED THEN\n"
        f"    INSERT ({insert_columns}) VALUES ({insert_values})"
    )


def _convert_insert(statement: str) -> tuple[str, ...]:
    value = _common_expression_conversion(statement.rstrip().rstrip(";"))
    match = re.match(
        r"INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)\s*ON\s+CONFLICT\s*\((\w+)\)\s+DO\s+NOTHING$",
        value,
        re.I | re.S,
    )
    if match:
        columns = [item.strip() for item in _split_top_level(match.group(2))]
        values = [item.strip() for item in _split_top_level(match.group(3))]
        return (_merge_do_nothing(match.group(1), columns, values, match.group(4)),)
    update_match = re.match(
        r"INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)\s*ON\s+CONFLICT\s*\((\w+)\)\s+DO\s+UPDATE\s+SET\s+(.+)$",
        value,
        re.I | re.S,
    )
    if update_match:
        table = update_match.group(1)
        columns = [item.strip() for item in _split_top_level(update_match.group(2))]
        values = [item.strip() for item in _split_top_level(update_match.group(3))]
        key = update_match.group(4)
        aliases = [f"{item} AS {column}" for column, item in zip(columns, values, strict=True)]
        update_clause = re.sub(
            r"\bEXCLUDED\.(\w+)", r"source.\1", update_match.group(5), flags=re.I
        )
        update_clause = re.sub(rf"\b{table}\.", "target.", update_clause, flags=re.I)
        return (  # nosec B608 - identifiers are parsed from trusted migrations
            f"MERGE INTO {table} target\n"  # noqa: S608  # nosec B608
            f"USING (SELECT {', '.join(aliases)} FROM dual) source\n"
            f"ON (target.{key} = source.{key})\n"
            f"WHEN MATCHED THEN UPDATE SET {update_clause}\n"
            f"WHEN NOT MATCHED THEN INSERT ({', '.join(columns)}) "
            f"VALUES ({', '.join(f'source.{column}' for column in columns)})",
        )
    raise ConversionError("unsupported INSERT ... ON CONFLICT statement")


def _convert_floor_update(statement: str) -> tuple[str, ...]:
    match = re.match(
        r"UPDATE\s+(\w+)\s+AS\s+target\s+SET\s+(.+?)\s+FROM\s+openinfra_floor_nomenclature_map\s+AS\s+mapping\s+WHERE\s+(.+)$",
        statement.rstrip().rstrip(";"),
        re.I | re.S,
    )
    if match is None:
        return (_common_expression_conversion(statement.rstrip().rstrip(";")),)
    table = match.group(1)
    assignments = _split_top_level(match.group(2))
    where = match.group(3)
    join_predicates = re.findall(r"target\.(\w+)\s*=\s*mapping\.(\w+)", where, flags=re.I)
    if not join_predicates:
        raise ConversionError("floor nomenclature UPDATE has no join predicate")
    correlation = " AND ".join(
        f"mapping.{right} = target.{left}" for left, right in join_predicates
    )
    set_parts: list[str] = []
    for assignment in assignments:
        target_column, source_expression = assignment.split("=", 1)
        target_column = target_column.strip()
        source_expression = source_expression.strip()
        set_parts.append(  # nosec B608 - trusted migration identifiers
            f"{target_column} = (SELECT {source_expression} "  # noqa: S608  # nosec B608
            "FROM openinfra_floor_nomenclature_map mapping "
            f"WHERE {correlation})"
        )
    return (  # nosec B608 - trusted migration identifiers
        f"UPDATE {table} target\nSET {', '.join(set_parts)}\n"  # noqa: S608  # nosec B608
        "WHERE EXISTS (SELECT 1 FROM openinfra_floor_nomenclature_map mapping "
        f"WHERE {correlation})",
    )


def _convert_update(statement: str) -> tuple[str, ...]:
    value = statement.rstrip().rstrip(";")
    if re.search(r"\bFROM\s+openinfra_floor_nomenclature_map\b", value, re.I):
        return _convert_floor_update(value)
    value = re.sub(
        r"pg_catalog\.family\s*\(\s*prefixes\.cidr\s*\)",
        "CASE WHEN INSTR(prefixes.cidr, ':') > 0 THEN 6 ELSE 4 END",
        value,
        flags=re.I,
    )
    return (_common_expression_conversion(value),)


def _convert_do_block(statement: str) -> tuple[str, ...]:
    upper = statement.upper()
    if "PARTITION OF" in upper or "FOREACH TABLE_NAME" in upper:
        return ()
    constraint = re.search(
        r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+CONSTRAINT\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?);\s*END\s+IF",
        statement,
        re.I | re.S,
    )
    if constraint:
        operation = _convert_checks(_common_expression_conversion(constraint.group(3).strip()))
        return (
            f"ALTER TABLE {constraint.group(1)} ADD CONSTRAINT {constraint.group(2)} {operation}",
        )
    if "OPENINFRA_FLOOR_NOMENCLATURE_MAP" in upper and "RAISE EXCEPTION" in upper:
        return (
            "DECLARE\n"
            "    duplicate_count NUMBER;\n"
            "BEGIN\n"
            "    SELECT COUNT(*) INTO duplicate_count FROM (\n"
            "        SELECT tenant_id, site_code, building_code, new_code\n"
            "        FROM openinfra_floor_nomenclature_map\n"
            "        GROUP BY tenant_id, site_code, building_code, new_code\n"
            "        HAVING COUNT(*) > 1\n"
            "    );\n"
            "    IF duplicate_count > 0 THEN\n"
            "        RAISE_APPLICATION_ERROR(-20001, "
            "'cannot migrate DCIM floor nomenclature: duplicate levels exist in a building');\n"
            "    END IF;\n"
            "END;",
        )
    raise ConversionError("unsupported PostgreSQL DO block")


def _convert_comment(statement: str) -> tuple[str, ...]:
    del statement
    return ()


def convert_statement(statement: str, partition_counts: dict[str, int]) -> tuple[str, ...]:
    value = _strip_leading_comments(statement)
    if not value:
        return ()
    upper = value.upper()
    if upper in {"BEGIN;", "BEGIN", "COMMIT;", "COMMIT"}:
        return ()
    if upper.startswith("CREATE EXTENSION"):
        return ()
    if upper.startswith("CREATE TABLE") or upper.startswith("CREATE TEMP TABLE"):
        return _convert_create_table(value, partition_counts)
    if upper.startswith("ALTER TABLE"):
        return _convert_alter_table(value)
    if upper.startswith("CREATE INDEX") or upper.startswith("CREATE UNIQUE INDEX"):
        return _convert_index(value)
    if upper.startswith("INSERT"):
        return _convert_insert(value)
    if upper.startswith("UPDATE"):
        return _convert_update(value)
    if upper.startswith("DO $"):
        return _convert_do_block(value)
    if upper.startswith("COMMENT ON INDEX"):
        return _convert_comment(value)
    raise ConversionError("unsupported PostgreSQL statement: " + " ".join(value.split())[:180])


def _document_state_preamble() -> tuple[str, ...]:
    return (
        "CREATE TABLE openinfra_document_state (\n"
        "    state_key VARCHAR2(64 CHAR) PRIMARY KEY,\n"
        "    payload CLOB NOT NULL,\n"
        "    version NUMBER(19) DEFAULT 0 NOT NULL,\n"
        "    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,\n"
        "    CONSTRAINT ck_openinfra_state_payload CHECK (payload IS JSON)\n"
        ")",
        "MERGE INTO openinfra_document_state target\n"
        "USING (SELECT 'global' AS state_key, '{}' AS payload FROM dual) source\n"
        "ON (target.state_key = source.state_key)\n"
        "WHEN NOT MATCHED THEN INSERT (state_key, payload, version) "
        "VALUES (source.state_key, source.payload, 0)",
    )


def convert_migration(path: Path) -> ConvertedMigration:
    source = path.read_text(encoding="utf-8")
    partitions = _partition_counts(source)
    statements: list[str] = []
    if path.name.startswith("0001_"):
        statements.extend(_document_state_preamble())
    for source_statement in PostgreSQLStatementSplitter.split(source):
        statements.extend(convert_statement(source_statement, partitions))
    if path.name.startswith("0040_"):
        statements.append("DROP TABLE openinfra_floor_nomenclature_map")
    header = (
        "-- Generated deterministically from installers/migrations/postgresql/"
        f"{path.name}.\n"
        f"-- Source SHA-256: {_sha256(source)}\n"
        "-- Do not edit manually; run scripts/generate_oracle_migrations.py.\n\n"
    )
    rendered_parts: list[str] = []
    for statement in statements:
        stripped = statement.strip()
        if stripped.upper().startswith(("BEGIN", "DECLARE")):
            normalized = stripped if stripped.endswith(";") else stripped + ";"
            rendered_parts.append(normalized + "\n/")
        else:
            rendered_parts.append(stripped.rstrip(";") + ";")
    output = header + "\n\n".join(rendered_parts) + "\n"
    validate_payload(path.name, output)
    return ConvertedMigration(
        name=path.name,
        source_sha256=_sha256(source),
        oracle_sha256=_sha256(output),
        statement_count=len(statements),
        output=output,
    )


def _mask_string_literals(payload: str) -> str:
    output: list[str] = []
    single = False
    index = 0
    while index < len(payload):
        char = payload[index]
        nxt = payload[index + 1] if index + 1 < len(payload) else ""
        if single:
            output.append("\n" if char == "\n" else " ")
            if char == "'" and nxt == "'":
                output.append(" ")
                index += 2
                continue
            if char == "'":
                single = False
            index += 1
            continue
        if char == "'":
            output.append(" ")
            single = True
        else:
            output.append(char)
        index += 1
    return "".join(output)


def validate_payload(name: str, payload: str) -> None:
    scan_payload = _mask_string_literals(payload)
    for label, pattern in POSTGRESQL_RESIDUAL_PATTERNS:
        match = pattern.search(scan_payload)
        if match is not None:
            line = payload.count("\n", 0, match.start()) + 1
            raise ConversionError(f"{name}:{line}: {label} remains after conversion")
    for identifier in re.findall(
        r"\b(?:TABLE|INDEX|CONSTRAINT)\s+([A-Za-z_][A-Za-z0-9_]*)", payload, re.I
    ):
        if len(identifier.encode("utf-8")) > 128:
            raise ConversionError(f"{name}: Oracle identifier exceeds 128 bytes: {identifier}")
    if re.search(r"CREATE\s+(?:UNIQUE\s+)?INDEX\b[^;]*\b(?:CLOB|BLOB)\b", payload, re.I | re.S):
        raise ConversionError(f"{name}: Oracle LOB index is forbidden")


def _oracle_type_max_bytes(definition: str) -> int:
    upper = definition.upper()
    if re.search(r"\b(?:CLOB|BLOB)\b", upper):
        raise ConversionError("Oracle LOB cannot participate in a B-tree key")
    character = re.search(r"\b(?:VARCHAR2|CHAR)\s*\(\s*(\d+)\s+CHAR\s*\)", upper)
    if character is not None:
        return int(character.group(1)) * 4
    byte_value = re.search(r"\b(?:VARCHAR2|CHAR)\s*\(\s*(\d+)\s*\)", upper)
    if byte_value is not None:
        return int(byte_value.group(1))
    if "NUMBER" in upper:
        return 22
    if "TIMESTAMP" in upper:
        return 13
    if re.search(r"\bDATE\b", upper):
        return 7
    if "BINARY_DOUBLE" in upper:
        return 8
    if "BINARY_FLOAT" in upper:
        return 4
    raise ConversionError("unsupported Oracle index column type: " + definition.splitlines()[0])


def _catalog_table_definitions(payload: str) -> dict[str, dict[str, str]]:
    tables: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"CREATE\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", payload, re.I):
        table = match.group(1).lower()
        opening = payload.find("(", match.start())
        closing = _find_matching_parenthesis(payload, opening)
        columns: dict[str, str] = {}
        for part in _split_top_level(payload[opening + 1 : closing]):
            column = _column_name(part)
            if column is not None:
                columns[column] = part
        tables[table] = columns
    for match in re.finditer(
        r"ALTER\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s+ADD\s*\(\s*"
        r"(\"?[A-Za-z_][A-Za-z0-9_]*\"?)\s+(.+?)\)\s*;",
        payload,
        re.I | re.S,
    ):
        table = match.group(1).lower()
        column = match.group(2).strip('"').lower()
        definition = match.group(2) + " " + match.group(3)
        tables.setdefault(table, {})[column] = definition
    return tables


def _index_expression_bytes(expression: str, columns: dict[str, str], *, index_name: str) -> int:
    value = expression.strip()
    case_match = re.fullmatch(
        r"CASE\s+WHEN\s+.+?\s+THEN\s+(\"?[A-Za-z_][A-Za-z0-9_]*\"?)\s+END(?:\s+DESC)?",
        value,
        re.I | re.S,
    )
    if case_match is not None:
        value = case_match.group(1)
    json_match = re.fullmatch(
        r"\(?\s*JSON_VALUE\s*\(.+?\s+RETURNING\s+VARCHAR2\s*\(\s*(\d+)\s+CHAR\s*\)\s*\)\s*\)?(?:\s+DESC)?",
        value,
        re.I | re.S,
    )
    if json_match is not None:
        return int(json_match.group(1)) * 4
    column_match = re.fullmatch(
        r"\"?([A-Za-z_][A-Za-z0-9_]*)\"?(?:\s+(?:ASC|DESC))?",
        value,
        re.I,
    )
    if column_match is None:
        raise ConversionError(
            f"{index_name}: unsupported Oracle index expression: {' '.join(value.split())}"
        )
    column = column_match.group(1).lower()
    definition = columns.get(column)
    if definition is None:
        raise ConversionError(f"{index_name}: indexed column does not exist: {column}")
    try:
        return _oracle_type_max_bytes(definition)
    except ConversionError as exc:
        raise ConversionError(f"{index_name}: {exc}") from exc


def validate_catalog_structure(converted: list[ConvertedMigration]) -> None:
    payload = "\n".join(item.output for item in converted)
    tables = _catalog_table_definitions(payload)
    if not tables:
        raise ConversionError("Oracle catalog contains no tables")

    key_specs: list[tuple[str, str, str]] = []
    for match in re.finditer(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
        r"ON\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        payload,
        re.I,
    ):
        opening = payload.find("(", match.start())
        closing = _find_matching_parenthesis(payload, opening)
        key_specs.append((match.group(1), match.group(2), payload[opening + 1 : closing]))

    for table, _columns in tables.items():
        table_pattern = re.compile(rf"CREATE\s+TABLE\s+{re.escape(table)}\s*\(", re.I)
        match = table_pattern.search(payload)
        if match is None:
            continue
        opening = payload.find("(", match.start())
        closing = _find_matching_parenthesis(payload, opening)
        for part in _split_top_level(payload[opening + 1 : closing]):
            constraint = re.match(
                r"(?:CONSTRAINT\s+[A-Za-z_][A-Za-z0-9_]*\s+)?(?:PRIMARY\s+KEY|UNIQUE)\s*\((.+)\)$",
                part.strip(),
                re.I | re.S,
            )
            if constraint is not None:
                name = f"{table}:inline-key"
                key_specs.append((name, table, constraint.group(1)))

    for index_name, table_name, body in key_specs:
        columns = tables.get(table_name.lower())
        if columns is None:
            raise ConversionError(f"{index_name}: indexed table does not exist: {table_name}")
        expressions = _split_top_level(body)
        if len(expressions) > 32:
            raise ConversionError(f"{index_name}: Oracle index exceeds 32 columns")
        key_bytes = sum(
            _index_expression_bytes(expression, columns, index_name=index_name)
            for expression in expressions
        )
        if key_bytes > 6000:
            raise ConversionError(
                f"{index_name}: conservative Oracle index key size {key_bytes} exceeds 6000 bytes"
            )


def generate_catalog(
    source_root: Path, target_root: Path, *, check: bool
) -> list[ConvertedMigration]:
    source_paths = sorted(source_root.glob("[0-9][0-9][0-9][0-9]_*.sql"))
    if not source_paths:
        raise ConversionError(f"PostgreSQL migration catalog is empty: {source_root}")
    expected_versions = [f"{index:04d}" for index in range(1, len(source_paths) + 1)]
    actual_versions = [path.name.split("_", 1)[0] for path in source_paths]
    if actual_versions != expected_versions:
        raise ConversionError("PostgreSQL migration versions are not contiguous from 0001")
    converted = [convert_migration(path) for path in source_paths]
    validate_catalog_structure(converted)
    manifest = {
        "schema": "openinfra.oracle-migration-catalog/v1",
        "source": "postgresql",
        "target": "oracle-19c",
        "count": len(converted),
        "migrations": [
            {
                "version": item.name.split("_", 1)[0],
                "filename": item.name,
                "source_sha256": item.source_sha256,
                "oracle_sha256": item.oracle_sha256,
                "statement_count": item.statement_count,
            }
            for item in converted
        ],
    }
    manifest_payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if check:
        actual_paths = sorted(target_root.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        actual_names = [path.name for path in actual_paths]
        expected_names = [item.name for item in converted]
        if actual_names != expected_names:
            raise ConversionError(
                "Oracle migration filenames diverge from PostgreSQL: "
                f"expected {expected_names}, got {actual_names}"
            )
        for item in converted:
            actual = (target_root / item.name).read_text(encoding="utf-8")
            if actual != item.output:
                raise ConversionError(f"Oracle migration drift detected: {item.name}")
        manifest_path = target_root / "manifest.json"
        if (
            not manifest_path.is_file()
            or manifest_path.read_text(encoding="utf-8") != manifest_payload
        ):
            raise ConversionError("Oracle migration manifest drift detected")
        return converted
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)
    for item in converted:
        (target_root / item.name).write_text(item.output, encoding="utf-8", newline="\n")
    (target_root / "manifest.json").write_text(manifest_payload, encoding="utf-8", newline="\n")
    return converted


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "installers/migrations/postgresql",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=PROJECT_ROOT / "installers/migrations/oracle",
    )
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        converted = generate_catalog(args.source, args.target, check=args.check)
    except (ConversionError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    action = "validated" if args.check else "generated"
    print(f"Oracle migration catalog {action}: {len(converted)} migrations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
