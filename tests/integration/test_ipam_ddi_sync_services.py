from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.ddi_sync_services import SyncDdiReservationCommand
from openinfra.application.ipam_services import AllocateIpCommand, DefineIpPrefixCommand
from openinfra.application.ports import DdiExecutor
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ValidationError
from openinfra.domain.ddi_sync import (
    DdiExecutionStatus,
    DdiMutationOutcome,
    DdiMutationReceipt,
    DdiProviderMutationError,
)
from openinfra.domain.ipam import DdiChange, DdiProvider
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class RecordingDdiExecutor(DdiExecutor):
    def __init__(
        self,
        provider: DdiProvider,
        *,
        fail_on_apply: int | None = None,
        outcome_unknown: bool = False,
        fail_compensation: bool = False,
    ) -> None:
        self._provider = provider
        self.fail_on_apply = fail_on_apply
        self.outcome_unknown = outcome_unknown
        self.fail_compensation = fail_compensation
        self.applied: list[DdiChange] = []
        self.compensated: list[int] = []

    @property
    def provider(self) -> DdiProvider:
        return self._provider

    def apply(self, sequence: int, change: DdiChange) -> DdiMutationReceipt:
        rollback = change.compensating()
        if self.fail_on_apply == len(self.applied) + 1:
            if self.outcome_unknown:
                receipt = DdiMutationReceipt.create(
                    sequence,
                    change,
                    rollback,
                    f"{self.provider.value}:unknown",
                    DdiMutationOutcome.UNKNOWN,
                )
                raise DdiProviderMutationError(
                    "provider timeout",
                    outcome_unknown=True,
                    receipt=receipt,
                )
            raise DdiProviderMutationError("provider rejected mutation")
        self.applied.append(change)
        return DdiMutationReceipt.create(
            sequence,
            change,
            rollback,
            f"{self.provider.value}:applied:{sequence}",
        )

    def compensate(self, receipt: DdiMutationReceipt) -> str:
        if self.fail_compensation:
            raise DdiProviderMutationError("rollback failed", outcome_unknown=True)
        self.compensated.append(receipt.sequence)
        return f"{self.provider.value}:rollback:{receipt.sequence}"


def _application(path: Path, *executors: DdiExecutor):
    app = ApplicationFactory().create_json_application(
        path,
        seed=False,
        ddi_executors=tuple(executors),
    )
    app.ipam_model_service.define_prefix(
        DefineIpPrefixCommand("default", "pytest", "prod", "10.88.0.0/29")
    )
    app.ipam_service.allocate(
        AllocateIpCommand(
            "default",
            "pytest",
            "prod",
            "10.88.0.0/29",
            "srv-ddi-sync",
            "reservation-sync-1",
        )
    )
    return app


def _command(**overrides: object) -> SyncDdiReservationCommand:
    values: dict[str, object] = {
        "tenant_id": "default",
        "actor": "pytest",
        "vrf": "prod",
        "reservation_idempotency_key": "reservation-sync-1",
        "execution_idempotency_key": "execution-sync-1",
        "providers": ("bind",),
        "dns_zone": "example.net",
        "reverse_dns_zone": "88.10.in-addr.arpa",
        "ttl": 300,
    }
    values.update(overrides)
    return SyncDdiReservationCommand(**values)  # type: ignore[arg-type]


def test_ddi_sync_success_is_idempotent_and_persisted(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    executor = RecordingDdiExecutor(DdiProvider.BIND)
    app = _application(state, executor)

    first = app.ipam_ddi_sync_service.synchronize(_command())
    second = app.ipam_ddi_sync_service.synchronize(_command())
    reloaded = ApplicationFactory().create_json_application(
        state, seed=False, ddi_executors=(executor,)
    ).ipam_ddi_sync_service.get_execution("default", "execution-sync-1")

    assert first.status is DdiExecutionStatus.SUCCEEDED
    assert second.id == first.id
    assert len(executor.applied) == 2
    assert reloaded is not None and reloaded.as_dict() == first.as_dict()


def test_ddi_sync_rejects_idempotency_key_reuse_for_different_request(
    tmp_path: Path,
) -> None:
    executor = RecordingDdiExecutor(DdiProvider.BIND)
    app = _application(tmp_path / "state.json", executor)
    app.ipam_ddi_sync_service.synchronize(_command())

    with pytest.raises(ValidationError, match="different request"):
        app.ipam_ddi_sync_service.synchronize(_command(ttl=600))


def test_ddi_sync_compensates_applied_changes_on_deterministic_failure(
    tmp_path: Path,
) -> None:
    bind = RecordingDdiExecutor(DdiProvider.BIND)
    powerdns = RecordingDdiExecutor(DdiProvider.POWERDNS, fail_on_apply=1)
    app = _application(tmp_path / "state.json", bind, powerdns)

    result = app.ipam_ddi_sync_service.synchronize(
        _command(providers=("bind", "powerdns"))
    )

    assert result.status is DdiExecutionStatus.COMPENSATED
    assert bind.compensated == [2, 1]
    assert result.reconciliation_required is False


def test_ddi_sync_unknown_first_mutation_requires_reconciliation(tmp_path: Path) -> None:
    bind = RecordingDdiExecutor(
        DdiProvider.BIND,
        fail_on_apply=1,
        outcome_unknown=True,
    )
    app = _application(tmp_path / "state.json", bind)

    result = app.ipam_ddi_sync_service.synchronize(_command())

    assert result.status is DdiExecutionStatus.COMPENSATION_FAILED
    assert result.reconciliation_required is True
    assert bind.compensated == [1]


def test_ddi_sync_compensation_failure_is_fail_closed(tmp_path: Path) -> None:
    bind = RecordingDdiExecutor(DdiProvider.BIND, fail_compensation=True)
    powerdns = RecordingDdiExecutor(DdiProvider.POWERDNS, fail_on_apply=1)
    app = _application(tmp_path / "state.json", bind, powerdns)

    result = app.ipam_ddi_sync_service.synchronize(
        _command(providers=("bind", "powerdns"))
    )

    assert result.status is DdiExecutionStatus.COMPENSATION_FAILED
    assert result.reconciliation_required is True


def test_ddi_sync_refuses_missing_executor_and_blocking_divergence(tmp_path: Path) -> None:
    app = _application(tmp_path / "state.json")
    with pytest.raises(ValidationError, match="executors unavailable"):
        app.ipam_ddi_sync_service.synchronize(_command())

    kea = RecordingDdiExecutor(DdiProvider.KEA)
    app = _application(tmp_path / "kea-state.json", kea)
    with pytest.raises(ValidationError, match="blocked"):
        app.ipam_ddi_sync_service.synchronize(
            _command(providers=("kea",), execution_idempotency_key="execution-kea-1")
        )


def test_ddi_sync_cli_and_http_require_authorization(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bind = RecordingDdiExecutor(DdiProvider.BIND)
    app = _application(tmp_path / "state.json", bind)
    token = "d" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            "default", "pytest", "ddi-operator", ("ipam:operator",), token
        )
    )

    cli = OpenInfraCLI()
    cli._create_application = lambda args: app  # type: ignore[method-assign]
    status = cli.run(
        [
            "ipam",
            "ddi-sync",
            "--data",
            str(tmp_path / "unused.json"),
            "--tenant",
            "default",
            "--auth-token",
            token,
            "--vrf",
            "prod",
            "--reservation-idempotency-key",
            "reservation-sync-1",
            "--execution-idempotency-key",
            "execution-cli-1",
            "--provider",
            "bind",
            "--dns-zone",
            "example.net",
            "--reverse-dns-zone",
            "88.10.in-addr.arpa",
        ]
    )
    assert status == 0
    assert '"status": "succeeded"' in capsys.readouterr().out

    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/ipam/ddi-sync"
        payload = {
            "tenant_id": "default",
            "vrf": "prod",
            "reservation_idempotency_key": "reservation-sync-1",
            "execution_idempotency_key": "execution-api-1",
            "providers": ["bind"],
            "dns_zone": "example.net",
            "reverse_dns_zone": "88.10.in-addr.arpa",
        }
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_json(url, payload)
        assert exc_info.value.code == 401
        result = _post_json(url, payload, token)
        assert result["status"] == "succeeded"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post_json(url: str, payload: dict[str, object], token: str | None = None) -> dict[str, object]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_ddi_sync_resume_failure_and_corrupt_journal_edges(tmp_path: Path) -> None:
    from dataclasses import replace

    from openinfra.application.ipam_services import PreviewDdiReservationCommand
    from openinfra.domain.ddi_sync import DdiExecutionJournal

    bind = RecordingDdiExecutor(DdiProvider.BIND)
    app = _application(tmp_path / "resume.json", bind)
    service = app.ipam_ddi_sync_service
    command = _command(execution_idempotency_key="execution-resume-1")
    preview = app.ipam_ddi_service.preview_reservation(
        PreviewDdiReservationCommand(
            command.tenant_id,
            command.actor,
            command.vrf,
            command.reservation_idempotency_key,
            command.providers,
            command.dns_zone,
            command.mac_address,
            command.ttl,
            False,
            command.reverse_dns_zone,
        )
    )
    fingerprint = service._fingerprint(command, preview.as_dict())
    running = service._initialize(command, preview.providers, fingerprint)
    running = service._persist(running.record_receipt(bind.apply(1, preview.changes[0])))
    assert service.synchronize(command).status is DdiExecutionStatus.RUNNING

    compensating = service._persist(running.begin_compensation("paused"))
    assert service.synchronize(command).status is DdiExecutionStatus.COMPENSATING
    resumed = service.synchronize(replace(command, resume=True))
    assert resumed.status is DdiExecutionStatus.COMPENSATED

    overrun_app = _application(tmp_path / "overrun.json", bind)
    overrun_service = overrun_app.ipam_ddi_sync_service
    overrun_command = _command(execution_idempotency_key="execution-overrun-1", resume=True)
    overrun_preview = overrun_app.ipam_ddi_service.preview_reservation(
        PreviewDdiReservationCommand(
            overrun_command.tenant_id,
            overrun_command.actor,
            overrun_command.vrf,
            overrun_command.reservation_idempotency_key,
            overrun_command.providers,
            overrun_command.dns_zone,
            overrun_command.mac_address,
            overrun_command.ttl,
            False,
            overrun_command.reverse_dns_zone,
        )
    )
    overrun = overrun_service._initialize(
        overrun_command,
        overrun_preview.providers,
        overrun_service._fingerprint(overrun_command, overrun_preview.as_dict()),
    )
    for sequence, change in enumerate((*overrun_preview.changes, overrun_preview.changes[0]), 1):
        overrun = overrun.record_receipt(
            DdiMutationReceipt.create(
                sequence,
                change,
                change.compensating(),
                f"bind:synthetic:{sequence}",
            )
        )
    overrun_service._persist(overrun)
    assert overrun_service.synchronize(overrun_command).status is DdiExecutionStatus.COMPENSATION_FAILED

    class UnexpectedFailureExecutor(RecordingDdiExecutor):
        def apply(self, sequence: int, change: DdiChange) -> DdiMutationReceipt:
            raise RuntimeError("unexpected adapter failure")

    unexpected_app = _application(
        tmp_path / "unexpected.json", UnexpectedFailureExecutor(DdiProvider.BIND)
    )
    failed = unexpected_app.ipam_ddi_sync_service.synchronize(
        _command(execution_idempotency_key="execution-unexpected-1")
    )
    assert failed.status is DdiExecutionStatus.FAILED
    assert failed.reconciliation_required is False

    missing_app = _application(tmp_path / "missing-compensator.json", bind)
    missing_service = missing_app.ipam_ddi_sync_service
    missing_command = _command(execution_idempotency_key="execution-missing-compensator-1")
    missing_preview = missing_app.ipam_ddi_service.preview_reservation(
        PreviewDdiReservationCommand(
            missing_command.tenant_id,
            missing_command.actor,
            missing_command.vrf,
            missing_command.reservation_idempotency_key,
            missing_command.providers,
            missing_command.dns_zone,
            missing_command.mac_address,
            missing_command.ttl,
            False,
            missing_command.reverse_dns_zone,
        )
    )
    missing = missing_service._initialize(
        missing_command,
        missing_preview.providers,
        missing_service._fingerprint(missing_command, missing_preview.as_dict()),
    )
    missing = missing_service._persist(
        missing.record_receipt(bind.apply(1, missing_preview.changes[0])).begin_compensation(
            "provider removed"
        )
    )
    missing_service._executors.clear()
    unavailable = missing_service._compensate(missing, "pytest")
    assert unavailable.status is DdiExecutionStatus.COMPENSATION_FAILED
    assert "executor unavailable" in (unavailable.error_message or "")

    orphan = DdiExecutionJournal.create(
        missing.tenant_id,
        "prod",
        "reservation-orphan",
        "execution-orphan",
        "b" * 64,
        (DdiProvider.BIND,),
    ).start()
    with pytest.raises(ValidationError, match="disappeared"):
        missing_service._persist(orphan)
