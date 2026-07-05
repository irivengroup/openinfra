from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from openinfra import __version__
from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import AllocateIpCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import OpenInfraError
from openinfra.interfaces.http_api import OpenApiDocumentProvider, OpenInfraThreadingServer


class TestHttpApi:
    def test_health_and_ipam_allocation(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            root = self._get_json(base_url + "/")
            api_index = self._get_json(base_url + "/api/v1")
            swagger = self._get_text(base_url + "/docs")
            swagger_alias = self._get_text(base_url + "/swagger")
            redoc = self._get_text(base_url + "/redoc")
            openapi = self._get_text(base_url + "/openapi.yaml")
            versioned_openapi = self._get_text(base_url + "/api/v1/openapi.yaml")
            health = self._get_json(base_url + "/health")
            ready = self._get_json(base_url + "/ready")
            version = self._get_json(base_url + "/api/v1/version")
            self._get_json(base_url + "/api/v1/database/schema")
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

            assert root["service"] == "openinfra-api"
            assert root["version"] == __version__
            assert root["health"] == "/health"
            assert root["readiness"] == "/ready"
            assert root["api"] == api_index["api"]
            assert api_index["api"] == {
                "version": "v1",
                "base_path": "/api/v1",
                "version_url": "/api/v1/version",
                "schema_url": "/api/v1/database/schema",
                "openapi_url": "/openapi.yaml",
            }
            assert root["documentation"] == {
                "swagger_ui": "/docs",
                "swagger_alias": "/swagger",
                "redoc": "/redoc",
                "openapi_yaml": "/openapi.yaml",
                "versioned_openapi_yaml": "/api/v1/openapi.yaml",
                "exports": {
                    "request": "/api/v1/exports/jobs",
                    "run": "/api/v1/exports/run",
                    "report": "/api/v1/exports/jobs",
                    "artifact": "/api/v1/exports/artifact",
                },
                "ressources_inventory": {
                    "objects": "/api/v1/ri/objects",
                    "object_versions": "/api/v1/ri/object-versions",
                    "relations": "/api/v1/ri/relations",
                    "governance_rules": "/api/v1/ri/governance-rules",
                    "legacy_sot_alias": "/api/v1/sot/objects",
                },
                "discovery": {
                    "collectors": "/api/v1/discovery/collectors",
                    "heartbeat": "/api/v1/discovery/collectors/heartbeat",
                    "authorize_job": "/api/v1/discovery/jobs/authorize",
                },
            }
            assert "SwaggerUIBundle" in swagger
            assert "SwaggerUIBundle" in swagger_alias
            assert "redoc.standalone.js" in redoc
            assert openapi.startswith("openapi: 3.1.0")
            assert versioned_openapi == openapi
            assert health["status"] == "ok"
            assert ready["ready"] is True
            assert ready["component"] == "json"
            assert version["version"] == __version__
            assert allocation["address"] == "10.6.0.1"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_discovery_collector_registry_http_contract(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "f" * 40
        fingerprint = "e" * 64
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="discovery-admin",
                roles=("security:admin",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            collector = self._post_json(
                base_url + "/api/v1/discovery/collectors",
                {
                    "tenant_id": "default",
                    "name": "SNMP PAR1",
                    "kind": "snmp",
                    "certificate_fingerprint": fingerprint,
                    "scopes": ["site/par1"],
                    "version": "1.0.0",
                    "vault_secret_ref": "vault://openinfra/discovery/snmp/par1",
                },
                token=token,
            )
            heartbeat = self._post_json(
                base_url + "/api/v1/discovery/collectors/heartbeat",
                {
                    "tenant_id": "default",
                    "collector_id": collector["id"],
                    "certificate_fingerprint": fingerprint,
                    "version": "1.0.1",
                },
            )
            decision = self._post_json(
                base_url + "/api/v1/discovery/jobs/authorize",
                {
                    "tenant_id": "default",
                    "collector_id": collector["id"],
                    "certificate_fingerprint": fingerprint,
                    "requested_scope": "site/par1",
                    "job_type": "snmp-scan",
                    "target": "par1-core",
                },
            )
            page = self._get_json(
                base_url + "/api/v1/discovery/collectors?tenant_id=default", token=token
            )
            disabled = self._post_json(
                base_url + "/api/v1/discovery/collectors/disable",
                {
                    "tenant_id": "default",
                    "collector_id": collector["id"],
                    "reason": "certificate rotation",
                },
                token=token,
            )
            try:
                self._post_json(
                    base_url + "/api/v1/discovery/jobs/authorize",
                    {
                        "tenant_id": "default",
                        "collector_id": collector["id"],
                        "certificate_fingerprint": fingerprint,
                        "requested_scope": "site/par1",
                        "job_type": "snmp-scan",
                        "target": "par1-core",
                    },
                )
            except urllib.error.HTTPError as exc:
                rejected = json.loads(exc.read().decode("utf-8"))
                assert exc.code == 403
                assert rejected["reasons"] == ["collector_not_active"]

            assert collector["status"] == "active"
            assert heartbeat["last_seen_version"] == "1.0.1"
            assert decision["authorized"] is True
            assert len(page["items"]) == 1
            assert disabled["status"] == "disabled"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_discovery_http_error_contracts(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "1" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="discovery-admin",
                roles=("security:admin",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            for url, expected_code in (
                (base_url + "/api/v1/discovery/collectors?tenant_id=default", 401),
                (base_url + "/api/v1/discovery/collectors?limit=bad", 400),
            ):
                try:
                    self._get_json(url)
                except urllib.error.HTTPError as exc:
                    assert exc.code == expected_code

            for route, payload in (
                (
                    "/api/v1/discovery/collectors",
                    {
                        "tenant_id": "default",
                        "name": "x",
                        "kind": "snmp",
                        "certificate_fingerprint": "bad",
                        "scopes": ["site/par1"],
                        "version": "1.0.0",
                    },
                ),
                (
                    "/api/v1/discovery/collectors/heartbeat",
                    {
                        "tenant_id": "default",
                        "collector_id": "missing",
                        "certificate_fingerprint": "bad",
                        "version": "1.0.0",
                    },
                ),
                (
                    "/api/v1/discovery/jobs/authorize",
                    {
                        "tenant_id": "default",
                        "collector_id": "missing",
                        "certificate_fingerprint": "bad",
                        "requested_scope": "site/par1",
                        "job_type": "snmp-scan",
                        "target": "x",
                    },
                ),
                (
                    "/api/v1/discovery/collectors/disable",
                    {"tenant_id": "default", "collector_id": "missing", "reason": "x"},
                ),
            ):
                try:
                    self._post_json(base_url + route, payload, token=token)
                except urllib.error.HTTPError as exc:
                    assert exc.code in {400, 401}
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_openapi_provider_and_unavailable_document_branch(self, tmp_path: Path) -> None:
        configured_openapi = tmp_path / "configured-openapi.yaml"
        configured_openapi.write_text("openapi: 3.1.0\ninfo:\n  title: Test\n", encoding="utf-8")
        provider = OpenApiDocumentProvider(str(configured_openapi))
        missing_provider = OpenApiDocumentProvider()
        missing_provider._candidate_paths = lambda: (tmp_path / "missing-openapi.yaml",)  # type: ignore[method-assign]

        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        server.openapi_document_provider = missing_provider
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            assert provider.read_yaml().startswith("openapi: 3.1.0")
            try:
                missing_provider.read_yaml()
            except OpenInfraError as exc:
                assert "OpenAPI document is unavailable" in str(exc)
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{server.server_port}/openapi.yaml", timeout=5
                )
            except urllib.error.HTTPError as exc:
                payload = json.loads(exc.read().decode("utf-8"))
                assert exc.code == 503
                assert "OpenAPI document is unavailable" in str(payload["error"])
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

    def test_import_dataset_api_endpoints(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "m" * 40
        csv_file = tmp_path / "api-import.csv"
        csv_file.write_text(
            "asset_key,kind,name,source,tags,serial\n"
            "device/api-601,device,API 601,api_import,prod,SN601\n",
            encoding="utf-8",
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-import-admin",
                roles=("ri:operator",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            report = self._post_json(
                base_url + "/api/v1/imports/datasets",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "admin_token": token,
                    "file_path": str(csv_file),
                    "format": "csv",
                    "mapping": {
                        "key": "asset_key",
                        "kind": "kind",
                        "display_name": "name",
                        "source": "source",
                        "tags": "tags",
                        "attributes.serial": "serial",
                    },
                    "batch_size": 100,
                },
            )
            persisted = self._get_json(
                base_url
                + "/api/v1/imports/report?tenant_id=default&job_id="
                + str(report["job_id"])
            )
            bad_request = urllib.request.Request(
                base_url + "/api/v1/imports/datasets",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(bad_request, timeout=5)
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            assert report["status"] == "validated"
            assert persisted["job_id"] == report["job_id"]
            assert persisted["create_count"] == 1
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_bulk_import_api_endpoints(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "n" * 40
        csv_file = tmp_path / "api-bulk-import.csv"
        csv_file.write_text(
            "asset_key,kind,name,source,tags,serial\n"
            "device/api-bulk-701,device,API Bulk 701,api_import,prod,SN701\n"
            "device/api-bulk-702,device,API Bulk 702,api_import,prod,SN702\n",
            encoding="utf-8",
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-bulk-import-admin",
                roles=("ri:operator",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            report = self._post_json(
                base_url + "/api/v1/imports/bulk-datasets",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "admin_token": token,
                    "file_path": str(csv_file),
                    "format": "csv",
                    "mapping": {
                        "key": "asset_key",
                        "kind": "kind",
                        "display_name": "name",
                        "source": "source",
                        "tags": "tags",
                        "attributes.serial": "serial",
                    },
                    "batch_size": 1,
                    "checkpoint_interval": 1,
                    "sample_limit": 5,
                },
            )
            persisted = self._get_json(
                base_url
                + "/api/v1/imports/bulk-report?tenant_id=default&job_id="
                + str(report["job_id"])
            )
            checkpoint = self._get_json(
                base_url
                + "/api/v1/imports/bulk-checkpoint?tenant_id=default&job_id="
                + str(report["job_id"])
            )
            bad_request = urllib.request.Request(
                base_url + "/api/v1/imports/bulk-datasets",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(bad_request, timeout=5)
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            assert report["status"] == "validated"
            assert report["metrics"]["batches_completed"] == 2
            assert persisted["job_id"] == report["job_id"]
            assert checkpoint["next_row_number"] == 3
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_migration_plan_api_endpoints(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "p" * 40
        csv_file = tmp_path / "api-netbox.csv"
        csv_file.write_text(
            "name,status,serial,extra\nsw-api-01,active,SN-API01,ignored\n",
            encoding="utf-8",
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-migration-admin",
                roles=("ri:operator",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            template = self._get_json(base_url + "/api/v1/imports/migration-template?source=netbox")
            report = self._post_json(
                base_url + "/api/v1/imports/migration-plans",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "admin_token": token,
                    "source": "netbox",
                    "file_path": str(csv_file),
                    "format": "csv",
                },
            )
            persisted = self._get_json(
                base_url
                + "/api/v1/imports/migration-report?tenant_id=default&job_id="
                + str(report["job_id"])
            )

            for bad_url in (
                base_url + "/api/v1/imports/migration-template?source=unknown",
                base_url + "/api/v1/imports/migration-report?tenant_id=default&job_id=missing",
            ):
                try:
                    self._get_json(bad_url)
                except urllib.error.HTTPError as exc:
                    assert exc.code == 400
            bad_request = urllib.request.Request(
                base_url + "/api/v1/imports/migration-plans",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(bad_request, timeout=5)
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            assert template["source"] == "netbox"
            assert report["status"] == "validated"
            assert any(gap["field"] == "extra" for gap in report["gaps"])
            assert persisted["job_id"] == report["job_id"]
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_export_api_endpoints(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "o" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="api-export-admin",
                roles=("ri:operator",),
                token=token,
            )
        )
        app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key="device/api-export-801",
                kind="device",
                display_name="API Export 801",
                attributes_json='{"serial":"SN801"}',
                tags=("prod",),
                source="api_export",
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            queued = self._post_json(
                base_url + "/api/v1/exports/jobs",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "admin_token": token,
                    "resource": "source_objects",
                    "format": "json",
                    "kind": "device",
                    "tag": "prod",
                },
            )
            completed = self._post_json(
                base_url + "/api/v1/exports/run",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "admin_token": token,
                    "job_id": queued["job_id"],
                    "page_size": 2,
                },
            )
            persisted = self._get_json(
                base_url + "/api/v1/exports/jobs?tenant_id=default&job_id=" + str(queued["job_id"]),
                token=token,
            )
            artifact = self._get_bytes(
                base_url
                + "/api/v1/exports/artifact?tenant_id=default&job_id="
                + str(queued["job_id"]),
                token=token,
            )

            assert queued["status"] == "queued"
            assert completed["status"] == "completed"
            assert persisted["artifact"]["signature_algorithm"] == "hmac-sha256"
            assert json.loads(artifact.decode("utf-8"))[0]["key"] == "device/api-export-801"
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

    def _get_bytes(self, url: str, token: str | None = None) -> bytes:
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read()

    def _get_text(self, url: str) -> str:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8")

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
    def test_ipam_conflict_detection_api_routes(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            helper = TestHttpApi()
            base_url = f"http://127.0.0.1:{server.server_port}"
            helper._post_json(
                base_url + "/api/v1/ipam/prefixes",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "cidr": "10.77.0.0/24",
                    "description": "api conflict scope",
                },
            )
            helper._post_json(
                base_url + "/api/v1/ipam/addresses",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "prefix": "10.77.0.0/24",
                    "address": "10.77.0.10",
                    "hostname": "api-owner",
                },
            )
            lease = helper._post_json(
                base_url + "/api/v1/ipam/dhcp-leases",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "prefix": "10.77.0.0/24",
                    "address": "10.77.0.10",
                    "mac_address": "aa:bb:cc:77:00:10",
                    "hostname": "api-rogue",
                    "source": "dhcp",
                },
            )
            dns = helper._post_json(
                base_url + "/api/v1/ipam/dns-observations",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "hostname": "ApiOwner.Example.Net.",
                    "address": "10.77.0.10",
                    "ptr_hostname": "old.example.net",
                    "source": "dns",
                },
            )
            report = helper._get_json(
                base_url + "/api/v1/ipam/conflicts?tenant_id=default&vrf=prod"
            )

            conflict_types = {item["type"] for item in report["conflicts"]}
            assert lease["mac_address"] == "aa:bb:cc:77:00:10"
            assert dns["hostname"] == "apiowner.example.net"
            assert report["total"] >= 3
            assert "duplicate_address" in conflict_types
            assert "lease_conflict" in conflict_types
            assert "dns_ptr_divergence" in conflict_types
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

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
                roles=("ri:operator",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            device = helper._post_json(
                base_url + "/api/v1/ri/objects",
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
                base_url + "/api/v1/ri/objects",
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
                base_url + "/api/v1/ri/relations",
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
                base_url + "/api/v1/ri/objects?tenant_id=default&kind=device&tag=api",
                token=token,
            )
            fetched = helper._get_json(
                base_url + "/api/v1/ri/objects?tenant_id=default&key=device/api-srv-1",
                token=token,
            )
            version = helper._get_json(
                base_url
                + "/api/v1/ri/object-versions?tenant_id=default"
                + "&key=device/api-srv-1&version=1",
                token=token,
            )
            relations = helper._get_json(
                base_url + "/api/v1/ri/relations?tenant_id=default&source_key=application/api-app",
                token=token,
            )
            try:
                helper._get_json(base_url + "/api/v1/ri/objects?tenant_id=default")
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
                roles=("ri:governance-admin",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            created = helper._post_json(
                base_url + "/api/v1/ri/governance-rules",
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
                base_url + "/api/v1/ri/governance-rules?tenant_id=default&object_kind=device",
                token=token,
            )
            evaluated = helper._post_json(
                base_url + "/api/v1/ri/governance/evaluate",
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
                base_url + "/api/v1/ri/governance/deactivate-rule",
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

    def test_dcim_define_room_api_requires_dcim_write_when_authenticated(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        viewer_token = "v" * 40
        dcim_token = "m" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="viewer-api-client",
                roles=("viewer",),
                token=viewer_token,
            )
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="dcim-api-client",
                roles=("dcim:operator",),
                token=dcim_token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            payload = {
                "tenant_id": "default",
                "site_code": "TLS1",
                "site_name": "Toulouse 1",
                "country": "FR",
                "region": "Occitanie",
                "city": "Toulouse",
                "building_code": "BAT-T",
                "building_name": "Building T",
                "floor_code": "F01",
                "floor_name": "First floor",
                "floor_index": 1,
                "room_code": "MDF1",
                "room_name": "MDF Toulouse",
                "rows": ["A", "B"],
                "columns": ["01", "02"],
                "zone_code": "Z1",
                "zone_name": "Zone 1",
                "zone_rows": ["A"],
                "zone_columns": ["01"],
            }
            helper = TestHttpApi()
            try:
                helper._post_json(base_url + "/api/v1/dcim/rooms", payload, token=viewer_token)
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            created = helper._post_json(
                base_url + "/api/v1/dcim/rooms",
                payload,
                token=dcim_token,
            )

            assert created["site"] == "TLS1"
            assert created["floor"] == "F01"
            assert created["zone"] == "Z1"
            assert created["created"]["room"] is True
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_dcim_rack_runtime_api_endpoints(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        helper = TestHttpApi()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            room = helper._post_json(
                base_url + "/api/v1/dcim/rooms",
                {
                    "tenant_id": "default",
                    "site_code": "BOR1",
                    "site_name": "Bordeaux 1",
                    "country": "FR",
                    "region": "Nouvelle-Aquitaine",
                    "city": "Bordeaux",
                    "building_code": "BAT-B",
                    "building_name": "Building B",
                    "floor_code": "F01",
                    "floor_name": "First floor",
                    "floor_index": 1,
                    "room_code": "MDF1",
                    "room_name": "MDF Bordeaux",
                    "rows": ["A"],
                    "columns": ["01"],
                    "zone_code": "Z1",
                    "zone_name": "Zone 1",
                    "zone_rows": ["A"],
                    "zone_columns": ["01"],
                },
            )
            rack = helper._post_json(
                base_url + "/api/v1/dcim/racks",
                {
                    "tenant_id": "default",
                    "site": "BOR1",
                    "building": "BAT-B",
                    "floor": "F01",
                    "room": "MDF1",
                    "zone": "Z1",
                    "rack": "R01",
                    "row": "A",
                    "column": "01",
                    "units": 48,
                    "faces": ["front", "rear"],
                    "max_weight_kg": 900,
                    "power_capacity_watts": 24000,
                },
            )
            capacity = helper._get_json(
                base_url
                + "/api/v1/dcim/rack-capacity?tenant_id=default"
                + "&site=BOR1&building=BAT-B&room=MDF1&rack=R01"
            )

            assert room["room"] == "MDF1"
            assert rack["rack"] == "R01"
            assert rack["faces"] == ["front", "rear"]
            assert capacity["units"] == 48
            assert capacity["faces_capacity"]["front"]["free_count"] == 48
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def test_dcim_locator_sheet_and_scan_api_endpoint(tmp_path: Path) -> None:
    from openinfra.application.dcim_services import LocateEquipmentCommand

    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    app.dcim_service.locate_equipment(
        LocateEquipmentCommand(
            tenant_id="default",
            actor="pytest",
            asset_tag="API-QR-1",
            equipment_name="API QR Server",
            site="PAR1",
            building="BAT-A",
            floor="F01",
            room="MMR1",
            zone=None,
            row="A",
            column="01",
            rack=None,
            u_position=None,
            rack_face=None,
            u_height=None,
            x=None,
            y=None,
            z=None,
        )
    )
    token = "e" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="dcim-qr-client",
            roles=("dcim:operator",),
            token=token,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    helper = TestHttpApi()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        sheet = helper._get_json(
            base_url + "/api/v1/dcim/locator-sheet?tenant_id=default&asset_tag=API-QR-1",
            token=token,
        )
        payload = str(sheet["locator"]["payload"])
        proof = helper._post_json(
            base_url + "/api/v1/dcim/verify-scan",
            {"tenant_id": "default", "asset_tag": "API-QR-1", "payload": payload},
            token=token,
        )
        html = helper._get_json(
            base_url
            + "/api/v1/dcim/locator-sheet?tenant_id=default&asset_tag=API-QR-1&format=html",
            token=token,
        )
        try:
            helper._post_json(
                base_url + "/api/v1/dcim/verify-scan",
                {"tenant_id": "default", "asset_tag": "API-QR-1", "payload": "bad"},
                token=token,
            )
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        assert sheet["asset_tag"] == "API-QR-1"
        assert str(sheet["qr_svg"]).startswith("<svg")
        assert proof["verified"] is True
        assert "OpenInfra fiche localisation" in str(html["html"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
