from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.domain.ddi_sync import DdiProviderMutationError
from openinfra.domain.ipam import DdiAction, DdiChange, DdiProvider, DdiRecordKind
from openinfra.infrastructure.ddi_executors import (
    BindExecutorSettings,
    BindNsupdateDdiExecutor,
    DdiExecutorFactory,
    JsonHttpTransport,
    KeaDdiExecutor,
    PowerDnsDdiExecutor,
    SubprocessRunner,
)


class FakeRunner:
    def __init__(self, responses: list[tuple[int, str, str]]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[tuple[str, ...], str | None, float]] = []

    def run(
        self, argv: Sequence[str], *, input_text: str | None, timeout_seconds: float
    ) -> tuple[int, str, str]:
        self.calls.append((tuple(argv), input_text, timeout_seconds))
        return self.responses.pop(0)


class FakeTransport:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, str], object | None]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: object | None = None,
    ) -> object:
        self.calls.append((method, url, dict(headers), payload))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _bind_change(action: DdiAction = DdiAction.UPSERT) -> DdiChange:
    return DdiChange.create(
        DdiProvider.BIND,
        action,
        DdiRecordKind.DNS_FORWARD,
        "srv01.example.net",
        "192.0.2.10",
        300,
        {"record_type": "A", "zone": "example.net"},
    )


def _powerdns_change() -> DdiChange:
    return DdiChange.create(
        DdiProvider.POWERDNS,
        DdiAction.UPSERT,
        DdiRecordKind.DNS_FORWARD,
        "srv01.example.net",
        "192.0.2.10",
        300,
        {"record_type": "A", "zone": "example.net"},
    )


def _kea_change() -> DdiChange:
    return DdiChange.create(
        DdiProvider.KEA,
        DdiAction.UPSERT,
        DdiRecordKind.DHCP_RESERVATION,
        "srv01",
        "192.0.2.10",
        0,
        {"subnet_id": "42", "hw_address": "02:00:00:00:00:10", "hostname": "srv01"},
    )


def test_subprocess_runner_rejects_relative_executable() -> None:
    with pytest.raises(ValidationError, match="absolute path"):
        SubprocessRunner().run(("nsupdate",), input_text=None, timeout_seconds=1)


def test_http_transport_rejects_insecure_or_credentialed_urls() -> None:
    transport = JsonHttpTransport()
    for url in ("http://pdns.example", "https://user:secret@pdns.example"):
        with pytest.raises(ValidationError):
            transport.request("GET", url, headers={})


def test_bind_apply_and_compensation_restore_exact_previous_values() -> None:
    runner = FakeRunner([(0, "192.0.2.7\n192.0.2.8\n", ""), (0, "", ""), (0, "", "")])
    executor = BindNsupdateDdiExecutor(
        BindExecutorSettings(Path("/usr/bin/nsupdate"), Path("/usr/bin/dig"), "192.0.2.53"),
        runner,
    )
    receipt = executor.apply(1, _bind_change())
    assert "update add 300 srv01.example.net A 192.0.2.10" in (runner.calls[1][1] or "")
    reference = executor.compensate(receipt)
    rollback_script = runner.calls[2][1] or ""
    assert "update add 300 srv01.example.net A 192.0.2.7" in rollback_script
    assert "update add 300 srv01.example.net A 192.0.2.8" in rollback_script
    assert reference.startswith("bind-rollback:")


def test_bind_mutation_failure_produces_unknown_receipt() -> None:
    runner = FakeRunner([(0, "", ""), (1, "", "timeout")])
    executor = BindNsupdateDdiExecutor(
        BindExecutorSettings(Path("/usr/bin/nsupdate"), Path("/usr/bin/dig"), "192.0.2.53"),
        runner,
    )
    with pytest.raises(DdiProviderMutationError) as raised:
        executor.apply(2, _bind_change())
    assert raised.value.outcome_unknown is True
    assert raised.value.receipt is not None
    assert raised.value.receipt.sequence == 2


def test_powerdns_apply_and_compensate_restore_full_rrset() -> None:
    previous = {
        "name": "srv01.example.net.",
        "type": "A",
        "ttl": 600,
        "records": [{"content": "192.0.2.7", "disabled": False}],
    }
    transport = FakeTransport([{"rrsets": [previous]}, {}, {}])
    executor = PowerDnsDdiExecutor(
        "https://pdns.example", "api-key", transport=transport  # type: ignore[arg-type]
    )
    receipt = executor.apply(1, _powerdns_change())
    assert transport.calls[0][0] == "GET"
    assert transport.calls[1][0] == "PATCH"
    executor.compensate(receipt)
    payload = transport.calls[2][3]
    assert isinstance(payload, dict)
    assert payload["rrsets"] == [{**previous, "changetype": "REPLACE"}]
    assert "X-API-Key" in transport.calls[2][2]


def test_powerdns_mutation_failure_is_unknown() -> None:
    transport = FakeTransport(
        [{"rrsets": []}, DdiProviderMutationError("connection lost", outcome_unknown=True)]
    )
    executor = PowerDnsDdiExecutor(
        "https://pdns.example", "api-key", transport=transport  # type: ignore[arg-type]
    )
    with pytest.raises(DdiProviderMutationError) as raised:
        executor.apply(1, _powerdns_change())
    assert raised.value.outcome_unknown is True
    assert raised.value.receipt is not None


def test_kea_apply_and_compensation_restore_previous_reservation() -> None:
    previous = {
        "reservation": {
            "subnet-id": 42,
            "hw-address": "02:00:00:00:00:07",
            "ip-address": "192.0.2.7",
            "hostname": "old-host",
        }
    }
    transport = FakeTransport(
        [[{"result": 0, "arguments": previous}], [{"result": 0}], [{"result": 0}]]
    )
    executor = KeaDdiExecutor(
        "https://kea.example", "token", transport=transport  # type: ignore[arg-type]
    )
    receipt = executor.apply(1, _kea_change())
    executor.compensate(receipt)
    rollback_payload = transport.calls[2][3]
    assert isinstance(rollback_payload, dict)
    assert rollback_payload["command"] == "reservation-add"
    assert rollback_payload["arguments"] == previous


def test_kea_rejects_non_reservation_change_and_unknown_mutation() -> None:
    executor = KeaDdiExecutor(
        "https://kea.example", "token", transport=FakeTransport([])  # type: ignore[arg-type]
    )
    invalid_kea_change = DdiChange.create(
        DdiProvider.KEA,
        DdiAction.UPSERT,
        DdiRecordKind.DNS_FORWARD,
        "srv01.example.net",
        "192.0.2.10",
        300,
        {"record_type": "A", "zone": "example.net"},
    )
    with pytest.raises(ValidationError, match="DHCP"):
        executor.apply(1, invalid_kea_change)

    transport = FakeTransport(
        [[{"result": 3}], DdiProviderMutationError("timeout", outcome_unknown=True)]
    )
    executor = KeaDdiExecutor(
        "https://kea.example", "token", transport=transport  # type: ignore[arg-type]
    )
    with pytest.raises(DdiProviderMutationError) as raised:
        executor.apply(1, _kea_change())
    assert raised.value.outcome_unknown is True
    assert raised.value.receipt is not None


def test_factory_loads_only_complete_provider_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENINFRA_DDI_POWERDNS_URL", "https://pdns.example")
    monkeypatch.setenv("OPENINFRA_DDI_POWERDNS_API_KEY", "key")
    monkeypatch.setenv("OPENINFRA_DDI_KEA_URL", "https://kea.example")
    monkeypatch.setenv("OPENINFRA_DDI_KEA_TOKEN", "token")
    providers = {executor.provider for executor in DdiExecutorFactory.from_environment()}
    assert providers == {DdiProvider.POWERDNS, DdiProvider.KEA}


def test_ddi_executor_validation_transport_and_provider_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess
    import urllib.error
    import urllib.request
    from io import BytesIO
    from types import SimpleNamespace

    from openinfra.infrastructure.ddi_executors import (
        DdiExecutorSupport,
        _NoRedirectHandler,
    )

    with pytest.raises(ValidationError, match="cannot be empty"):
        SubprocessRunner().run((), input_text=None, timeout_seconds=1)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )
    assert SubprocessRunner().run(("/bin/echo",), input_text="x", timeout_seconds=1) == (
        0,
        "ok",
        "",
    )
    with pytest.raises(urllib.error.HTTPError, match="redirects are disabled"):
        _NoRedirectHandler().redirect_request(
            urllib.request.Request("https://provider.example"),
            BytesIO(),
            302,
            "Found",
            {},
            "https://other.example",
        )

    for timeout in (0.0, 121.0):
        with pytest.raises(ValidationError, match="HTTP timeout"):
            JsonHttpTransport(timeout)
    with pytest.raises(ValidationError, match="fragment"):
        DdiExecutorSupport.validate_https_url("https://provider.example/api#fragment")
    with pytest.raises(ValidationError, match="rollback metadata"):
        DdiExecutorSupport.parse_json_metadata("not-json", "rollback")

    class FakeResponse:
        def __init__(self, body: bytes, url: str = "https://provider.example/api") -> None:
            self._body = body
            self._url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def geturl(self) -> str:
            return self._url

        def read(self) -> bytes:
            return self._body

    class FakeOpener:
        def __init__(self, responses: list[object]) -> None:
            self.responses = responses

        def open(self, _request: object, *, timeout: float) -> FakeResponse:
            assert timeout == 1
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            assert isinstance(response, FakeResponse)
            return response

    transport = JsonHttpTransport(1)
    transport._opener = FakeOpener(  # type: ignore[assignment]
        [FakeResponse(b""), FakeResponse(b'{"ok":true}'), FakeResponse(b"\xff")]
    )
    assert transport.request("GET", "https://provider.example/api", headers={}) == {}
    assert transport.request("POST", "https://provider.example/api", headers={}, payload={}) == {
        "ok": True
    }
    with pytest.raises(DdiProviderMutationError, match="invalid JSON") as invalid_json:
        transport.request("POST", "https://provider.example/api", headers={}, payload={})
    assert invalid_json.value.outcome_unknown is True

    for method, expected_unknown in (("GET", False), ("PATCH", True)):
        failed = JsonHttpTransport(1)
        failed._opener = FakeOpener(  # type: ignore[assignment]
            [urllib.error.URLError("offline")]
        )
        with pytest.raises(DdiProviderMutationError) as raised:
            failed.request(method, "https://provider.example/api", headers={})
        assert raised.value.outcome_unknown is expected_unknown

    for settings, message in (
        (BindExecutorSettings(Path("nsupdate"), Path("/usr/bin/dig"), "dns"), "absolute"),
        (
            BindExecutorSettings(
                Path("/usr/bin/nsupdate"), Path("/usr/bin/dig"), "dns", Path("relative.key")
            ),
            "key file",
        ),
        (BindExecutorSettings(Path("/usr/bin/nsupdate"), Path("/usr/bin/dig"), "bad dns"), "server"),
        (
            BindExecutorSettings(
                Path("/usr/bin/nsupdate"), Path("/usr/bin/dig"), "dns", timeout_seconds=0
            ),
            "timeout",
        ),
    ):
        with pytest.raises(ValidationError, match=message):
            settings.validate()

    pre_read_failure = BindNsupdateDdiExecutor(
        BindExecutorSettings(Path("/usr/bin/nsupdate"), Path("/usr/bin/dig"), "dns"),
        FakeRunner([(1, "", "refused")]),
    )
    with pytest.raises(DdiProviderMutationError, match="pre-read"):
        pre_read_failure.apply(1, _bind_change())
    bind = BindNsupdateDdiExecutor(
        BindExecutorSettings(Path("/usr/bin/nsupdate"), Path("/usr/bin/dig"), "dns"),
        FakeRunner([]),
    )
    no_metadata = DdiChange.create(
        DdiProvider.BIND,
        DdiAction.UPSERT,
        DdiRecordKind.DNS_FORWARD,
        "srv.example",
        "192.0.2.1",
        300,
        {},
    )
    with pytest.raises(ValidationError, match="record_type and zone"):
        bind._render_update(no_metadata)
    with pytest.raises(ValidationError, match="non-BIND"):
        bind.apply(1, _powerdns_change())
    keyed_runner = FakeRunner([(0, "", ""), (0, "", "")])
    keyed = BindNsupdateDdiExecutor(
        BindExecutorSettings(
            Path("/usr/bin/nsupdate"),
            Path("/usr/bin/dig"),
            "dns",
            Path("/etc/bind/key"),
        ),
        keyed_runner,
    )
    keyed.apply(1, _bind_change(DdiAction.DELETE))
    assert keyed_runner.calls[1][0][1:] == ("-k", "/etc/bind/key")

    for key, server, message in (("", "localhost", "API key"), ("key", "bad/id", "server id")):
        with pytest.raises(ValidationError, match=message):
            PowerDnsDdiExecutor("https://pdns.example", key, server)
    for response, message in (([], "zone response"), ({"rrsets": {}}, "rrsets response")):
        pdns = PowerDnsDdiExecutor(
            "https://pdns.example",
            "key",
            transport=FakeTransport([response]),  # type: ignore[arg-type]
        )
        with pytest.raises(DdiProviderMutationError, match=message):
            pdns.apply(1, _powerdns_change())
    pdns = PowerDnsDdiExecutor(
        "https://pdns.example", "key", transport=FakeTransport([])  # type: ignore[arg-type]
    )
    with pytest.raises(ValidationError, match="zone and record_type"):
        pdns._mutate(
            DdiChange.create(
                DdiProvider.POWERDNS,
                DdiAction.UPSERT,
                DdiRecordKind.DNS_FORWARD,
                "srv.example",
                "192.0.2.1",
                300,
                {},
            )
        )
    for previous in ('{}', '[1]'):
        rollback = DdiChange.create(
            DdiProvider.POWERDNS,
            DdiAction.UPSERT,
            DdiRecordKind.DNS_FORWARD,
            "srv.example",
            "192.0.2.1",
            300,
            {"zone": "example", "record_type": "A", "previous_rrsets": previous},
        )
        with pytest.raises(ValidationError, match="previous_rrsets"):
            pdns._mutate(rollback)
    with pytest.raises(ValidationError, match="non-PowerDNS"):
        pdns.apply(1, _bind_change())
    assert pdns._absolute_name("example.") == "example."

    with pytest.raises(ValidationError, match="bearer token"):
        KeaDdiExecutor("https://kea.example", " ")
    kea = KeaDdiExecutor(
        "https://kea.example", "token", transport=FakeTransport([])  # type: ignore[arg-type]
    )
    with pytest.raises(ValidationError, match="non-Kea"):
        kea.apply(1, _bind_change())
    invalid_lookup = DdiChange.create(
        DdiProvider.KEA,
        DdiAction.UPSERT,
        DdiRecordKind.DHCP_RESERVATION,
        "srv",
        "192.0.2.1",
        0,
        {},
    )
    with pytest.raises(ValidationError, match="subnet_id"):
        kea._lookup_arguments(invalid_lookup)
    assert kea._extract_kea_arguments([]) == {}
    assert kea._extract_kea_arguments({"reservation": "invalid"}) == {}
    for response, message in (([], "response must be an object"), ([{"result": 2, "text": "bad"}], "bad")):
        failing_kea = KeaDdiExecutor(
            "https://kea.example", "token", transport=FakeTransport([response])  # type: ignore[arg-type]
        )
        with pytest.raises(DdiProviderMutationError, match=message):
            failing_kea._command("reservation-add", {}, mutation=True)
    deterministic = KeaDdiExecutor(
        "https://kea.example",
        "token",
        transport=FakeTransport([DdiProviderMutationError("rejected")]),  # type: ignore[arg-type]
    )
    with pytest.raises(DdiProviderMutationError) as converted:
        deterministic._command("reservation-add", {}, mutation=True)
    assert converted.value.outcome_unknown is True

    monkeypatch.setenv("OPENINFRA_DDI_POWERDNS_TIMEOUT_SECONDS", "invalid")
    with pytest.raises(ValidationError, match="must be numeric"):
        DdiExecutorFactory._timeout("OPENINFRA_DDI_POWERDNS_TIMEOUT_SECONDS")
    monkeypatch.setenv("OPENINFRA_DDI_POWERDNS_TIMEOUT_SECONDS", "121")
    with pytest.raises(ValidationError, match="between"):
        DdiExecutorFactory._timeout("OPENINFRA_DDI_POWERDNS_TIMEOUT_SECONDS")
