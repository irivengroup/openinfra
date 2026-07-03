from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class SmokeError(Exception):
    """Raised when runtime smoke validation fails."""


@dataclass(frozen=True, slots=True)
class HttpJsonClient:
    base_url: str
    bearer_token: str
    timeout_seconds: float = 5.0

    def get(self, path: str) -> dict[str, object]:
        request = urllib.request.Request(
            self.base_url + path,
            headers={"Authorization": "Bearer " + self.bearer_token},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.bearer_token,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class RuntimeSmokeScenario:
    def __init__(self, client: HttpJsonClient, database_dsn: str) -> None:
        self._client = client
        self._database_dsn = database_dsn

    def run(self) -> None:
        self._wait_until_ready()
        self._assert_health()
        self._assert_version()
        self._assert_schema_status()
        self._assert_security_lifecycle()
        self._assert_identity_lifecycle()
        self._assert_source_of_truth_lifecycle()
        self._assert_source_governance_lifecycle()
        self._assert_access_policy_lifecycle()
        self._assert_api_ipam_idempotency()
        self._assert_cli_ipam_transaction()
        self._assert_audit_trail()

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + 60.0
        last_error = "not checked"
        while time.monotonic() < deadline:
            try:
                ready = self._client.get("/ready")
                if ready.get("ready") is True:
                    return
                last_error = json.dumps(ready, sort_keys=True)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = str(exc)
            time.sleep(2.0)
        raise SmokeError("runtime did not become ready: " + last_error)

    def _assert_health(self) -> None:
        health = self._client.get("/health")
        if health.get("status") != "ok":
            raise SmokeError("unexpected health response: " + json.dumps(health, sort_keys=True))

    def _assert_version(self) -> None:
        version = self._client.get("/api/v1/version")
        if version.get("version") != "0.11.0":
            raise SmokeError("unexpected version response: " + json.dumps(version, sort_keys=True))

    def _assert_schema_status(self) -> None:
        schema = self._client.get("/api/v1/database/schema")
        if schema.get("backend") != "postgresql" or schema.get("ready") is not True:
            raise SmokeError("unexpected schema status: " + json.dumps(schema, sort_keys=True))


    def _assert_security_lifecycle(self) -> None:
        worker_token = secrets.token_urlsafe(48)
        bootstrap_command = [
            "openinfra",
            "security",
            "bootstrap-token",
            "--backend",
            "postgresql",
            "--postgres-dsn",
            self._database_dsn,
            "--tenant",
            "default",
            "--subject",
            "runtime-viewer",
            "--role",
            "viewer",
            "--token",
            worker_token,
            "--ttl-seconds",
            "3600",
        ]
        completed = subprocess.run(
            bootstrap_command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise SmokeError("security bootstrap failed: " + completed.stderr.strip())
        listed = self._client.get("/api/v1/security/tokens?tenant_id=default&limit=50")
        if "token_hash" in json.dumps(listed):
            raise SmokeError("security token listing leaked token hashes")
        revoked = self._client.post(
            "/api/v1/security/revoke-token",
            {
                "tenant_id": "default",
                "actor": "docker-smoke",
                "target_token": worker_token,
                "admin_token": self._client.bearer_token,
            },
        )
        if revoked.get("revoked") is not True:
            raise SmokeError(
                "security token revocation failed: " + json.dumps(revoked, sort_keys=True)
            )


    def _assert_identity_lifecycle(self) -> None:
        user = self._client.post(
            "/api/v1/identity/users",
            {
                "tenant_id": "default",
                "actor": "docker-smoke",
                "username": "runtime-operator",
                "display_name": "Runtime Operator",
                "email": "runtime-operator@example.com",
                "roles": ["viewer"],
            },
        )
        group = self._client.post(
            "/api/v1/identity/groups",
            {
                "tenant_id": "default",
                "actor": "docker-smoke",
                "name": "runtime-ipam",
                "display_name": "Runtime IPAM Operators",
                "roles": ["ipam:operator"],
            },
        )
        membership = self._client.post(
            "/api/v1/identity/group-memberships",
            {
                "tenant_id": "default",
                "actor": "docker-smoke",
                "username": "runtime-operator",
                "group_name": "runtime-ipam",
            },
        )
        effective = self._client.get(
            "/api/v1/identity/effective?tenant_id=default&subject=runtime-operator"
        )
        if user.get("username") != "runtime-operator":
            raise SmokeError("identity user creation failed: " + json.dumps(user, sort_keys=True))
        if group.get("name") != "runtime-ipam":
            raise SmokeError("identity group creation failed: " + json.dumps(group, sort_keys=True))
        if membership.get("group_name") != "runtime-ipam":
            raise SmokeError(
                "identity group membership failed: " + json.dumps(membership, sort_keys=True)
            )
        if "ipam:operator" not in effective.get("effective_roles", []):
            raise SmokeError(
                "identity effective roles failed: " + json.dumps(effective, sort_keys=True)
            )



    def _assert_source_governance_lifecycle(self) -> None:
        rule = self._client.post(
            "/api/v1/sot/governance-rules",
            {
                "tenant_id": "default",
                "actor": "docker-smoke",
                "name": "runtime-serial-authority",
                "object_kind": "device",
                "attribute_path": "serial",
                "authoritative_source": "discovery",
                "priority": 800,
                "freshness_seconds": 3600,
                "conflict_strategy": "reject",
            },
        )
        listed = self._client.get(
            "/api/v1/sot/governance-rules?tenant_id=default&object_kind=device&limit=20"
        )
        evaluated = self._client.post(
            "/api/v1/sot/governance/evaluate",
            {
                "tenant_id": "default",
                "object_kind": "device",
                "incoming_source": "manual",
                "existing_attributes": {"serial": "DISC-001"},
                "incoming_attributes": {"serial": "MAN-002"},
            },
        )
        if rule.get("name") != "runtime-serial-authority":
            raise SmokeError(
                "source governance rule creation failed: " + json.dumps(rule, sort_keys=True)
            )
        if not listed.get("items"):
            raise SmokeError(
                "source governance listing failed: " + json.dumps(listed, sort_keys=True)
            )
        if evaluated.get("accepted") is not False:
            raise SmokeError(
                "source governance evaluation failed: " + json.dumps(evaluated, sort_keys=True)
            )

    def _assert_access_policy_lifecycle(self) -> None:
        rule = self._client.post(
            "/api/v1/access/rules",
            {
                "tenant_id": "default",
                "actor": "docker-smoke",
                "name": "runtime-docker-par1-prod",
                "permission": "ipam.allocate",
                "effect": "allow",
                "subjects": ["docker-runtime"],
                "site_codes": ["PAR1"],
                "environments": ["prod"],
            },
        )
        rules = self._client.get("/api/v1/access/rules?tenant_id=default&limit=20")
        evaluation = self._client.post(
            "/api/v1/access/evaluate",
            {
                "tenant_id": "default",
                "token": self._client.bearer_token,
                "permission": "ipam.allocate",
                "site_code": "PAR1",
                "environment": "prod",
            },
        )
        if rule.get("name") != "runtime-docker-par1-prod":
            raise SmokeError(
                "access policy rule creation failed: " + json.dumps(rule, sort_keys=True)
            )
        if not rules.get("items"):
            raise SmokeError("access policy listing failed: " + json.dumps(rules, sort_keys=True))
        if evaluation.get("allowed") is not True:
            raise SmokeError(
                "access policy evaluation failed: " + json.dumps(evaluation, sort_keys=True)
            )

    def _assert_api_ipam_idempotency(self) -> None:
        payload = {
            "tenant_id": "default",
            "actor": "docker-smoke-api",
            "vrf": "runtime",
            "prefix": "10.90.0.0/29",
            "hostname": "srv-api-runtime-01",
            "idempotency_key": "runtime-api-0001",
            "site_code": "PAR1",
            "environment": "prod",
        }
        first = self._client.post("/api/v1/ipam/allocate", payload)
        second = self._client.post("/api/v1/ipam/allocate", payload)
        if first.get("address") != "10.90.0.1" or first.get("created") is not True:
            raise SmokeError("unexpected first allocation: " + json.dumps(first, sort_keys=True))
        if second.get("address") != first.get("address") or second.get("created") is not False:
            raise SmokeError("idempotency failed: " + json.dumps(second, sort_keys=True))

    def _assert_cli_ipam_transaction(self) -> None:
        command = [
            "openinfra",
            "ipam",
            "allocate",
            "--backend",
            "postgresql",
            "--postgres-dsn",
            self._database_dsn,
            "--tenant",
            "default",
            "--auth-token",
            self._client.bearer_token,
            "--site-code",
            "PAR1",
            "--environment",
            "prod",
            "--vrf",
            "runtime",
            "--prefix",
            "10.90.1.0/29",
            "--hostname",
            "srv-cli-runtime-01",
            "--idempotency-key",
            "runtime-cli-0001",
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise SmokeError("CLI allocation failed: " + completed.stderr.strip())
        payload = json.loads(completed.stdout)
        if payload.get("address") != "10.90.1.1" or payload.get("created") is not True:
            raise SmokeError("unexpected CLI allocation: " + json.dumps(payload, sort_keys=True))

    def _assert_audit_trail(self) -> None:
        listed = self._client.get("/api/v1/audit/events?tenant_id=default&limit=50")
        if not listed.get("items"):
            raise SmokeError("audit event listing returned no data")
        if "record_hash" not in json.dumps(listed):
            raise SmokeError("audit event listing did not include integrity hashes")
        integrity = self._client.get("/api/v1/audit/integrity?tenant_id=default&limit=500")
        if integrity.get("valid") is not True:
            raise SmokeError(
                "audit integrity validation failed: " + json.dumps(integrity, sort_keys=True)
            )
        exported = self._client.post(
            "/api/v1/audit/export",
            {"tenant_id": "default", "format": "jsonl", "limit": 50},
        )
        if exported.get("content_type") != "application/x-ndjson":
            raise SmokeError("audit export failed: " + json.dumps(exported, sort_keys=True))


class RuntimeSmokeCli:
    @classmethod
    def main(cls) -> int:
        base_url = os.environ.get("OPENINFRA_API_BASE_URL", "http://api:8080").rstrip("/")
        database_dsn = os.environ.get("OPENINFRA_DATABASE_DSN", "").strip()
        token = os.environ.get("OPENINFRA_BOOTSTRAP_TOKEN", "").strip()
        if not database_dsn:
            print("OPENINFRA_DATABASE_DSN is required", file=sys.stderr)
            return 2
        if len(token) < 32:
            print("OPENINFRA_BOOTSTRAP_TOKEN is required", file=sys.stderr)
            return 2
        try:
            RuntimeSmokeScenario(HttpJsonClient(base_url, token), database_dsn).run()
        except SmokeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("OpenInfra runtime smoke validation passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(RuntimeSmokeCli.main())
