from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from openinfra.domain.common import Pagination, ValidationError
from openinfra.infrastructure.cursor_pagination import (
    CursorDirection,
    CursorField,
    CursorTokenCodec,
    CursorValueType,
    PostgreSQLKeysetPage,
)

KEY_MATERIAL = "cursor-secret-material-for-openinfra-tests-0001"


def test_cursor_codec_is_deterministic_signed_and_bound_to_scope_and_filters() -> None:
    codec = CursorTokenCodec(KEY_MATERIAL)
    fields = (
        CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
        CursorField("id", CursorDirection.DESC),
    )
    row = {"created_at": datetime(2026, 7, 12, 10, 30, tzinfo=UTC), "id": "row-002"}
    filters = {"tenant_id": "tenant-a", "active": True, "tags": ["a", "b"]}

    first = codec.encode("security.audit-events", filters, fields, row)
    second = codec.encode("security.audit-events", filters, fields, row)

    assert first == second
    assert first.count(".") == 1
    assert codec.decode(first, "security.audit-events", filters, fields) == (
        row["created_at"],
        "row-002",
    )

    with pytest.raises(ValidationError, match="signature"):
        codec.decode(
            first[:-1] + ("A" if first[-1] != "A" else "B"),
            "security.audit-events",
            filters,
            fields,
        )
    with pytest.raises(ValidationError, match="scope"):
        codec.decode(first, "security.api-tokens", filters, fields)
    with pytest.raises(ValidationError, match="filters"):
        codec.decode(first, "security.audit-events", {**filters, "active": False}, fields)


def test_cursor_codec_validates_secret_payload_and_supported_types() -> None:
    with pytest.raises(ValidationError, match="32"):
        CursorTokenCodec("short")
    with pytest.raises(ValidationError, match="field name"):
        CursorField("created-at")

    codec = CursorTokenCodec(KEY_MATERIAL)
    fields = (
        CursorField("priority", value_type=CursorValueType.INTEGER),
        CursorField("score", CursorDirection.DESC, CursorValueType.FLOAT),
        CursorField("enabled", value_type=CursorValueType.BOOLEAN),
        CursorField("period_start", CursorDirection.DESC, CursorValueType.DATE),
    )
    row = {
        "priority": 4,
        "score": 9.5,
        "enabled": True,
        "period_start": date(2026, 7, 1),
    }
    token = codec.encode("finops.cost-records", {"tenant_id": "tenant-a"}, fields, row)
    assert codec.decode(token, "finops.cost-records", {"tenant_id": "tenant-a"}, fields) == (
        4,
        9.5,
        True,
        date(2026, 7, 1),
    )

    for invalid in ("", "x" * 4097, "missing-separator", "%%%.%%"):
        with pytest.raises(ValidationError, match="cursor"):
            codec.decode(invalid, "finops.cost-records", {"tenant_id": "tenant-a"}, fields)


def test_keyset_page_builds_mixed_direction_lexicographic_predicate() -> None:
    codec = CursorTokenCodec(KEY_MATERIAL)
    fields = (
        CursorField("priority", CursorDirection.DESC, CursorValueType.INTEGER),
        CursorField("name"),
        CursorField("id"),
    )
    filters = {"tenant_id": "tenant-a", "object_kind": "server"}
    cursor = codec.encode(
        "rsot.source-governance-rules",
        filters,
        fields,
        {"priority": 90, "name": "authoritative", "id": "rule-1"},
    )
    page = PostgreSQLKeysetPage.create(
        Pagination.from_values(100, cursor),
        scope="rsot.source-governance-rules",
        tenant_id="tenant-a",
        filters={"object_kind": "server"},
        fields=fields,
        codec=codec,
    )

    assert page.where_sql == (
        "AND ((priority < %(cursor_0)s) OR "
        "(priority = %(cursor_0)s AND name > %(cursor_1)s) OR "
        "(priority = %(cursor_0)s AND name = %(cursor_1)s AND id > %(cursor_2)s))"
    )
    assert page.offset_sql == ""
    assert page.parameters == {
        "fetch_limit": 101,
        "cursor_0": 90,
        "cursor_1": "authoritative",
        "cursor_2": "rule-1",
    }


def test_keyset_page_emits_opaque_cursor_and_accepts_legacy_numeric_offset() -> None:
    codec = CursorTokenCodec(KEY_MATERIAL)
    fields = (CursorField("object_key"),)
    rows = [
        {"object_key": "asset-001"},
        {"object_key": "asset-002"},
        {"object_key": "asset-003"},
    ]
    page = PostgreSQLKeysetPage.create(
        Pagination.from_values(2),
        scope="rsot.source-objects",
        tenant_id="tenant-a",
        filters={"kind": None},
        fields=fields,
        codec=codec,
    )
    next_cursor = page.next_cursor(rows)
    assert next_cursor is not None and not next_cursor.isdigit()

    resumed = PostgreSQLKeysetPage.create(
        Pagination.from_values(2, next_cursor),
        scope="rsot.source-objects",
        tenant_id="tenant-a",
        filters={"kind": None},
        fields=fields,
        codec=codec,
    )
    assert resumed.where_sql == "AND ((object_key > %(cursor_0)s))"
    assert resumed.parameters["cursor_0"] == "asset-002"

    legacy = PostgreSQLKeysetPage.create(
        Pagination.from_values(2, "500000"),
        scope="rsot.source-objects",
        tenant_id="tenant-a",
        filters={"kind": None},
        fields=fields,
        codec=codec,
    )
    assert legacy.where_sql == ""
    assert legacy.offset_sql == " OFFSET %(legacy_offset)s"
    assert legacy.parameters["legacy_offset"] == 500000
    migrated_cursor = legacy.next_cursor(rows)
    assert migrated_cursor is not None and not migrated_cursor.isdigit()


def test_keyset_page_keeps_numeric_cursor_only_without_signing_codec() -> None:
    page = PostgreSQLKeysetPage.create(
        Pagination.from_values(2),
        scope="rsot.source-objects",
        tenant_id="tenant-a",
        filters={},
        fields=(CursorField("object_key"),),
        codec=None,
    )
    assert page.next_cursor([{"object_key": "a"}, {"object_key": "b"}, {"object_key": "c"}]) == "2"
    with pytest.raises(ValidationError, match="signing secret"):
        PostgreSQLKeysetPage.create(
            Pagination.from_values(2, "opaque.cursor"),
            scope="rsot.source-objects",
            tenant_id="tenant-a",
            filters={},
            fields=(CursorField("object_key"),),
            codec=None,
        )


def test_cursor_fields_reject_invalid_values_and_round_trip_scalars() -> None:
    timestamp = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)
    day = date(2026, 7, 12)
    assert (
        CursorField("timestamp", value_type=CursorValueType.DATETIME).decode(timestamp.isoformat())
        == timestamp
    )
    assert CursorField("day", value_type=CursorValueType.DATE).decode(day.isoformat()) == day
    assert CursorField("count", value_type=CursorValueType.INTEGER).encode("12") == 12
    assert CursorField("ratio", value_type=CursorValueType.FLOAT).encode("1.25") == 1.25
    assert CursorField("active", value_type=CursorValueType.BOOLEAN).encode(True) is True
    assert CursorField("label").encode(123) == "123"

    cases = (
        (CursorField("timestamp", value_type=CursorValueType.DATETIME), "not-a-datetime"),
        (CursorField("day", value_type=CursorValueType.DATE), "not-a-date"),
        (CursorField("count", value_type=CursorValueType.INTEGER), True),
        (CursorField("ratio", value_type=CursorValueType.FLOAT), True),
        (CursorField("active", value_type=CursorValueType.BOOLEAN), "true"),
        (CursorField("label"), 12),
    )
    for field, value in cases:
        with pytest.raises(ValidationError, match="cursor field"):
            field.decode(value)
    with pytest.raises(ValidationError, match="cannot be null"):
        CursorField("label").encode(None)
    with pytest.raises(ValidationError, match="datetime"):
        CursorField("timestamp", value_type=CursorValueType.DATETIME).encode("bad")
    with pytest.raises(ValidationError, match="date"):
        CursorField("day", value_type=CursorValueType.DATE).encode(timestamp)
    with pytest.raises(ValidationError, match="integer"):
        CursorField("count", value_type=CursorValueType.INTEGER).encode(True)
    with pytest.raises(ValidationError, match="integer"):
        CursorField("count", value_type=CursorValueType.INTEGER).encode("not-an-integer")
    with pytest.raises(ValidationError, match="float"):
        CursorField("ratio", value_type=CursorValueType.FLOAT).encode(False)
    with pytest.raises(ValidationError, match="float"):
        CursorField("ratio", value_type=CursorValueType.FLOAT).encode("not-a-float")
    with pytest.raises(ValidationError, match="boolean"):
        CursorField("active", value_type=CursorValueType.BOOLEAN).encode(1)


def test_cursor_codec_rejects_signed_payload_with_invalid_shape() -> None:
    codec = CursorTokenCodec(KEY_MATERIAL)
    fields = (CursorField("id"),)
    valid = codec.encode("rsot.source-objects", {"tenant_id": "tenant-a"}, fields, {"id": "a"})
    encoded_payload, _ = valid.split(".", 1)
    payload = CursorTokenCodec._decode_segment(encoded_payload)

    def signed(value: object) -> str:
        import hashlib
        import hmac
        import json

        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            KEY_MATERIAL.encode("utf-8"), CursorTokenCodec._domain + raw, hashlib.sha256
        ).digest()
        return (
            CursorTokenCodec._encode_segment(raw)
            + "."
            + CursorTokenCodec._encode_segment(signature)
        )

    assert payload
    with pytest.raises(ValidationError, match="payload"):
        codec.decode(signed([1]), "rsot.source-objects", {"tenant_id": "tenant-a"}, fields)
    with pytest.raises(ValidationError, match="scope"):
        codec.decode(
            signed({"v": 99, "s": "rsot.source-objects", "f": "x", "p": ["a"]}),
            "rsot.source-objects",
            {"tenant_id": "tenant-a"},
            fields,
        )
    fingerprint = CursorTokenCodec._filter_fingerprint({"tenant_id": "tenant-a"})
    with pytest.raises(ValidationError, match="position"):
        codec.decode(
            signed({"v": 1, "s": "rsot.source-objects", "f": fingerprint, "p": []}),
            "rsot.source-objects",
            {"tenant_id": "tenant-a"},
            fields,
        )
    with pytest.raises(ValidationError, match="scope"):
        codec.encode("invalid scope!", {}, fields, {"id": "a"})


def test_keyset_page_validates_fields_and_terminal_pages() -> None:
    codec = CursorTokenCodec(KEY_MATERIAL)
    with pytest.raises(ValidationError, match="at least one"):
        PostgreSQLKeysetPage.create(
            Pagination.from_values(2),
            scope="rsot.source-objects",
            tenant_id="tenant-a",
            filters={},
            fields=(),
            codec=codec,
        )
    page = PostgreSQLKeysetPage.create(
        Pagination.from_values(2),
        scope="rsot.source-objects",
        tenant_id="tenant-a",
        filters={},
        fields=(CursorField("id"),),
        codec=codec,
    )
    assert page.next_cursor([]) is None
    assert page.next_cursor([{"id": "a"}, {"id": "b"}]) is None
