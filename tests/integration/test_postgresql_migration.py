from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from openinfra.infrastructure.postgresql import (
    ConnectionProtocol,
    CursorProtocol,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLSessionRegistry,
    PostgreSQLStatementSplitter,
)

_IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
_SQL_IGNORED_IDENTIFIERS = frozenset(
    {
        "and",
        "array",
        "array_length",
        "between",
        "case",
        "check",
        "created_at",
        "default",
        "false",
        "in",
        "is",
        "like",
        "not",
        "null",
        "or",
        "pg_catalog",
        "text",
        "true",
    }
)


class _MigrationCursor(CursorProtocol):
    def __init__(self, connection: _MigrationConnection) -> None:
        self._connection = connection
        self._rows: list[Mapping[str, object]] = []
        self._row: Mapping[str, object] | None = None
        self.closed = False

    def execute(
        self,
        query: str,
        params: Mapping[str, object] | Sequence[object] | None = None,
    ) -> object:
        assert params is None or isinstance(params, Mapping)
        effective = dict(params or {})
        normalized = " ".join(query.split())
        self._connection.statements.append(normalized)
        if (
            "ALTER TABLE prefixes ADD COLUMN IF NOT EXISTS family smallint" in query
            and "UPDATE prefixes SET family" in query
        ):
            raise AssertionError("migration DDL and dependent DML must not share one execute call")
        if "CREATE TABLE IF NOT EXISTS openinfra_schema_migrations" in query:
            self._connection.history_created = True
        elif "FROM openinfra_schema_migrations" in query:
            self._rows = list(self._connection.applied.values())
        elif "INSERT INTO openinfra_schema_migrations" in query:
            version = str(effective["version"])
            self._connection.applied[version] = {
                "version": version,
                "checksum": str(effective["checksum"]),
                "applied_at": datetime.now(UTC),
            }
        return self

    def fetchone(self) -> Mapping[str, object] | None:
        return self._row

    def fetchall(self) -> Sequence[Mapping[str, object]]:
        return tuple(self._rows)

    def close(self) -> object:
        self.closed = True
        return None


class _MigrationConnection(ConnectionProtocol):
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.applied: dict[str, Mapping[str, object]] = {}
        self.history_created = False
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> CursorProtocol:
        return _MigrationCursor(self)

    def commit(self) -> object:
        self.commits += 1
        return None

    def rollback(self) -> object:
        self.rollbacks += 1
        return None

    def close(self) -> object:
        self.closed = True
        return None


class _MigrationConnector:
    def __init__(self) -> None:
        self.connection = _MigrationConnection()

    def connect(self, dsn: str, profile: PostgreSQLClusterProfile) -> ConnectionProtocol:
        assert dsn == "postgresql://openinfra@postgres/openinfra"
        assert "statement_timeout" in profile.dsn_options()
        return self.connection


def _migration_statements(path: Path) -> tuple[str, ...]:
    statements = []
    for statement in PostgreSQLStatementSplitter.split(path.read_text(encoding="utf-8")):
        if statement.upper() not in {"BEGIN;", "COMMIT;"}:
            statements.append(statement)
    return tuple(statements)


def _matching_parenthesized_value(sql: str, opening_index: int) -> str:
    depth = 0
    start = opening_index + 1
    for index, character in enumerate(sql[opening_index:], start=opening_index):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return sql[start:index]
    raise AssertionError("unbalanced SQL parenthesized expression")


def _split_top_level_csv(payload: str) -> tuple[str, ...]:
    parts: list[str] = []
    buffer: list[str] = []
    depth = 0
    for character in payload:
        if character == "(":
            depth += 1
        elif character == ")" and depth > 0:
            depth -= 1
        if character == "," and depth == 0:
            part = "".join(buffer).strip()
            if part:
                parts.append(part)
            buffer = []
            continue
        buffer.append(character)
    trailing = "".join(buffer).strip()
    if trailing:
        parts.append(trailing)
    return tuple(parts)


def _without_literals(sql: str) -> str:
    return re.sub(r"'([^']|'')*'", "''", sql)


def _referenced_identifiers(expression: str) -> set[str]:
    cleaned = _without_literals(expression)
    identifiers = {match.group(0).lower() for match in re.finditer(_IDENTIFIER, cleaned)}
    function_names = {
        match.group(1).lower() for match in re.finditer(rf"\b({_IDENTIFIER})\s*\(", cleaned)
    }
    qualified_names = set()
    for match in re.finditer(rf"\b({_IDENTIFIER})\.({_IDENTIFIER})\b", cleaned):
        qualified_names.add(match.group(1).lower())
        identifiers.add(match.group(2).lower())
    return identifiers - function_names - qualified_names - _SQL_IGNORED_IDENTIFIERS


def _record_create_table(statement: str, schema: dict[str, set[str]]) -> None:
    match = re.search(rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+({_IDENTIFIER})\b", statement, re.I)
    if match is None or " PARTITION OF " in statement.upper():
        return
    table = match.group(1).lower()
    opening_index = statement.find("(", match.end())
    if opening_index == -1:
        return
    body = _matching_parenthesized_value(statement, opening_index)
    columns = schema.setdefault(table, set())
    for item in _split_top_level_csv(body):
        column_match = re.match(rf"\s*({_IDENTIFIER})\b", item)
        if column_match is None:
            continue
        column = column_match.group(1).lower()
        if column in {"check", "constraint", "exclude", "foreign", "primary", "unique"}:
            continue
        columns.add(column)


def _record_added_column(statement: str, schema: dict[str, set[str]]) -> None:
    table_match = re.search(rf"ALTER\s+TABLE\s+({_IDENTIFIER})\b", statement, re.I)
    if table_match is None:
        return
    table = table_match.group(1).lower()
    for column_match in re.finditer(
        rf"ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+({_IDENTIFIER})\b",
        statement,
        re.I,
    ):
        schema.setdefault(table, set()).add(column_match.group(1).lower())


def _assert_update_columns_exist(statement: str, schema: Mapping[str, set[str]]) -> None:
    match = re.search(
        rf"UPDATE\s+({_IDENTIFIER})\s+SET\s+(.+?)(?:\s+WHERE\s+|;)", statement, re.I | re.S
    )
    if match is None:
        return
    table = match.group(1).lower()
    assert table in schema, f"UPDATE references unknown table {table}"
    assignments = _split_top_level_csv(match.group(2))
    for assignment in assignments:
        column_match = re.match(rf"\s*(?:{_IDENTIFIER}\.)?({_IDENTIFIER})\s*=", assignment, re.I)
        assert column_match is not None, f"unsupported UPDATE assignment: {assignment}"
        column = column_match.group(1).lower()
        assert column in schema[table], f"UPDATE {table} references unknown column {column}"


def _assert_index_columns_exist(statement: str, schema: Mapping[str, set[str]]) -> None:
    match = re.search(rf"ON\s+({_IDENTIFIER})\s+(?:USING\s+{_IDENTIFIER}\s+)?\(", statement, re.I)
    if match is None or "CREATE INDEX" not in statement.upper():
        return
    table = match.group(1).lower()
    assert table in schema, f"INDEX references unknown table {table}"
    opening_index = statement.find("(", match.end() - 1)
    columns = _matching_parenthesized_value(statement, opening_index)
    for expression in _split_top_level_csv(columns):
        normalized = re.sub(
            r"\s+(ASC|DESC|NULLS\s+(FIRST|LAST))\b", "", expression, flags=re.I
        ).strip()
        if re.fullmatch(_IDENTIFIER, normalized):
            assert normalized.lower() in schema[table], (
                f"INDEX on {table} references unknown column {normalized}"
            )
    where_match = re.search(r"\bWHERE\b(.+);?$", statement, re.I | re.S)
    if where_match is not None:
        missing = _referenced_identifiers(where_match.group(1)) - schema[table]
        assert not missing, f"INDEX predicate on {table} references unknown columns {missing}"


def _assert_constraint_columns_exist(statement: str, schema: Mapping[str, set[str]]) -> None:
    match = re.search(rf"ALTER\s+TABLE\s+({_IDENTIFIER})\s+ADD\s+CONSTRAINT\b", statement, re.I)
    if match is None or " CHECK " not in statement.upper():
        return
    table = match.group(1).lower()
    assert table in schema, f"CONSTRAINT references unknown table {table}"
    opening_index = statement.upper().find("CHECK", match.end())
    opening_index = statement.find("(", opening_index)
    expression = _matching_parenthesized_value(statement, opening_index)
    missing = _referenced_identifiers(expression) - schema[table]
    assert not missing, f"CONSTRAINT on {table} references unknown columns {missing}"


class TestPostgreSQLMigration:
    def test_bootstrap_migration_is_partitioned_indexed_and_audited(self) -> None:
        migration = PostgreSQLMigrationCatalog.from_project_root().load("0001_bootstrap")

        assert "PARTITION BY HASH" in migration.sql
        assert "PARTITION BY RANGE" in migration.sql
        assert "CREATE INDEX" in migration.sql
        assert "audit_events" in migration.sql

    def test_statement_splitter_preserves_plpgsql_blocks_and_splits_dependent_ddl(self) -> None:
        statements = _migration_statements(
            Path("migrations/postgresql/0015_ipam_enterprise_foundation.sql")
        )

        assert any(statement.startswith("DO $$") for statement in statements)
        assert any("ADD COLUMN IF NOT EXISTS family" in statement for statement in statements)
        assert any("UPDATE prefixes SET family" in statement for statement in statements)
        assert all(
            not (
                "ADD COLUMN IF NOT EXISTS family" in statement
                and "UPDATE prefixes SET family" in statement
            )
            for statement in statements
        )

    def test_executor_applies_migrations_statement_by_statement_before_history_insert(self) -> None:
        connector = _MigrationConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@postgres/openinfra",
                connector=connector.connect,
            )
        )
        executor = PostgreSQLMigrationExecutor(
            registry, PostgreSQLMigrationCatalog.from_project_root()
        )

        status = executor.apply_all()
        statements = connector.connection.statements
        add_family_index = next(
            index
            for index, statement in enumerate(statements)
            if "ALTER TABLE prefixes ADD COLUMN IF NOT EXISTS family smallint" in statement
        )
        update_family_index = next(
            index
            for index, statement in enumerate(statements)
            if "UPDATE prefixes SET family" in statement
        )
        not_null_index = next(
            index
            for index, statement in enumerate(statements)
            if "ALTER TABLE prefixes ALTER COLUMN family SET NOT NULL" in statement
        )

        assert status.ready is True
        assert len(connector.connection.applied) == 21
        assert connector.connection.commits == 1
        assert connector.connection.rollbacks == 0
        assert add_family_index < update_family_index < not_null_index

    def test_all_postgresql_migrations_reference_known_columns_in_order(self) -> None:
        schema: dict[str, set[str]] = {}
        migration_paths = sorted(Path("migrations/postgresql").glob("*.sql"))

        assert [path.name[:4] for path in migration_paths] == [
            f"{index:04d}" for index in range(1, 22)
        ]
        for path in migration_paths:
            for statement in _migration_statements(path):
                _record_create_table(statement, schema)
                _record_added_column(statement, schema)
                _assert_update_columns_exist(statement, schema)
                _assert_constraint_columns_exist(statement, schema)
                _assert_index_columns_exist(statement, schema)

        assert "family" in schema["prefixes"]
        assert "family" in schema["ip_aggregates"]
        assert "address_family" in schema["ipam_bgp_peers"]
        assert "dlq" in schema["import_jobs"]
        assert "metrics" in schema["bulk_import_jobs"]
        assert "next_row_number" in schema["bulk_import_checkpoints"]
        assert "artifact" in schema["export_jobs"]
        assert "content" in schema["export_artifacts"]
        assert "secret_hex" in schema["export_signing_keys"]
