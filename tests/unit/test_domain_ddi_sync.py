from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.ddi_sync import (
    DdiExecutionJournal,
    DdiExecutionStatus,
    DdiMutationOutcome,
    DdiMutationReceipt,
)
from openinfra.domain.ipam import DdiChange, DdiProvider


def _change(provider: str = "bind", name: str = "srv.example.net") -> DdiChange:
    return DdiChange.create(
        provider,
        "upsert",
        "dns_forward" if provider != "kea" else "dhcp_reservation",
        name,
        "10.0.0.10",
        300 if provider != "kea" else 0,
        {"record_type": "A", "zone": "example.net"},
    )


def _journal() -> DdiExecutionJournal:
    return DdiExecutionJournal.create(
        TenantId.from_value("default"),
        "prod",
        "reservation-key",
        "execution-key",
        hashlib.sha256(b"request").hexdigest(),
        (DdiProvider.BIND,),
        datetime(2026, 7, 22, tzinfo=UTC),
    )


def test_ddi_execution_success_round_trip() -> None:
    change = _change()
    receipt = DdiMutationReceipt.create(1, change, change.compensating(), "bind:ref")
    journal = _journal().start().record_receipt(receipt).succeed()
    restored = DdiExecutionJournal.restore(journal.as_dict())

    assert journal.status is DdiExecutionStatus.SUCCEEDED
    assert journal.terminal is True
    assert restored == journal
    assert restored.as_dict()["receipt_count"] == 1


def test_ddi_execution_compensation_requires_every_applied_receipt() -> None:
    change = _change()
    receipt = DdiMutationReceipt.create(1, change, change.compensating(), "bind:ref")
    journal = _journal().start().record_receipt(receipt).begin_compensation("provider failed")

    with pytest.raises(ValidationError, match="uncompensated"):
        journal.compensated()

    compensated = journal.mark_receipt_compensated(1, "bind:rollback").compensated()
    assert compensated.status is DdiExecutionStatus.COMPENSATED
    assert compensated.receipts[0].compensation_reference == "bind:rollback"


def test_unknown_outcome_stays_fail_closed_after_successful_rollback() -> None:
    change = _change()
    receipt = DdiMutationReceipt.create(
        1,
        change,
        change.compensating(),
        "bind:unknown",
        DdiMutationOutcome.UNKNOWN,
    )
    result = (
        _journal()
        .start()
        .record_receipt(receipt)
        .begin_compensation("timeout")
        .mark_receipt_compensated(1, "bind:rollback")
        .compensated()
    )

    assert result.status is DdiExecutionStatus.COMPENSATION_FAILED
    assert result.reconciliation_required is True


def test_ddi_execution_rejects_key_reuse_and_invalid_sequences() -> None:
    journal = _journal().start()
    journal.ensure_same_request(hashlib.sha256(b"request").hexdigest())
    with pytest.raises(ValidationError, match="different request"):
        journal.ensure_same_request(hashlib.sha256(b"other").hexdigest())

    change = _change()
    with pytest.raises(ValidationError, match="sequence must be 1"):
        journal.record_receipt(
            DdiMutationReceipt.create(2, change, change.compensating(), "bind:ref")
        )


def test_ddi_execution_timestamps_and_restore_validation_are_strict() -> None:
    journal = _journal().start()
    with pytest.raises(ValidationError, match="move backwards"):
        journal.fail_without_effect(
            "failure", now=datetime(2026, 7, 21, tzinfo=UTC)
        )

    payload = journal.as_dict()
    payload["request_fingerprint"] = "invalid"
    with pytest.raises(ValidationError, match="SHA-256"):
        DdiExecutionJournal.restore(payload)

    payload = journal.as_dict()
    payload["updated_at"] = (journal.created_at - timedelta(seconds=1)).isoformat()
    with pytest.raises(ValidationError, match="precede"):
        DdiExecutionJournal.restore(payload)


def test_receipt_restore_rejects_inconsistent_compensation_state() -> None:
    change = _change()
    receipt = DdiMutationReceipt.create(1, change, change.compensating(), "bind:ref")
    payload = receipt.as_dict()
    payload["compensation_reference"] = "orphan"
    with pytest.raises(ValidationError, match="uncompensated"):
        DdiMutationReceipt.restore(payload)


def test_ddi_execution_validation_and_state_machine_edges_are_fail_closed() -> None:
    from dataclasses import replace

    from openinfra.domain.ipam import DdiAction, DdiRecordKind

    for parser, value, message in (
        (DdiExecutionStatus.from_value, "unknown", "status is invalid"),
        (DdiMutationOutcome.from_value, "unknown-value", "outcome is invalid"),
    ):
        with pytest.raises(ValidationError, match=message):
            parser(value)

    bind = _change()
    kea = _change("kea", "srv")
    with pytest.raises(ValidationError, match="sequence must be positive"):
        DdiMutationReceipt.create(0, bind, bind.compensating(), "bind:ref")
    with pytest.raises(ValidationError, match="provider reference is mandatory"):
        DdiMutationReceipt.create(1, bind, bind.compensating(), "   ")
    with pytest.raises(ValidationError, match="rollback provider"):
        DdiMutationReceipt.create(1, bind, kea, "bind:ref")
    with pytest.raises(ValidationError, match="timezone-aware"):
        DdiMutationReceipt.create(
            1, bind, bind.compensating(), "bind:ref", recorded_at=datetime(2026, 7, 22)
        )

    receipt = DdiMutationReceipt.create(1, bind, bind.compensating(), "bind:ref")
    with pytest.raises(ValidationError, match="compensation reference is mandatory"):
        receipt.mark_compensated(" ")
    payload = receipt.as_dict()
    payload["change"] = []
    with pytest.raises(ValidationError, match="change must be an object"):
        DdiMutationReceipt.restore(payload)
    payload = receipt.as_dict()
    payload["change"] = {**bind.as_dict(), "metadata": []}
    with pytest.raises(ValidationError, match="metadata must be an object"):
        DdiMutationReceipt.restore(payload)
    payload = receipt.as_dict()
    payload["compensated"] = True
    payload["compensation_reference"] = None
    assert DdiMutationReceipt.restore(payload).compensation_reference == "restored-compensation"

    with pytest.raises(ValidationError, match="SHA-256"):
        DdiExecutionJournal.create(
            TenantId.from_value("default"), "prod", "res-key", "exec-key", "bad", (DdiProvider.BIND,)
        )
    with pytest.raises(ValidationError, match="at least one provider"):
        DdiExecutionJournal.create(
            TenantId.from_value("default"), "prod", "res-key", "exec-key", "a" * 64, ()
        )
    with pytest.raises(ValidationError, match="3 to 128 safe characters"):
        DdiExecutionJournal.create(
            TenantId.from_value("default"), "prod", "x", "exec-key", "a" * 64, (DdiProvider.BIND,)
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        DdiExecutionJournal.create(
            TenantId.from_value("default"),
            "prod",
            "res-key",
            "exec-key",
            "a" * 64,
            (DdiProvider.BIND,),
            datetime(2026, 7, 22),
        )
    payload = _journal().as_dict()
    payload["providers"] = "bind"
    with pytest.raises(ValidationError, match="must be arrays"):
        DdiExecutionJournal.restore(payload)

    pending = _journal()
    running = pending.start()
    with pytest.raises(ValidationError, match="only be recorded"):
        pending.record_receipt(receipt)
    wrong_provider = DdiMutationReceipt.create(
        1,
        DdiChange.create(
            DdiProvider.POWERDNS,
            DdiAction.UPSERT,
            DdiRecordKind.DNS_FORWARD,
            "srv.example.net",
            "10.0.0.10",
            300,
            {"record_type": "A", "zone": "example.net"},
        ),
        DdiChange.create(
            DdiProvider.POWERDNS,
            DdiAction.DELETE,
            DdiRecordKind.DNS_FORWARD,
            "srv.example.net",
            "10.0.0.10",
            300,
            {"record_type": "A", "zone": "example.net"},
        ),
        "pdns:ref",
    )
    with pytest.raises(ValidationError, match="not part"):
        running.record_receipt(wrong_provider)
    with pytest.raises(ValidationError, match="without applied receipts"):
        running.succeed()
    unknown = DdiMutationReceipt.create(
        1, bind, bind.compensating(), "bind:unknown", DdiMutationOutcome.UNKNOWN
    )
    with pytest.raises(ValidationError, match="without applied receipts"):
        running.record_receipt(unknown).succeed()
    with pytest.raises(ValidationError, match="only start"):
        pending.begin_compensation("error")
    with pytest.raises(ValidationError, match="only be compensated"):
        running.mark_receipt_compensated(1, "rollback")
    compensating = running.record_receipt(receipt).begin_compensation("error")
    with pytest.raises(ValidationError, match="not found"):
        compensating.mark_receipt_compensated(99, "rollback")
    with pytest.raises(ValidationError, match="only finish"):
        running.compensated()

    succeeded = running.record_receipt(receipt).succeed()
    for operation, message in (
        (succeeded.start, "cannot start"),
        (lambda: succeeded.fail_without_effect("late"), "cannot fail"),
        (lambda: pending.compensation_failed("late"), "invalid source state"),
    ):
        with pytest.raises(ValidationError, match=message):
            operation()

    with pytest.raises(ValidationError, match="successful DDI execution"):
        replace(succeeded, receipts=())._validate_invariants()
    compensated = compensating.mark_receipt_compensated(1, "rollback").compensated()
    with pytest.raises(ValidationError, match="cannot require reconciliation"):
        replace(compensated, reconciliation_required=True)._validate_invariants()
    compensation_failed = running.compensation_failed("unknown")
    with pytest.raises(ValidationError, match="must require reconciliation"):
        replace(compensation_failed, reconciliation_required=False)._validate_invariants()
