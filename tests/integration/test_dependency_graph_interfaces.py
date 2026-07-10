from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    UpsertSourceObjectCommand,
)
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestDependencyGraphInterfaces:
    def test_cli_exposes_traverse_impact_and_path(self, tmp_path: Path, capsys) -> None:
        data_path = tmp_path / "state.json"
        token = "c" * 40
        app = self._seed(data_path, token)
        del app

        base = [
            "--backend",
            "json",
            "--data",
            str(data_path),
            "--tenant",
            "default",
            "--admin-token",
            token,
        ]
        assert (
            OpenInfraCLI().run(
                [
                    "graph",
                    "traverse",
                    *base,
                    "--root-key",
                    "application/web",
                    "--direction",
                    "outgoing",
                ]
            )
            == 0
        )
        traverse = json.loads(capsys.readouterr().out)
        assert traverse["node_count"] == 3

        assert (
            OpenInfraCLI().run(
                ["graph", "impact", *base, "--root-key", "server/app-01", "--direction", "incoming"]
            )
            == 0
        )
        impact = json.loads(capsys.readouterr().out)
        assert impact["impacted_count"] == 2

        assert (
            OpenInfraCLI().run(
                [
                    "graph",
                    "path",
                    *base,
                    "--source-key",
                    "application/web",
                    "--target-key",
                    "server/app-01",
                ]
            )
            == 0
        )
        path = json.loads(capsys.readouterr().out)
        assert path["found"] is True
        assert path["hop_count"] == 2

        assert (
            OpenInfraCLI().run(
                [
                    "graph",
                    "spof",
                    *base,
                    "--root-key",
                    "application/web",
                    "--direction",
                    "outgoing",
                ]
            )
            == 0
        )
        spof = json.loads(capsys.readouterr().out)
        assert spof["spof_count"] == 1
        assert spof["items"][0]["node"]["key"] == "service/api"

        output = tmp_path / "graph.graphml"
        assert (
            OpenInfraCLI().run(
                [
                    "graph",
                    "export",
                    *base,
                    "--root-key",
                    "application/web",
                    "--direction",
                    "outgoing",
                    "--format",
                    "graphml",
                    "--output",
                    str(output),
                ]
            )
            == 0
        )
        metadata = json.loads(capsys.readouterr().out)
        assert metadata["format"] == "graphml"
        assert output.read_text(encoding="utf-8").startswith("<?xml")

        assert (
            OpenInfraCLI().run(
                [
                    "graph",
                    "export",
                    *base,
                    "--root-key",
                    "application/web",
                    "--direction",
                    "outgoing",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        exported_stdout = json.loads(capsys.readouterr().out)
        assert exported_stdout["root_key"] == "application/web"

    def test_http_api_exposes_graph_queries_and_rejects_missing_bearer(
        self, tmp_path: Path
    ) -> None:
        token = "h" * 40
        app = self._seed(tmp_path / "state.json", token)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            graph = self._get_json(
                base_url
                + "/api/v1/graph/traverse?"
                + urllib.parse.urlencode(
                    {
                        "tenant_id": "default",
                        "root_key": "application/web",
                        "direction": "outgoing",
                        "max_depth": "4",
                    }
                ),
                token,
            )
            impact = self._get_json(
                base_url
                + "/api/v1/graph/impact?"
                + urllib.parse.urlencode(
                    {
                        "tenant_id": "default",
                        "root_key": "server/app-01",
                        "direction": "incoming",
                    }
                ),
                token,
            )
            path = self._get_json(
                base_url
                + "/api/v1/graph/path?"
                + urllib.parse.urlencode(
                    {
                        "tenant_id": "default",
                        "source_key": "application/web",
                        "target_key": "server/app-01",
                    }
                ),
                token,
            )
            spof = self._get_json(
                base_url
                + "/api/v1/graph/spof?"
                + urllib.parse.urlencode(
                    {
                        "tenant_id": "default",
                        "root_key": "application/web",
                        "direction": "outgoing",
                    }
                ),
                token,
            )
            export_body, export_headers = self._get_bytes(
                base_url
                + "/api/v1/graph/export?"
                + urllib.parse.urlencode(
                    {
                        "tenant_id": "default",
                        "root_key": "application/web",
                        "direction": "outgoing",
                        "format": "csv",
                    }
                ),
                token,
            )
            discovery = self._get_json(base_url + "/api/v1", None)

            assert graph["node_count"] == 3
            assert impact["direct_count"] == 1
            assert path["found"] is True
            assert spof["spof_count"] == 1
            assert export_body.startswith(b"record_type,key,display_name")
            assert export_headers["content-type"].startswith("text/csv")
            assert "attachment; filename=" in export_headers["content-disposition"]
            assert discovery["documentation"]["graph"] == {
                "traverse": "/api/v1/graph/traverse",
                "impact": "/api/v1/graph/impact",
                "path": "/api/v1/graph/path",
                "spof": "/api/v1/graph/spof",
                "export": "/api/v1/graph/export",
            }

            unauthorized_routes = (
                "/api/v1/graph/traverse?tenant_id=default&root_key=application%2Fweb",
                "/api/v1/graph/impact?tenant_id=default&root_key=server%2Fapp-01",
                (
                    "/api/v1/graph/path?tenant_id=default&source_key=application%2Fweb"
                    "&target_key=server%2Fapp-01"
                ),
                "/api/v1/graph/spof?tenant_id=default&root_key=application%2Fweb",
                "/api/v1/graph/export?tenant_id=default&root_key=application%2Fweb",
            )
            for route in unauthorized_routes:
                try:
                    self._get_json(base_url + route, None)
                except urllib.error.HTTPError as exc:
                    assert exc.code == 401
                else:
                    raise AssertionError(f"graph endpoint accepted a missing bearer token: {route}")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _seed(self, data_path: Path, token: str):
        app = ApplicationFactory().create_json_application(data_path)
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="graph-interface-reader",
                roles=("rsot:operator",),
                token=token,
            )
        )
        for key, kind, name in (
            ("application/web", "application", "Web"),
            ("service/api", "service", "API"),
            ("server/app-01", "server", "Application server"),
        ):
            app.source_of_truth_service.upsert_object(
                UpsertSourceObjectCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=token,
                    key=key,
                    kind=kind,
                    display_name=name,
                    attributes_json="{}",
                    tags=("graph",),
                    source="manual",
                )
            )
        for source_key, target_key, relation_type in (
            ("application/web", "service/api", "calls"),
            ("service/api", "server/app-01", "runs_on"),
        ):
            app.source_of_truth_service.create_relation(
                CreateSourceRelationCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=token,
                    relation_type=relation_type,
                    source_key=source_key,
                    target_key=target_key,
                    provenance="manual",
                )
            )
        return app

    def _get_json(self, url: str, token: str | None) -> dict[str, object]:
        headers = {"Authorization": "Bearer " + token} if token else {}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert isinstance(payload, dict)
        return payload

    def _get_bytes(self, url: str, token: str) -> tuple[bytes, dict[str, str]]:
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read(), {key.lower(): value for key, value in response.headers.items()}


def test_runtime_openapi_documents_dependency_graph_contract() -> None:
    openapi = Path("docs/api/openapi.yaml").read_text(encoding="utf-8")

    for route in (
        "/api/v1/graph/traverse:",
        "/api/v1/graph/impact:",
        "/api/v1/graph/path:",
        "/api/v1/graph/spof:",
        "/api/v1/graph/export:",
    ):
        assert route in openapi
    assert "operationId: traverseDependencyGraph" in openapi
    assert "operationId: analyzeDependencyImpact" in openapi
    assert "operationId: findDependencyPath" in openapi
    assert "operationId: analyzeDependencySinglePointsOfFailure" in openapi
    assert "operationId: exportDependencyGraph" in openapi
    assert "application/graphml+xml" in openapi
    assert "maximum: 5000" in openapi
    assert "bearerToken" in openapi
