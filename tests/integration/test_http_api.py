from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import AllocateIpCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestHttpApi:
    def test_health_and_ipam_allocation(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            health = self._get_json(base_url + "/health")
            ready = self._get_json(base_url + "/ready")
            version = self._get_json(base_url + "/api/v1/version")
            schema = self._get_json(base_url + "/api/v1/database/schema")
            allocation = self._post_json(
                base_url + "/api/v1/ipam/allocate",
                {
                    "tenant_id": "default",
                    "vrf": "default",
                    "prefix": "10.6.0.0/30",
                    "hostname": "srv-api-01",
                    "idempotency_key": "api-1",
                },
            )

            assert health["status"] == "ok"
            assert ready["ready"] is True
            assert ready["component"] == "json"
            assert version["version"] == "0.11.0"
            assert allocation["address"] == "10.6.0.1"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


    def test_authenticated_ipam_allocation_requires_valid_bearer_token(
        self,
        tmp_path: Path,
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "a" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-auth-client",
                roles=("ipam:operator",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            payload = {
                "tenant_id": "default",
                "vrf": "default",
                "prefix": "10.44.0.0/30",
                "hostname": "srv-api-secure-01",
                "idempotency_key": "api-secure-1",
            }
            try:
                self._post_json(base_url + "/api/v1/ipam/allocate", payload)
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            allocation = self._post_json(
                base_url + "/api/v1/ipam/allocate",
                payload,
                token=token,
            )
            whoami = self._post_json(
                base_url + "/api/v1/security/whoami",
                {"tenant_id": "default", "token": token},
            )

            assert allocation["address"] == "10.44.0.1"
            assert whoami["subject"] == "api-auth-client"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_api_returns_bad_request_on_invalid_payload(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            request = urllib.request.Request(
                base_url + "/api/v1/ipam/allocate",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(request, timeout=5)
            except urllib.error.HTTPError as exc:
                assert exc.code == 400
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _get_json(self, url: str, token: str | None = None) -> dict[str, object]:
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(
        self,
        url: str,
        payload: dict[str, object],
        token: str | None = None,
    ) -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_api_entrypoint_application_factory_backend_selection(self, tmp_path: Path) -> None:
        from argparse import Namespace

        from openinfra.domain.common import OpenInfraError
        from openinfra.interfaces.http_api import OpenInfraApiEntrypoint

        entrypoint = OpenInfraApiEntrypoint()
        json_app = entrypoint._create_application(
            Namespace(backend="json", data=tmp_path / "state.json", postgres_dsn=None)
        )

        assert json_app.ipam_service is not None
        try:
            entrypoint._create_application(
                Namespace(backend="postgresql", data=tmp_path / "state.json", postgres_dsn="")
            )
        except OpenInfraError as exc:
            assert "OPENINFRA_DATABASE_DSN" in str(exc)

    def test_security_lifecycle_api_endpoints(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "b" * 40
        worker_token = "c" * 40
        rotated_token = "d" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-admin-client",
                roles=("admin",),
                token=admin_token,
                ttl_seconds=3600,
            )
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-worker-client",
                roles=("viewer",),
                token=worker_token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            listed = self._get_json(
                base_url + "/api/v1/security/tokens?tenant_id=default&limit=10",
                token=admin_token,
            )
            revoked = self._post_json(
                base_url + "/api/v1/security/revoke-token",
                {
                    "tenant_id": "default",
                    "target_token": worker_token,
                    "admin_token": admin_token,
                },
            )
            rotated = self._post_json(
                base_url + "/api/v1/security/rotate-token",
                {
                    "tenant_id": "default",
                    "current_token": admin_token,
                    "token": rotated_token,
                    "ttl_seconds": 3600,
                },
            )
            try:
                self._get_json(
                    base_url + "/api/v1/security/tokens?tenant_id=default",
                    token=admin_token,
                )
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            listed_after_rotation = self._get_json(
                base_url + "/api/v1/security/tokens?tenant_id=default&include_inactive=true",
                token=rotated_token,
            )

            assert len(listed["items"]) == 2
            assert "token_hash" not in json.dumps(listed)
            assert revoked["revoked"] is True
            assert rotated["token_prefix"] == rotated_token[:12]
            assert len(listed_after_rotation["items"]) == 3
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_identity_api_endpoints_and_effective_roles(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "e" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="identity-api-admin",
                roles=("admin",),
                token=admin_token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            user = self._post_json(
                base_url + "/api/v1/identity/users",
                {
                    "tenant_id": "default",
                    "username": "api-user",
                    "display_name": "API User",
                    "email": "api-user@example.com",
                    "roles": ["viewer"],
                },
                token=admin_token,
            )
            group = self._post_json(
                base_url + "/api/v1/identity/groups",
                {
                    "tenant_id": "default",
                    "name": "api-dcim",
                    "display_name": "API DCIM",
                    "roles": ["dcim:operator"],
                },
                token=admin_token,
            )
            membership = self._post_json(
                base_url + "/api/v1/identity/group-memberships",
                {
                    "tenant_id": "default",
                    "username": "api-user",
                    "group_name": "api-dcim",
                },
                token=admin_token,
            )
            group_grant = self._post_json(
                base_url + "/api/v1/identity/group-roles",
                {"tenant_id": "default", "group_name": "api-dcim", "role": "ipam:operator"},
                token=admin_token,
            )
            user_grant = self._post_json(
                base_url + "/api/v1/identity/user-roles",
                {"tenant_id": "default", "username": "api-user", "role": "security:admin"},
                token=admin_token,
            )
            effective = self._get_json(
                base_url + "/api/v1/identity/effective?tenant_id=default&subject=api-user",
                token=admin_token,
            )

            assert user["username"] == "api-user"
            assert group["name"] == "api-dcim"
            assert membership["group_name"] == "api-dcim"
            assert group_grant["changed"] is True
            assert user_grant["changed"] is True
            assert effective["effective_roles"] == [
                "dcim:operator",
                "ipam:operator",
                "security:admin",
                "viewer",
            ]
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


class TestAccessPolicyHttpApi:
    def test_access_policy_api_restricts_authenticated_ipam_context(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "f" * 40
        worker_token = "g" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "api-admin", ("admin",), admin_token)
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                "default",
                "pytest",
                "api-worker",
                ("ipam:operator",),
                worker_token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            rule = TestHttpApi()._post_json(
                base_url + "/api/v1/access/rules",
                {
                    "tenant_id": "default",
                    "name": "api-worker-par1-prod",
                    "permission": "ipam.allocate",
                    "effect": "allow",
                    "subjects": ["api-worker"],
                    "site_codes": ["PAR1"],
                    "environments": ["prod"],
                },
                token=admin_token,
            )
            rules = TestHttpApi()._get_json(
                base_url + "/api/v1/access/rules?tenant_id=default&limit=10",
                token=admin_token,
            )
            evaluation = TestHttpApi()._post_json(
                base_url + "/api/v1/access/evaluate",
                {
                    "tenant_id": "default",
                    "token": worker_token,
                    "permission": "ipam.allocate",
                    "site_code": "PAR1",
                    "environment": "prod",
                },
            )
            allocation = TestHttpApi()._post_json(
                base_url + "/api/v1/ipam/allocate",
                {
                    "tenant_id": "default",
                    "vrf": "default",
                    "prefix": "10.88.0.0/30",
                    "hostname": "api-abac-01",
                    "idempotency_key": "api-abac-1",
                    "site_code": "PAR1",
                    "environment": "prod",
                },
                token=worker_token,
            )
            try:
                TestHttpApi()._post_json(
                    base_url + "/api/v1/ipam/allocate",
                    {
                        "tenant_id": "default",
                        "vrf": "default",
                        "prefix": "10.88.0.0/30",
                        "hostname": "api-abac-02",
                        "idempotency_key": "api-abac-2",
                        "site_code": "LON1",
                        "environment": "prod",
                    },
                    token=worker_token,
                )
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            deactivated = TestHttpApi()._post_json(
                base_url + "/api/v1/access/deactivate-rule",
                {"tenant_id": "default", "name": "api-worker-par1-prod"},
                token=admin_token,
            )

            assert rule["name"] == "api-worker-par1-prod"
            assert rules["items"][0]["permission"] == "ipam.allocate"
            assert evaluation["allowed"] is True
            assert allocation["address"] == "10.88.0.1"
            assert deactivated["deactivated"] is True
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


class TestAuditHttpApi:
    def test_audit_api_lists_exports_and_verifies_chain(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "i" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "audit-api-admin", ("admin",), admin_token)
        )
        app.ipam_service.allocate(
            AllocateIpCommand(
                tenant_id="default",
                actor="pytest",
                vrf="default",
                prefix="10.98.0.0/30",
                hostname="audit-api-srv",
                idempotency_key="audit-api-1",
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            helper = TestHttpApi()
            base_url = f"http://127.0.0.1:{server.server_port}"
            listed = helper._get_json(
                base_url + "/api/v1/audit/events?tenant_id=default&limit=10",
                token=admin_token,
            )
            exported = helper._post_json(
                base_url + "/api/v1/audit/export",
                {"tenant_id": "default", "format": "json", "limit": 10},
                token=admin_token,
            )
            verified = helper._get_json(
                base_url + "/api/v1/audit/integrity?tenant_id=default&limit=100",
                token=admin_token,
            )

            assert listed["items"]
            assert listed["items"][0]["integrity_valid"] is True
            assert exported["content_type"] == "application/json"
            assert exported["count"] >= 1
            assert verified["valid"] is True
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

class TestSourceOfTruthHttpApi:
    def test_sot_api_objects_relations_and_versions(self, tmp_path: Path) -> None:
        helper = TestHttpApi()
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "y" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="sot-api-admin",
                roles=("sot:operator",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            device = helper._post_json(
                base_url + "/api/v1/sot/objects",
                {
                    "tenant_id": "default",
                    "key": "device/api-srv-1",
                    "kind": "device",
                    "display_name": "API Server 1",
                    "attributes": {"serial": "API1"},
                    "tags": ["prod", "api"],
                    "source": "manual",
                },
                token=token,
            )
            helper._post_json(
                base_url + "/api/v1/sot/objects",
                {
                    "tenant_id": "default",
                    "key": "application/api-app",
                    "kind": "application",
                    "display_name": "API App",
                    "attributes": {"owner": "platform"},
                    "tags": ["prod"],
                    "source": "manual",
                },
                token=token,
            )
            relation = helper._post_json(
                base_url + "/api/v1/sot/relations",
                {
                    "tenant_id": "default",
                    "relation_type": "runs_on",
                    "source_key": "application/api-app",
                    "target_key": "device/api-srv-1",
                    "provenance": "manual",
                },
                token=token,
            )
            listed = helper._get_json(
                base_url + "/api/v1/sot/objects?tenant_id=default&kind=device&tag=api",
                token=token,
            )
            fetched = helper._get_json(
                base_url + "/api/v1/sot/objects?tenant_id=default&key=device/api-srv-1",
                token=token,
            )
            version = helper._get_json(
                base_url
                + "/api/v1/sot/object-versions?tenant_id=default"
                + "&key=device/api-srv-1&version=1",
                token=token,
            )
            relations = helper._get_json(
                base_url + "/api/v1/sot/relations?tenant_id=default&source_key=application/api-app",
                token=token,
            )
            try:
                helper._get_json(base_url + "/api/v1/sot/objects?tenant_id=default")
            except urllib.error.HTTPError as exc:
                assert exc.code == 401

            assert device["version"] == 1
            assert fetched["key"] == "device/api-srv-1"
            assert listed["items"][0]["key"] == "device/api-srv-1"
            assert version["payload"]["display_name"] == "API Server 1"
            assert relation["relation_type"] == "runs_on"
            assert relations["items"][0]["target_key"] == "device/api-srv-1"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

class TestSourceGovernanceHttpApi:
    def test_governance_api_rules_evaluation_and_deactivation(self, tmp_path: Path) -> None:
        helper = TestHttpApi()
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "k" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="governance-api-admin",
                roles=("sot:governance-admin",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            created = helper._post_json(
                base_url + "/api/v1/sot/governance-rules",
                {
                    "tenant_id": "default",
                    "name": "api-serial-authority",
                    "object_kind": "device",
                    "attribute_path": "serial",
                    "authoritative_source": "discovery",
                    "priority": 700,
                    "freshness_seconds": 3600,
                    "conflict_strategy": "reject",
                },
                token=token,
            )
            listed = helper._get_json(
                base_url + "/api/v1/sot/governance-rules?tenant_id=default&object_kind=device",
                token=token,
            )
            evaluated = helper._post_json(
                base_url + "/api/v1/sot/governance/evaluate",
                {
                    "tenant_id": "default",
                    "object_kind": "device",
                    "incoming_source": "manual",
                    "existing_attributes": {"serial": "S1"},
                    "incoming_attributes": {"serial": "S2"},
                },
                token=token,
            )
            deactivated = helper._post_json(
                base_url + "/api/v1/sot/governance/deactivate-rule",
                {"tenant_id": "default", "name": "api-serial-authority"},
                token=token,
            )

            assert created["name"] == "api-serial-authority"
            assert listed["items"][0]["attribute_path"] == "serial"
            assert evaluated["accepted"] is False
            assert evaluated["conflicts"][0]["authoritative_source"] == "discovery"
            assert deactivated["deactivated"] is True
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
