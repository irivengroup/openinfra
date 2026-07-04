from __future__ import annotations

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.ipam import (
    DdiChange,
    DdiDivergence,
    DdiProvider,
    DdiReservationPreview,
)


def test_ddi_change_normalizes_metadata_and_compensation() -> None:
    change = DdiChange.create(
        "bind",
        "upsert",
        "dns_forward",
        "srv.example.net",
        "10.0.0.10",
        300,
        {"record_type": "A"},
    )
    rollback = change.compensating()

    assert change.provider == DdiProvider.BIND
    assert change.as_dict()["metadata"] == {"record_type": "A"}
    assert rollback.action.value == "delete"
    assert rollback.as_dict()["metadata"]["compensates"] == "upsert"


def test_ddi_preview_safe_to_apply_requires_changes_and_no_blocking_divergence() -> None:
    tenant = TenantId.from_value("default")
    change = DdiChange.create("powerdns", "upsert", "dns_reverse", "1.0.0.10.in-addr.arpa", "srv")
    warning = DdiDivergence.create("warning", "informational", "srv", ("warning",), "review")
    error = DdiDivergence.create("error", "blocked", "srv", ("error",), "fix")

    safe = DdiReservationPreview.create(
        tenant, "prod", "key-1", (DdiProvider.POWERDNS,), True, (change,), (warning,)
    )
    blocked = DdiReservationPreview.create(
        tenant, "prod", "key-2", (DdiProvider.POWERDNS,), True, (change,), (error,)
    )
    empty = DdiReservationPreview.create(
        tenant, "prod", "key-3", (DdiProvider.POWERDNS,), True, (), ()
    )

    assert safe.safe_to_apply is True
    assert blocked.safe_to_apply is False
    assert empty.safe_to_apply is False


@pytest.mark.parametrize(
    ("name", "value", "ttl"),
    [("", "10.0.0.1", 300), ("srv", "", 300), ("srv", "10.0.0.1", 86401)],
)
def test_ddi_change_rejects_invalid_values(name: str, value: str, ttl: int) -> None:
    with pytest.raises(ValidationError):
        DdiChange.create("bind", "upsert", "dns_forward", name, value, ttl)


def test_ddi_enums_reject_unknown_values() -> None:
    from openinfra.domain.ipam import DdiAction, DdiRecordKind

    with pytest.raises(ValidationError):
        DdiProvider.from_value("unknown")
    with pytest.raises(ValidationError):
        DdiAction.from_value("replace")
    with pytest.raises(ValidationError):
        DdiRecordKind.from_value("txt")


def test_ddi_change_accepts_enum_instances_and_delete_compensation() -> None:
    from openinfra.domain.ipam import DdiAction, DdiRecordKind

    change = DdiChange.create(
        DdiProvider.KEA,
        DdiAction.DELETE,
        DdiRecordKind.DHCP_RESERVATION,
        "kea:1:aa:bb:cc:dd:ee:ff",
        "10.0.0.5",
        0,
    )

    assert change.compensating().action == DdiAction.UPSERT


@pytest.mark.parametrize(
    ("kind", "target", "evidence", "action"),
    [
        ("", "target", ("evidence",), "fix"),
        ("kind", "", ("evidence",), "fix"),
        ("kind", "target", (), "fix"),
        ("kind", "target", ("evidence",), ""),
    ],
)
def test_ddi_divergence_rejects_incomplete_values(
    kind: str, target: str, evidence: tuple[str, ...], action: str
) -> None:
    with pytest.raises(ValidationError):
        DdiDivergence.create("warning", kind, target, evidence, action)


def test_ddi_preview_rejects_missing_identity_or_provider() -> None:
    tenant = TenantId.from_value("default")
    with pytest.raises(ValidationError):
        DdiReservationPreview.create(tenant, "prod", "", (DdiProvider.BIND,), True, (), ())
    with pytest.raises(ValidationError):
        DdiReservationPreview.create(tenant, "prod", "key", (), True, (), ())
