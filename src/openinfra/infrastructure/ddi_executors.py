from __future__ import annotations

import hashlib
import json
import os
import ssl
import subprocess  # nosec B404 - fixed absolute executables, shell=False, bounded timeout
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from openinfra.application.ports import DdiExecutor
from openinfra.domain.common import ValidationError
from openinfra.domain.ddi_sync import (
    DdiMutationOutcome,
    DdiMutationReceipt,
    DdiProviderMutationError,
)
from openinfra.domain.ipam import DdiAction, DdiChange, DdiProvider, DdiRecordKind


class ProcessRunner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None,
        timeout_seconds: float,
    ) -> tuple[int, str, str]: ...


class SubprocessRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None,
        timeout_seconds: float,
    ) -> tuple[int, str, str]:
        if not argv:
            raise ValidationError("DDI process argv cannot be empty")
        executable = Path(argv[0])
        if not executable.is_absolute():
            raise ValidationError("DDI process executable must be an absolute path")
        completed = subprocess.run(  # nosec B603 - argv only, shell=False by default
            list(argv),
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return completed.returncode, completed.stdout, completed.stderr


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> urllib.request.Request | None:
        raise urllib.error.HTTPError(req.full_url, code, "redirects are disabled", headers, fp)


class JsonHttpTransport:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        if not 0.1 <= timeout_seconds <= 120:
            raise ValidationError("DDI HTTP timeout must be between 0.1 and 120 seconds")
        self._timeout_seconds = timeout_seconds
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            _NoRedirectHandler(),
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: object | None = None,
    ) -> object:
        DdiExecutorSupport.validate_https_url(url)
        body = None
        normalized_headers = {str(key): str(value) for key, value in headers.items()}
        normalized_headers.setdefault("Accept", "application/json")
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            normalized_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(
            url,
            data=body,
            headers=normalized_headers,
            method=method.upper(),
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                final_url = response.geturl()
                DdiExecutorSupport.validate_https_url(final_url)
                raw = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DdiProviderMutationError(str(exc), outcome_unknown=method.upper() != "GET") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DdiProviderMutationError(
                "DDI provider returned invalid JSON",
                outcome_unknown=method.upper() != "GET",
            ) from exc


class DdiExecutorSupport:
    @staticmethod
    def validate_https_url(url: str) -> str:
        normalized = url.strip().rstrip("/")
        parsed = urllib.parse.urlsplit(normalized)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise ValidationError("DDI provider URL must use HTTPS")
        if parsed.username or parsed.password:
            raise ValidationError("DDI provider URL cannot contain embedded credentials")
        if parsed.fragment:
            raise ValidationError("DDI provider URL cannot contain a fragment")
        return normalized

    @staticmethod
    def metadata(change: DdiChange) -> dict[str, str]:
        return dict(change.metadata)

    @staticmethod
    def json_metadata(value: object) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def parse_json_metadata(value: str, field_name: str) -> object:
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"DDI rollback metadata {field_name} is invalid") from exc


@dataclass(frozen=True, slots=True)
class BindExecutorSettings:
    nsupdate_path: Path
    dig_path: Path
    server: str
    key_file: Path | None = None
    timeout_seconds: float = 15.0

    def validate(self) -> BindExecutorSettings:
        if not self.nsupdate_path.is_absolute() or not self.dig_path.is_absolute():
            raise ValidationError("BIND DDI executables must use absolute paths")
        if self.key_file is not None and not self.key_file.is_absolute():
            raise ValidationError("BIND DDI key file must use an absolute path")
        if not self.server.strip() or any(char.isspace() for char in self.server):
            raise ValidationError("BIND DDI server is invalid")
        if not 0.1 <= self.timeout_seconds <= 120:
            raise ValidationError("BIND DDI timeout must be between 0.1 and 120 seconds")
        return self


class BindNsupdateDdiExecutor(DdiExecutor):
    def __init__(
        self,
        settings: BindExecutorSettings,
        runner: ProcessRunner | None = None,
    ) -> None:
        self._settings = settings.validate()
        self._runner = runner or SubprocessRunner()

    @property
    def provider(self) -> DdiProvider:
        return DdiProvider.BIND

    def apply(self, sequence: int, change: DdiChange) -> DdiMutationReceipt:
        self._require_provider(change)
        previous = self._read_existing(change)
        rollback = self._rollback_change(change, previous)
        script = self._render_update(change)
        reference = "bind:" + hashlib.sha256(script.encode("utf-8")).hexdigest()[:24]
        try:
            self._execute_update(script)
        except DdiProviderMutationError as exc:
            if exc.outcome_unknown:
                receipt = DdiMutationReceipt.create(
                    sequence,
                    change,
                    rollback,
                    reference,
                    DdiMutationOutcome.UNKNOWN,
                )
                raise DdiProviderMutationError(
                    str(exc), outcome_unknown=True, receipt=receipt
                ) from exc
            raise
        return DdiMutationReceipt.create(sequence, change, rollback, reference)

    def compensate(self, receipt: DdiMutationReceipt) -> str:
        self._require_provider(receipt.rollback_change)
        script = self._render_update(receipt.rollback_change)
        self._execute_update(script)
        digest = hashlib.sha256(script.encode("utf-8")).hexdigest()[:24]
        return f"bind-rollback:{digest}"

    def _read_existing(self, change: DdiChange) -> tuple[str, ...]:
        record_type = DdiExecutorSupport.metadata(change).get("record_type", "A")
        argv = (
            str(self._settings.dig_path),
            f"@{self._settings.server}",
            "+short",
            change.name,
            record_type,
        )
        code, stdout, stderr = self._runner.run(
            argv,
            input_text=None,
            timeout_seconds=self._settings.timeout_seconds,
        )
        if code != 0:
            raise DdiProviderMutationError(
                f"BIND pre-read failed: {stderr.strip() or 'unknown error'}"
            )
        return tuple(line.strip() for line in stdout.splitlines() if line.strip())

    def _rollback_change(self, change: DdiChange, previous: tuple[str, ...]) -> DdiChange:
        metadata = DdiExecutorSupport.metadata(change)
        metadata["restore_values"] = DdiExecutorSupport.json_metadata(list(previous))
        return DdiChange.create(
            provider=change.provider,
            action=DdiAction.UPSERT if previous else DdiAction.DELETE,
            record_kind=change.record_kind,
            name=change.name,
            value=previous[0] if previous else change.value,
            ttl=change.ttl,
            metadata=metadata,
        )

    def _render_update(self, change: DdiChange) -> str:
        metadata = DdiExecutorSupport.metadata(change)
        record_type = metadata.get("record_type")
        zone = metadata.get("zone")
        if not record_type or not zone:
            raise ValidationError("BIND DDI change requires record_type and zone metadata")
        values_raw = metadata.get("restore_values")
        values = (
            tuple(str(item) for item in DdiExecutorSupport.parse_json_metadata(values_raw, "restore_values"))
            if values_raw
            else (change.value,)
        )
        lines = [f"server {self._settings.server}", f"zone {zone}"]
        lines.append(f"update delete {change.name} {record_type}")
        if change.action is DdiAction.UPSERT:
            for value in values:
                lines.append(f"update add {change.ttl} {change.name} {record_type} {value}")
        lines.extend(("send", ""))
        return "\n".join(lines)

    def _execute_update(self, script: str) -> None:
        argv = [str(self._settings.nsupdate_path)]
        if self._settings.key_file is not None:
            argv.extend(("-k", str(self._settings.key_file)))
        code, _stdout, stderr = self._runner.run(
            argv,
            input_text=script,
            timeout_seconds=self._settings.timeout_seconds,
        )
        if code != 0:
            raise DdiProviderMutationError(
                f"BIND mutation failed: {stderr.strip() or 'unknown error'}",
                outcome_unknown=True,
            )

    def _require_provider(self, change: DdiChange) -> None:
        if change.provider is not self.provider:
            raise ValidationError("BIND executor received a non-BIND change")


class PowerDnsDdiExecutor(DdiExecutor):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        server_id: str = "localhost",
        transport: JsonHttpTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._base_url = DdiExecutorSupport.validate_https_url(base_url)
        self._api_key = api_key.strip()
        self._server_id = server_id.strip()
        if not self._api_key:
            raise ValidationError("PowerDNS API key is mandatory")
        if not self._server_id or "/" in self._server_id:
            raise ValidationError("PowerDNS server id is invalid")
        self._transport = transport or JsonHttpTransport(timeout_seconds)

    @property
    def provider(self) -> DdiProvider:
        return DdiProvider.POWERDNS

    def apply(self, sequence: int, change: DdiChange) -> DdiMutationReceipt:
        self._require_provider(change)
        previous = self._read_rrset(change)
        rollback = self._rollback_change(change, previous)
        reference = "powerdns:" + hashlib.sha256(
            DdiExecutorSupport.json_metadata(change.as_dict()).encode("utf-8")
        ).hexdigest()[:24]
        try:
            self._mutate(change)
        except DdiProviderMutationError as exc:
            receipt = DdiMutationReceipt.create(
                sequence,
                change,
                rollback,
                reference,
                DdiMutationOutcome.UNKNOWN,
            )
            raise DdiProviderMutationError(
                str(exc), outcome_unknown=True, receipt=receipt
            ) from exc
        return DdiMutationReceipt.create(sequence, change, rollback, reference)

    def compensate(self, receipt: DdiMutationReceipt) -> str:
        self._require_provider(receipt.rollback_change)
        self._mutate(receipt.rollback_change)
        digest = hashlib.sha256(
            DdiExecutorSupport.json_metadata(receipt.rollback_change.as_dict()).encode("utf-8")
        ).hexdigest()[:24]
        return f"powerdns-rollback:{digest}"

    def _read_rrset(self, change: DdiChange) -> list[dict[str, object]]:
        metadata = DdiExecutorSupport.metadata(change)
        zone = metadata.get("zone")
        record_type = metadata.get("record_type")
        if not zone or not record_type:
            raise ValidationError("PowerDNS change requires zone and record_type metadata")
        payload = self._transport.request("GET", self._zone_url(zone), headers=self._headers())
        if not isinstance(payload, dict):
            raise DdiProviderMutationError("PowerDNS zone response must be an object")
        rrsets = payload.get("rrsets", [])
        if not isinstance(rrsets, list):
            raise DdiProviderMutationError("PowerDNS rrsets response must be an array")
        expected_name = self._absolute_name(change.name)
        return [
            dict(item)
            for item in rrsets
            if isinstance(item, dict)
            and str(item.get("name", "")) == expected_name
            and str(item.get("type", "")) == record_type
        ]

    def _rollback_change(
        self, change: DdiChange, previous: list[dict[str, object]]
    ) -> DdiChange:
        metadata = DdiExecutorSupport.metadata(change)
        metadata["previous_rrsets"] = DdiExecutorSupport.json_metadata(previous)
        return DdiChange.create(
            provider=change.provider,
            action=DdiAction.UPSERT if previous else DdiAction.DELETE,
            record_kind=change.record_kind,
            name=change.name,
            value=change.value,
            ttl=change.ttl,
            metadata=metadata,
        )

    def _mutate(self, change: DdiChange) -> None:
        metadata = DdiExecutorSupport.metadata(change)
        zone = metadata.get("zone")
        record_type = metadata.get("record_type")
        if not zone or not record_type:
            raise ValidationError("PowerDNS change requires zone and record_type metadata")
        previous_raw = metadata.get("previous_rrsets")
        if previous_raw and change.action is DdiAction.UPSERT:
            rrsets_value = DdiExecutorSupport.parse_json_metadata(previous_raw, "previous_rrsets")
            if not isinstance(rrsets_value, list):
                raise ValidationError("PowerDNS previous_rrsets must be an array")
            rrsets = [
                {**dict(item), "changetype": "REPLACE"}
                for item in rrsets_value
                if isinstance(item, dict)
            ]
            if len(rrsets) != len(rrsets_value):
                raise ValidationError("PowerDNS previous_rrsets contains invalid entries")
        else:
            records = []
            change_type = "DELETE"
            if change.action is DdiAction.UPSERT:
                records = [{"content": change.value, "disabled": False}]
                change_type = "REPLACE"
            rrsets = [
                {
                    "name": self._absolute_name(change.name),
                    "type": record_type,
                    "ttl": change.ttl,
                    "changetype": change_type,
                    "records": records,
                }
            ]
        self._transport.request(
            "PATCH",
            self._zone_url(zone),
            headers=self._headers(),
            payload={"rrsets": rrsets},
        )

    def _zone_url(self, zone: str) -> str:
        encoded_server = urllib.parse.quote(self._server_id, safe="")
        encoded_zone = urllib.parse.quote(self._absolute_name(zone), safe="")
        return f"{self._base_url}/api/v1/servers/{encoded_server}/zones/{encoded_zone}"

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    @staticmethod
    def _absolute_name(value: str) -> str:
        return value if value.endswith(".") else f"{value}."

    def _require_provider(self, change: DdiChange) -> None:
        if change.provider is not self.provider:
            raise ValidationError("PowerDNS executor received a non-PowerDNS change")


class KeaDdiExecutor(DdiExecutor):
    def __init__(
        self,
        control_agent_url: str,
        bearer_token: str,
        transport: JsonHttpTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._url = DdiExecutorSupport.validate_https_url(control_agent_url)
        self._token = bearer_token.strip()
        if not self._token:
            raise ValidationError("Kea bearer token is mandatory")
        self._transport = transport or JsonHttpTransport(timeout_seconds)

    @property
    def provider(self) -> DdiProvider:
        return DdiProvider.KEA

    def apply(self, sequence: int, change: DdiChange) -> DdiMutationReceipt:
        self._require_provider(change)
        previous = self._command("reservation-get", self._lookup_arguments(change), mutation=False)
        rollback = self._rollback_change(change, previous)
        reference = "kea:" + hashlib.sha256(
            DdiExecutorSupport.json_metadata(change.as_dict()).encode("utf-8")
        ).hexdigest()[:24]
        try:
            self._execute_change(change)
        except DdiProviderMutationError as exc:
            receipt = DdiMutationReceipt.create(
                sequence,
                change,
                rollback,
                reference,
                DdiMutationOutcome.UNKNOWN,
            )
            raise DdiProviderMutationError(
                str(exc), outcome_unknown=True, receipt=receipt
            ) from exc
        return DdiMutationReceipt.create(sequence, change, rollback, reference)

    def compensate(self, receipt: DdiMutationReceipt) -> str:
        self._require_provider(receipt.rollback_change)
        self._execute_change(receipt.rollback_change)
        digest = hashlib.sha256(
            DdiExecutorSupport.json_metadata(receipt.rollback_change.as_dict()).encode("utf-8")
        ).hexdigest()[:24]
        return f"kea-rollback:{digest}"

    def _rollback_change(self, change: DdiChange, previous: object) -> DdiChange:
        metadata = DdiExecutorSupport.metadata(change)
        arguments = self._extract_kea_arguments(previous)
        metadata["previous_reservation"] = DdiExecutorSupport.json_metadata(arguments)
        return DdiChange.create(
            provider=change.provider,
            action=DdiAction.UPSERT if arguments else DdiAction.DELETE,
            record_kind=change.record_kind,
            name=change.name,
            value=change.value,
            ttl=0,
            metadata=metadata,
        )

    def _execute_change(self, change: DdiChange) -> None:
        metadata = DdiExecutorSupport.metadata(change)
        previous_raw = metadata.get("previous_reservation")
        if previous_raw and change.action is DdiAction.UPSERT:
            previous = DdiExecutorSupport.parse_json_metadata(previous_raw, "previous_reservation")
            if not isinstance(previous, dict):
                raise ValidationError("Kea previous_reservation must be an object")
            command = "reservation-add"
            arguments = previous
        elif change.action is DdiAction.DELETE:
            command = "reservation-del"
            arguments = self._lookup_arguments(change)
        else:
            command = "reservation-add"
            arguments = self._reservation_arguments(change)
        self._command(command, arguments, mutation=True)

    def _command(self, command: str, arguments: dict[str, object], *, mutation: bool) -> object:
        payload = {
            "command": command,
            "service": ["dhcp4"],
            "arguments": arguments,
        }
        try:
            response = self._transport.request(
                "POST",
                self._url,
                headers={"Authorization": f"Bearer {self._token}"},
                payload=payload,
            )
        except DdiProviderMutationError as exc:
            if mutation and not exc.outcome_unknown:
                raise DdiProviderMutationError(str(exc), outcome_unknown=True) from exc
            raise
        result = response[0] if isinstance(response, list) and response else response
        if not isinstance(result, dict):
            raise DdiProviderMutationError(
                "Kea response must be an object",
                outcome_unknown=mutation,
            )
        code = int(result.get("result", 1))
        if command == "reservation-get" and code == 3:
            return {}
        if code != 0:
            text = str(result.get("text", "Kea command failed"))
            raise DdiProviderMutationError(text, outcome_unknown=mutation)
        return result.get("arguments", {})

    def _lookup_arguments(self, change: DdiChange) -> dict[str, object]:
        metadata = DdiExecutorSupport.metadata(change)
        subnet_id = int(metadata.get("subnet_id", "0"))
        hw_address = metadata.get("hw_address")
        if subnet_id < 1 or not hw_address:
            raise ValidationError("Kea change requires subnet_id and hw_address metadata")
        return {"subnet-id": subnet_id, "identifier-type": "hw-address", "identifier": hw_address}

    def _reservation_arguments(self, change: DdiChange) -> dict[str, object]:
        metadata = DdiExecutorSupport.metadata(change)
        lookup = self._lookup_arguments(change)
        return {
            "reservation": {
                "subnet-id": lookup["subnet-id"],
                "hw-address": lookup["identifier"],
                "ip-address": change.value,
                "hostname": metadata.get("hostname", ""),
            }
        }

    @staticmethod
    def _extract_kea_arguments(payload: object) -> dict[str, object]:
        if not isinstance(payload, dict):
            return {}
        reservation = payload.get("reservation")
        return {"reservation": dict(reservation)} if isinstance(reservation, dict) else {}

    def _require_provider(self, change: DdiChange) -> None:
        if change.provider is not self.provider:
            raise ValidationError("Kea executor received a non-Kea change")
        if change.record_kind is not DdiRecordKind.DHCP_RESERVATION:
            raise ValidationError("Kea executor only accepts DHCP reservation changes")


class DdiExecutorFactory:
    @classmethod
    def from_environment(cls) -> tuple[DdiExecutor, ...]:
        executors: list[DdiExecutor] = []
        bind_server = os.environ.get("OPENINFRA_DDI_BIND_SERVER", "").strip()
        nsupdate_path = Path(
            os.environ.get("OPENINFRA_DDI_BIND_NSUPDATE_PATH", "/usr/bin/nsupdate")
        )
        dig_path = Path(os.environ.get("OPENINFRA_DDI_BIND_DIG_PATH", "/usr/bin/dig"))
        if bind_server and nsupdate_path.is_file() and dig_path.is_file():
            key_value = os.environ.get("OPENINFRA_DDI_BIND_KEY_FILE", "").strip()
            executors.append(
                BindNsupdateDdiExecutor(
                    BindExecutorSettings(
                        nsupdate_path=nsupdate_path,
                        dig_path=dig_path,
                        server=bind_server,
                        key_file=Path(key_value) if key_value else None,
                        timeout_seconds=cls._timeout("OPENINFRA_DDI_BIND_TIMEOUT_SECONDS"),
                    )
                )
            )
        powerdns_url = os.environ.get("OPENINFRA_DDI_POWERDNS_URL", "").strip()
        powerdns_key = os.environ.get("OPENINFRA_DDI_POWERDNS_API_KEY", "").strip()
        if powerdns_url and powerdns_key:
            executors.append(
                PowerDnsDdiExecutor(
                    powerdns_url,
                    powerdns_key,
                    os.environ.get("OPENINFRA_DDI_POWERDNS_SERVER_ID", "localhost"),
                    timeout_seconds=cls._timeout("OPENINFRA_DDI_POWERDNS_TIMEOUT_SECONDS"),
                )
            )
        kea_url = os.environ.get("OPENINFRA_DDI_KEA_URL", "").strip()
        kea_token = os.environ.get("OPENINFRA_DDI_KEA_TOKEN", "").strip()
        if kea_url and kea_token:
            executors.append(
                KeaDdiExecutor(
                    kea_url,
                    kea_token,
                    timeout_seconds=cls._timeout("OPENINFRA_DDI_KEA_TIMEOUT_SECONDS"),
                )
            )
        return tuple(executors)

    @staticmethod
    def _timeout(name: str) -> float:
        raw = os.environ.get(name, "15").strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValidationError(f"{name} must be numeric") from exc
        if not 0.1 <= value <= 120:
            raise ValidationError(f"{name} must be between 0.1 and 120")
        return value
