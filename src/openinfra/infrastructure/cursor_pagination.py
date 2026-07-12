from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from openinfra.domain.common import Pagination, ValidationError


class CursorDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class CursorValueType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"


@dataclass(frozen=True, slots=True)
class CursorField:
    name: str
    direction: CursorDirection = CursorDirection.ASC
    value_type: CursorValueType = CursorValueType.STRING

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z_][a-z0-9_]*", self.name) is None:
            raise ValidationError("cursor field name is invalid")

    @property
    def comparison_operator(self) -> str:
        return ">" if self.direction is CursorDirection.ASC else "<"

    def encode(self, value: object) -> object:
        if value is None:
            raise ValidationError(f"cursor field {self.name} cannot be null")
        if self.value_type is CursorValueType.DATETIME:
            if not isinstance(value, datetime):
                raise ValidationError(f"cursor field {self.name} must be a datetime")
            return value.isoformat()
        if self.value_type is CursorValueType.DATE:
            if not isinstance(value, date) or isinstance(value, datetime):
                raise ValidationError(f"cursor field {self.name} must be a date")
            return value.isoformat()
        if self.value_type is CursorValueType.INTEGER:
            if isinstance(value, bool):
                raise ValidationError(f"cursor field {self.name} must be an integer")
            try:
                return int(str(value))
            except ValueError as exc:
                raise ValidationError(f"cursor field {self.name} must be an integer") from exc
        if self.value_type is CursorValueType.FLOAT:
            if isinstance(value, bool):
                raise ValidationError(f"cursor field {self.name} must be a float")
            try:
                return float(str(value))
            except ValueError as exc:
                raise ValidationError(f"cursor field {self.name} must be a float") from exc
        if self.value_type is CursorValueType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValidationError(f"cursor field {self.name} must be a boolean")
            return value
        return str(value)

    def decode(self, value: object) -> object:
        if self.value_type is CursorValueType.DATETIME:
            if not isinstance(value, str):
                raise ValidationError(f"cursor field {self.name} is invalid")
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError(f"cursor field {self.name} is invalid") from exc
        if self.value_type is CursorValueType.DATE:
            if not isinstance(value, str):
                raise ValidationError(f"cursor field {self.name} is invalid")
            try:
                return date.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError(f"cursor field {self.name} is invalid") from exc
        if self.value_type is CursorValueType.INTEGER:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"cursor field {self.name} is invalid")
            return value
        if self.value_type is CursorValueType.FLOAT:
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValidationError(f"cursor field {self.name} is invalid")
            return float(value)
        if self.value_type is CursorValueType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValidationError(f"cursor field {self.name} is invalid")
            return value
        if not isinstance(value, str):
            raise ValidationError(f"cursor field {self.name} is invalid")
        return value


class CursorTokenCodec:
    _version = 1
    _domain = b"openinfra:keyset-cursor:v1\x00"
    _maximum_token_length = 4096

    def __init__(self, secret: str) -> None:
        normalized = secret.strip()
        if len(normalized) < 32:
            raise ValidationError("cursor signing secret must contain at least 32 characters")
        self._secret = normalized.encode("utf-8")

    def encode(
        self,
        scope: str,
        filters: Mapping[str, object],
        fields: Sequence[CursorField],
        row: Mapping[str, object],
    ) -> str:
        normalized_scope = self._scope(scope)
        values = [field.encode(row[field.name]) for field in fields]
        payload = json.dumps(
            {
                "v": self._version,
                "s": normalized_scope,
                "f": self._filter_fingerprint(filters),
                "p": values,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(self._secret, self._domain + payload, hashlib.sha256).digest()
        return self._encode_segment(payload) + "." + self._encode_segment(signature)

    def decode(
        self,
        token: str,
        scope: str,
        filters: Mapping[str, object],
        fields: Sequence[CursorField],
    ) -> tuple[object, ...]:
        normalized = token.strip()
        if not normalized or len(normalized) > self._maximum_token_length:
            raise ValidationError("pagination cursor is invalid")
        try:
            encoded_payload, encoded_signature = normalized.split(".", 1)
            payload = self._decode_segment(encoded_payload)
            signature = self._decode_segment(encoded_signature)
            decoded = json.loads(payload)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("pagination cursor is invalid") from exc
        expected = hmac.new(self._secret, self._domain + payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValidationError("pagination cursor signature is invalid")
        if not isinstance(decoded, dict):
            raise ValidationError("pagination cursor payload is invalid")
        if decoded.get("v") != self._version or decoded.get("s") != self._scope(scope):
            raise ValidationError("pagination cursor scope is invalid")
        if decoded.get("f") != self._filter_fingerprint(filters):
            raise ValidationError("pagination cursor filters do not match the request")
        positions = decoded.get("p")
        if not isinstance(positions, list) or len(positions) != len(fields):
            raise ValidationError("pagination cursor position is invalid")
        return tuple(field.decode(value) for field, value in zip(fields, positions, strict=True))

    @classmethod
    def _scope(cls, value: str) -> str:
        normalized = value.strip().lower()
        if re.fullmatch(r"[a-z0-9_.:-]{3,160}", normalized) is None:
            raise ValidationError("pagination cursor scope is invalid")
        return normalized

    @classmethod
    def _filter_fingerprint(cls, filters: Mapping[str, object]) -> str:
        canonical = cls._canonical_value(dict(filters))
        encoded = json.dumps(
            canonical,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _canonical_value(cls, value: object) -> object:
        if value is None or isinstance(value, str | int | float | bool):
            return value
        if isinstance(value, datetime | date):
            return value.isoformat()
        if isinstance(value, Mapping):
            return {
                str(key): cls._canonical_value(item)
                for key, item in sorted(value.items(), key=lambda item: str(item[0]))
            }
        if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray | str):
            return [cls._canonical_value(item) for item in value]
        return str(value)

    @staticmethod
    def _encode_segment(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_segment(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)


@dataclass(frozen=True, slots=True)
class PostgreSQLKeysetPage:
    pagination: Pagination
    scope: str
    tenant_id: str
    filters: Mapping[str, object]
    fields: tuple[CursorField, ...]
    codec: CursorTokenCodec | None
    position: tuple[object, ...] | None
    legacy_offset: int | None

    @classmethod
    def create(
        cls,
        pagination: Pagination,
        *,
        scope: str,
        tenant_id: str,
        filters: Mapping[str, object],
        fields: Sequence[CursorField],
        codec: CursorTokenCodec | None,
    ) -> PostgreSQLKeysetPage:
        normalized_fields = tuple(fields)
        if not normalized_fields:
            raise ValidationError("keyset pagination requires at least one cursor field")
        cursor = pagination.cursor
        if cursor is None:
            return cls(
                pagination,
                scope,
                tenant_id,
                dict(filters),
                normalized_fields,
                codec,
                None,
                None,
            )
        if re.fullmatch(r"[0-9]+", cursor):
            offset = int(cursor)
            return cls(
                pagination,
                scope,
                tenant_id,
                dict(filters),
                normalized_fields,
                codec,
                None,
                offset,
            )
        if codec is None:
            raise ValidationError("opaque pagination cursors require a configured signing secret")
        cursor_filters = {"tenant_id": tenant_id, **dict(filters)}
        position = codec.decode(cursor, scope, cursor_filters, normalized_fields)
        return cls(
            pagination,
            scope,
            tenant_id,
            dict(filters),
            normalized_fields,
            codec,
            position,
            None,
        )

    @property
    def where_sql(self) -> str:
        if self.position is None:
            return ""
        terms: list[str] = []
        for index, field in enumerate(self.fields):
            equalities = [
                f"{previous.name} = %(cursor_{previous_index})s"
                for previous_index, previous in enumerate(self.fields[:index])
            ]
            comparison = f"{field.name} {field.comparison_operator} %(cursor_{index})s"
            terms.append("(" + " AND ".join([*equalities, comparison]) + ")")
        return "AND (" + " OR ".join(terms) + ")"

    @property
    def offset_sql(self) -> str:
        return " OFFSET %(legacy_offset)s" if self.legacy_offset is not None else ""

    @property
    def parameters(self) -> dict[str, object]:
        params: dict[str, object] = {"fetch_limit": self.pagination.limit + 1}
        if self.position is not None:
            params.update({f"cursor_{index}": value for index, value in enumerate(self.position)})
        if self.legacy_offset is not None:
            params["legacy_offset"] = self.legacy_offset
        return params

    def next_cursor(self, rows: Sequence[Mapping[str, object]]) -> str | None:
        if len(rows) <= self.pagination.limit:
            return None
        selected = rows[: self.pagination.limit]
        if not selected:
            return None
        if self.codec is None:
            offset = self.legacy_offset or 0
            return str(offset + self.pagination.limit)
        cursor_filters = {"tenant_id": self.tenant_id, **dict(self.filters)}
        return self.codec.encode(self.scope, cursor_filters, self.fields, selected[-1])
