from __future__ import annotations

import json
from datetime import UTC, datetime

from pytest import MonkeyPatch
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.common import DomainEvent, EntityId, Pagination, TenantId
from openinfra.domain.kubernetes_gitops import (
    KubernetesGitOpsPolicy,
    KubernetesGitOpsResource,
    KubernetesGitOpsState,
)
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLKubernetesGitOpsRepository,
    PostgreSQLSessionRegistry,
)


def _repository() -> PostgreSQLKubernetesGitOpsRepository:
    connection = FakeConnection()
    return PostgreSQLKubernetesGitOpsRepository(
        PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=lambda _dsn, _profile: connection,
            )
        )
    )


def _state() -> KubernetesGitOpsState:
    policy = KubernetesGitOpsPolicy.create(
        required_labels=("app.kubernetes.io/name",),
        required_annotations=("openinfra.io/change-ref",),
        allowed_environments=("production",),
    )
    resource = KubernetesGitOpsResource.create(
        "workload",
        "api",
        namespace="production",
        labels={
            "app.kubernetes.io/name": "api",
            "app.kubernetes.io/owner": "payments",
            "app.kubernetes.io/environment": "production",
        },
        annotations={"openinfra.io/change-ref": "chg-001"},
        owner="payments",
        environment="production",
        attributes={"replicas": 3},
    )
    return KubernetesGitOpsState.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "https://git.example.net/platform/kubernetes.git",
        "b" * 40,
        "clusters/prod-par-01",
        "platform",
        "production",
        datetime(2026, 7, 15, 7, tzinfo=UTC),
        policy,
        (resource,),
    )


def test_kubernetes_gitops_postgresql_repository_writes_state_and_outbox(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    state = _state()
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    repo.save_state(state)
    repo.append_event(
        DomainEvent(
            EntityId.new(),
            state.tenant_id,
            state.id,
            "kubernetes.gitops.state.imported",
            {"fingerprint": state.fingerprint},
            datetime(2026, 7, 15, 7, 1, tzinfo=UTC),
        )
    )
    joined = "\n".join(query for query, _params in statements)
    assert "INSERT INTO kubernetes_gitops_states" in joined
    assert "INSERT INTO kubernetes_gitops_event_outbox" in joined
    assert "ON CONFLICT (tenant_id, id) DO NOTHING" in joined
    payload = json.loads(statements[0][1]["payload"])  # type: ignore[arg-type]
    assert payload["fingerprint"] == state.fingerprint
    assert payload["revision"] == "b" * 40


def test_kubernetes_gitops_postgresql_repository_reads_filters_and_latest(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    state = _state()
    tenant = state.tenant_id
    payload = json.dumps(state.as_dict(include_resources=True))
    rows = iter(({"payload": payload}, {"payload": payload}, {"payload": payload}, None))
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: next(rows))
    assert repo.get_state(tenant, state.id.value) == state
    assert repo.find_state_by_fingerprint(tenant, state.fingerprint) == state
    assert repo.find_latest_state(tenant, "CLUSTER-PAR-01") == state
    assert repo.get_state(tenant, state.id.value) is None

    captured: list[tuple[str, dict[str, object]]] = []

    def fetch_all(query: str, params: dict[str, object]) -> list[dict[str, object]]:
        captured.append((" ".join(query.split()), dict(params)))
        return [
            {
                "payload": payload,
                "captured_at": state.captured_at,
                "imported_at": state.imported_at,
                "id": state.id.value,
            }
        ]

    monkeypatch.setattr(repo, "_fetch_all", fetch_all)
    page = repo.list_states(
        tenant,
        Pagination(limit=10),
        cluster_key="CLUSTER-PAR-01",
        environment="PRODUCTION",
        owner="PLATFORM",
    )
    assert page.items == (state,)
    query, params = captured[-1]
    assert "cluster_key = %(cluster_key)s" in query
    assert "environment = %(environment)s" in query
    assert "owner = %(owner)s" in query
    assert params["cluster_key"] == "cluster-par-01"
    assert params["environment"] == "production"
    assert params["owner"] == "platform"
