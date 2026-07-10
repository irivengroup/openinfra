from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dependency_graph_services import (
    AnalyzeDependencyImpactCommand,
    FindDependencyPathCommand,
    TraverseDependencyGraphCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.common import NotFoundError, ValidationError


class TestDependencyGraphServices:
    def test_traverse_path_and_impact_are_tenant_aware_and_cycle_safe(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        self._object(app, token, "application/portal", "application", "Portal")
        self._object(app, token, "service/api", "service", "API")
        self._object(app, token, "database/main", "database", "Main database")
        self._object(app, token, "server/db-01", "server", "DB server")
        self._relation(app, token, "application/portal", "service/api", "calls")
        self._relation(app, token, "service/api", "database/main", "depends_on")
        self._relation(app, token, "database/main", "server/db-01", "runs_on")
        self._relation(app, token, "server/db-01", "database/main", "hosts")

        graph = app.dependency_graph_service.traverse(
            TraverseDependencyGraphCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/portal",
                direction="outgoing",
                max_depth=6,
                max_nodes=50,
            )
        )
        path = app.dependency_graph_service.find_path(
            FindDependencyPathCommand(
                tenant_id="default",
                admin_token=token,
                source_key="application/portal",
                target_key="server/db-01",
                direction="outgoing",
            )
        )
        impact = app.dependency_graph_service.impact(
            AnalyzeDependencyImpactCommand(
                tenant_id="default",
                admin_token=token,
                root_key="server/db-01",
                direction="incoming",
                max_depth=6,
                max_nodes=50,
            )
        )

        assert [node.key for node in graph.nodes] == [
            "application/portal",
            "service/api",
            "database/main",
            "server/db-01",
        ]
        assert graph.max_depth_reached == 3
        assert graph.truncated is False
        assert path.found is True
        assert path.as_dict()["hop_count"] == 3
        assert [node.key for node in path.nodes] == [
            "application/portal",
            "service/api",
            "database/main",
            "server/db-01",
        ]
        assert {node.key for node in impact.impacted_nodes} == {
            "application/portal",
            "service/api",
            "database/main",
        }
        assert impact.direct_count == 1
        assert impact.indirect_count == 2
        assert impact.by_kind == {"application": 1, "database": 1, "service": 1}

    def test_filters_as_of_and_truncation_are_deterministic(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        for key, kind in (
            ("application/a", "application"),
            ("service/b", "service"),
            ("service/c", "service"),
            ("server/d", "server"),
        ):
            self._object(app, token, key, kind, key)
        now = datetime.now(UTC)
        self._relation(
            app,
            token,
            "application/a",
            "service/b",
            "calls",
            valid_from=now - timedelta(days=10),
        )
        self._relation(
            app,
            token,
            "application/a",
            "service/c",
            "observes",
            valid_from=now - timedelta(days=10),
        )
        self._relation(
            app,
            token,
            "service/b",
            "server/d",
            "calls",
            valid_from=now + timedelta(days=2),
        )

        filtered = app.dependency_graph_service.traverse(
            TraverseDependencyGraphCommand(
                "default",
                token,
                "application/a",
                direction="outgoing",
                relation_types=("calls",),
                as_of=now,
            )
        )
        truncated = app.dependency_graph_service.traverse(
            TraverseDependencyGraphCommand(
                "default",
                token,
                "application/a",
                direction="outgoing",
                max_nodes=2,
            )
        )

        assert [node.key for node in filtered.nodes] == ["application/a", "service/b"]
        assert filtered.relation_types == ("calls",)
        assert filtered.as_of == now.isoformat()
        assert truncated.truncated is True
        assert len(truncated.nodes) == 2

    def test_missing_paths_and_invalid_limits_are_controlled(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        self._object(app, token, "application/a", "application", "A")
        self._object(app, token, "application/b", "application", "B")

        path = app.dependency_graph_service.find_path(
            FindDependencyPathCommand("default", token, "application/a", "application/b")
        )
        assert path.found is False
        assert path.nodes == ()
        assert path.edges == ()

        with pytest.raises(NotFoundError):
            app.dependency_graph_service.traverse(
                TraverseDependencyGraphCommand("default", token, "missing/object")
            )
        with pytest.raises(ValidationError):
            app.dependency_graph_service.traverse(
                TraverseDependencyGraphCommand("default", token, "application/a", max_depth=0)
            )
        with pytest.raises(ValidationError):
            app.dependency_graph_service.traverse(
                TraverseDependencyGraphCommand(
                    "default", token, "application/a", direction="sideways"
                )
            )
        with pytest.raises(ValidationError):
            app.dependency_graph_service.traverse(
                TraverseDependencyGraphCommand(
                    "default", token, "application/a", as_of="2026-01-01"
                )
            )

    def _application(self, tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "g" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="graph-reader",
                roles=("rsot:operator",),
                token=token,
            )
        )
        return app, token

    def _object(self, app, token: str, key: str, kind: str, name: str) -> None:
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

    def _relation(
        self,
        app,
        token: str,
        source_key: str,
        target_key: str,
        relation_type: str,
        valid_from: datetime | None = None,
    ) -> None:
        app.source_of_truth_service.create_relation(
            CreateSourceRelationCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                relation_type=relation_type,
                source_key=source_key,
                target_key=target_key,
                provenance="manual",
                valid_from=valid_from,
            )
        )


def test_dependency_graph_internal_guards_and_bounds(tmp_path: Path, monkeypatch) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "guards.json")
    token = "z" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="graph-guard-reader",
            roles=("rsot:operator",),
            token=token,
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="application/root",
            kind="application",
            display_name="Root",
            attributes_json="{}",
            tags=("graph",),
            source="manual",
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="service/child",
            kind="service",
            display_name="Child",
            attributes_json="{}",
            tags=("graph",),
            source="manual",
        )
    )
    app.source_of_truth_service.create_relation(
        CreateSourceRelationCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            relation_type="calls",
            source_key="application/root",
            target_key="service/child",
            provenance="manual",
        )
    )
    service = app.dependency_graph_service

    same_object = service.find_path(
        FindDependencyPathCommand(
            tenant_id="default",
            admin_token=token,
            source_key="application/root",
            target_key="application/root",
        )
    )
    depth_limited = service.traverse(
        TraverseDependencyGraphCommand(
            tenant_id="default",
            admin_token=token,
            root_key="application/root",
            direction="outgoing",
            max_depth=1,
        )
    )

    assert same_object.found is True
    assert same_object.as_dict()["hop_count"] == 0
    assert depth_limited.max_depth_reached == 1
    assert service._datetime("") is None
    assert service._datetime(datetime.now(UTC)) is not None
    with pytest.raises(ValidationError, match="max_nodes"):
        service._limits(2, 1)
    with pytest.raises(ValidationError, match="ISO-8601"):
        service._datetime("not-a-date")

    from openinfra.domain.common import TenantId
    from openinfra.domain.dependency import GraphDirection
    from openinfra.domain.source_of_truth import SourceRelation, SourceRelationPage

    tenant_id = TenantId.from_value("default")
    unrelated = SourceRelation.create(
        tenant_id,
        "calls",
        "service/unrelated-a",
        "service/unrelated-b",
        "manual",
    )
    assert service._neighbor_key("application/root", unrelated, GraphDirection.BOTH) is None

    monkeypatch.setattr(service, "_relations", lambda *_args, **_kwargs: (unrelated,))
    with pytest.raises(ValidationError, match="unrelated relation"):
        service.traverse(
            TraverseDependencyGraphCommand(
                tenant_id="default",
                admin_token=token,
                root_key="application/root",
            )
        )

    repository = service._repository
    monkeypatch.undo()

    def cyclic_page(*_args, **_kwargs):
        return SourceRelationPage((), "same-cursor")

    monkeypatch.setattr(type(repository), "list_relations", cyclic_page)
    with pytest.raises(ValidationError, match="cyclic pagination cursor"):
        service._relation_pages(tenant_id, source_key="application/root")
