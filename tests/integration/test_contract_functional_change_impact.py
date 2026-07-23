from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.dependency_graph_services import AnalyzeChangeImpactCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    UpsertSourceObjectCommand,
)
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def test_tst_func_0005_change_impact_lists_business_services_critical_dependencies_and_spof(
    tmp_path: Path, capsys
) -> None:
    data_path = tmp_path / "state.json"
    token = "i" * 40
    app = _seed(data_path, token)

    report = app.dependency_graph_service.analyze_change_impact(
        AnalyzeChangeImpactCommand(
            tenant_id="default",
            admin_token=token,
            root_key="server/db-01",
            direction="incoming",
            max_depth=8,
            max_nodes=100,
        )
    )
    payload = report.as_dict()

    assert payload["business_service_count"] == 5
    assert {item["key"] for item in payload["business_services"]} == {
        "database/main",
        "service/api",
        "service/batch",
        "application/portal",
        "application/billing",
    }
    assert payload["root_spof_risk"] is True
    risks = {item["node"]["key"]: item for item in payload["critical_dependencies"]}
    assert risks["database/main"]["affected_business_service_count"] == 4
    assert risks["database/main"]["risk_level"] == "high"
    assert risks["service/api"]["affected_business_service_keys"] == [
        "application/billing",
        "application/portal",
    ]
    assert payload["complete"] is True

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
                "change-impact",
                *base,
                "--root-key",
                "server/db-01",
                "--direction",
                "incoming",
            ]
        )
        == 0
    )
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["business_service_count"] == 5
    assert cli_payload["critical_dependency_count"] == 2

    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        query = urllib.parse.urlencode(
            {
                "tenant_id": "default",
                "root_key": "server/db-01",
                "direction": "incoming",
            }
        )
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/api/v1/graph/change-impact?{query}",
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            http_payload = json.loads(response.read().decode("utf-8"))
        assert http_payload["business_service_count"] == 5
        assert http_payload["critical_dependency_count"] == 2
        assert http_payload["root_spof_risk"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _seed(data_path: Path, token: str):
    app = ApplicationFactory().create_json_application(data_path)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="impact-reader",
            roles=("rsot:operator",),
            token=token,
        )
    )
    for key, kind, name in (
        ("server/db-01", "server", "Database server"),
        ("database/main", "database", "Main database"),
        ("service/api", "service", "Customer API"),
        ("service/batch", "service", "Nightly batch"),
        ("application/portal", "application", "Customer portal"),
        ("application/billing", "application", "Billing application"),
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
                tags=("impact",),
                source="manual",
            )
        )
    for source_key, target_key, relation_type in (
        ("database/main", "server/db-01", "runs_on"),
        ("service/api", "database/main", "depends_on"),
        ("service/batch", "database/main", "depends_on"),
        ("application/portal", "service/api", "calls"),
        ("application/billing", "service/api", "calls"),
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


def test_change_impact_filters_bounds_and_empty_business_scope(tmp_path: Path) -> None:
    token = "j" * 40
    app = _seed(tmp_path / "state.json", token)

    bounded = app.dependency_graph_service.analyze_change_impact(
        AnalyzeChangeImpactCommand(
            tenant_id="default",
            admin_token=token,
            root_key="server/db-01",
            direction="incoming",
            max_nodes=2,
        )
    ).as_dict()
    assert bounded["complete"] is False
    assert bounded["truncated"] is True
    assert bounded["impacted_count"] == 1

    empty = app.dependency_graph_service.analyze_change_impact(
        AnalyzeChangeImpactCommand(
            tenant_id="default",
            admin_token=token,
            root_key="server/db-01",
            direction="incoming",
            business_service_kinds=("network-appliance",),
            business_service_resource_types=("switch",),
        )
    ).as_dict()
    assert empty["business_services"] == []
    assert empty["critical_dependencies"] == []
    assert empty["root_spof_risk"] is False

    from openinfra.domain.common import ValidationError

    for invalid_limit in (0, 201):
        try:
            app.dependency_graph_service.analyze_change_impact(
                AnalyzeChangeImpactCommand(
                    tenant_id="default",
                    admin_token=token,
                    root_key="server/db-01",
                    affected_sample_limit=invalid_limit,
                )
            )
        except ValidationError as exc:
            assert "affected sample limit" in str(exc)
        else:
            raise AssertionError(f"invalid sample limit accepted: {invalid_limit}")
