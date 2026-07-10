from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dependency_graph_services import (
    AnalyzeDependencySpofCommand,
    ExportDependencyGraphCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.common import ValidationError


class TestDependencySpofServices:
    def test_spof_analysis_is_deterministic_filtered_and_paginated(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        self._seed_topology(app, token)

        first = app.dependency_graph_service.analyze_spof(
            AnalyzeDependencySpofCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                max_depth=8,
                max_nodes=100,
                affected_sample_limit=1,
                limit=1,
            )
        )

        assert first.total_spof_count == 2
        assert len(first.candidates) == 1
        assert first.next_cursor is not None
        assert first.candidates[0].node.key == "service/gateway"
        assert first.candidates[0].affected_count == 1
        assert first.candidates[0].affected_sample == ("service/api",)
        assert first.candidates[0].affected_sample_truncated is False

        second = app.dependency_graph_service.analyze_spof(
            AnalyzeDependencySpofCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                max_depth=8,
                max_nodes=100,
                affected_sample_limit=1,
                limit=1,
                cursor=first.next_cursor,
            )
        )
        assert second.candidates[0].node.key == "database/main"
        assert second.candidates[0].rank == 2
        assert second.next_cursor is None

        database_only = app.dependency_graph_service.analyze_spof(
            AnalyzeDependencySpofCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                candidate_kinds=("database",),
            )
        )
        assert [item.node.key for item in database_only.candidates] == ["database/main"]

        with pytest.raises(ValidationError, match="does not match"):
            app.dependency_graph_service.analyze_spof(
                AnalyzeDependencySpofCommand(
                    tenant_id="default",
                    admin_token=token,
                    root_key="application/portal",
                    direction="outgoing",
                    candidate_kinds=("service",),
                    limit=1,
                    cursor=first.next_cursor,
                )
            )

        cursor_payload = json.loads(
            base64.urlsafe_b64decode(
                first.next_cursor + "=" * (-len(first.next_cursor) % 4)
            ).decode("utf-8")
        )
        cursor_payload["offset"] = 999
        outside_cursor = (
            base64.urlsafe_b64encode(
                json.dumps(cursor_payload, separators=(",", ":")).encode("utf-8")
            )
            .decode("ascii")
            .rstrip("=")
        )
        with pytest.raises(ValidationError, match="outside the result set"):
            app.dependency_graph_service.analyze_spof(
                AnalyzeDependencySpofCommand(
                    tenant_id="default",
                    admin_token=token,
                    root_key="application/portal",
                    direction="outgoing",
                    max_depth=8,
                    max_nodes=100,
                    affected_sample_limit=1,
                    limit=1,
                    cursor=outside_cursor,
                )
            )

    def test_spof_uses_alternative_paths_and_reports_bounded_completeness(
        self, tmp_path: Path
    ) -> None:
        app, token = self._application(tmp_path)
        self._seed_topology(app, token)

        report = app.dependency_graph_service.analyze_spof(
            AnalyzeDependencySpofCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                max_nodes=3,
            )
        )

        assert report.truncated is True
        assert report.as_dict()["complete"] is False
        assert "service/api" not in {item.node.key for item in report.candidates}
        assert "service/worker" not in {item.node.key for item in report.candidates}

    def test_graph_exports_are_deterministic_and_spof_annotated(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        self._seed_topology(app, token)

        json_export = app.dependency_graph_service.export(
            ExportDependencyGraphCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                format="json",
            )
        )
        payload = json.loads(json_export.content.decode("utf-8"))
        assert json_export.filename == "openinfra-graph-application-portal.json"
        assert json_export.spof_count == 2
        assert payload["spof"]["count"] == 2
        assert payload["node_count"] == 7

        csv_export = app.dependency_graph_service.export(
            ExportDependencyGraphCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                format="csv",
            )
        )
        csv_text = csv_export.content.decode("utf-8")
        assert csv_text.startswith("record_type,key,display_name")
        assert "node,database/main,Main database" in csv_text
        assert "edge,,,,,,,,,," in csv_text

        graphml_export = app.dependency_graph_service.export(
            ExportDependencyGraphCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                format="graphml",
            )
        )
        graphml = graphml_export.content.decode("utf-8")
        assert graphml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert '<node id="database/main">' in graphml
        assert '<data key="is_spof">true</data>' in graphml
        assert '<edge id="' in graphml

        without_spof = app.dependency_graph_service.export(
            ExportDependencyGraphCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                format="json",
                include_spof=False,
            )
        )
        assert without_spof.spof_count == 0

        with pytest.raises(ValidationError, match="json, csv or graphml"):
            app.dependency_graph_service.export(
                ExportDependencyGraphCommand(
                    tenant_id="default",
                    admin_token=token,
                    root_key="application/portal",
                    format="xlsx",
                )
            )

    def _application(self, tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "s" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="spof-reader",
                roles=("rsot:operator",),
                token=token,
            )
        )
        return app, token

    def _seed_topology(self, app, token: str) -> None:
        for key, kind, name in (
            ("application/portal", "application", "Portal"),
            ("service/gateway", "service", "Gateway"),
            ("service/api", "service", "API"),
            ("service/worker", "service", "Worker"),
            ("database/main", "database", "Main database"),
            ("storage/main", "storage", "Main storage"),
            ("service/metrics", "service", "Metrics"),
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
                    tags=("spof",),
                    source="manual",
                )
            )
        for source_key, target_key, relation_type in (
            ("application/portal", "service/gateway", "calls"),
            ("service/gateway", "service/api", "calls"),
            ("application/portal", "service/worker", "calls"),
            ("service/api", "database/main", "depends_on"),
            ("service/worker", "database/main", "depends_on"),
            ("database/main", "storage/main", "depends_on"),
            ("application/portal", "service/metrics", "observes"),
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
