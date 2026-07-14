from __future__ import annotations

import json
from datetime import UTC, datetime

from pytest import MonkeyPatch
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.common import DomainEvent, EntityId, Pagination, TenantId
from openinfra.domain.kubernetes_topology import KubernetesResource, KubernetesTopologySnapshot
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLKubernetesTopologyRepository,
    PostgreSQLSessionRegistry,
)


def _repository() -> PostgreSQLKubernetesTopologyRepository:
    connection = FakeConnection()
    return PostgreSQLKubernetesTopologyRepository(
        PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=lambda _dsn, _profile: connection,
            )
        )
    )


def _snapshot() -> KubernetesTopologySnapshot:
    return KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "pytest",
        datetime(2026, 7, 14, 12, tzinfo=UTC),
        (
            KubernetesResource.create("namespace", "ns-prod", "production"),
            KubernetesResource.create("node", "node-1", "worker-01"),
        ),
        region="eu-west",
        site_code="par-01",
    )


def test_kubernetes_postgresql_repository_writes_snapshot_and_outbox(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    snapshot = _snapshot()
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    repo.save_snapshot(snapshot)
    repo.append_event(
        DomainEvent(
            EntityId.new(),
            snapshot.tenant_id,
            snapshot.id,
            "kubernetes.topology.imported",
            {"fingerprint": snapshot.fingerprint},
            datetime(2026, 7, 14, 12, 1, tzinfo=UTC),
        )
    )
    joined = "\n".join(query for query, _params in statements)
    assert "INSERT INTO kubernetes_topology_snapshots" in joined
    assert "INSERT INTO kubernetes_topology_event_outbox" in joined
    assert "ON CONFLICT (tenant_id, id) DO NOTHING" in joined
    assert json.loads(statements[0][1]["payload"])["fingerprint"] == snapshot.fingerprint  # type: ignore[arg-type]


def test_kubernetes_postgresql_repository_reads_filters_and_latest(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    snapshot = _snapshot()
    tenant = snapshot.tenant_id
    payload = json.dumps(snapshot.as_dict(include_resources=True))
    rows = iter(({"payload": payload}, {"payload": payload}, {"payload": payload}, None))
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: next(rows))
    assert repo.get_snapshot(tenant, snapshot.id.value) == snapshot
    assert repo.find_snapshot_by_fingerprint(tenant, snapshot.fingerprint) == snapshot
    assert repo.find_latest_snapshot(tenant, "cluster-par-01") == snapshot
    assert repo.get_snapshot(tenant, snapshot.id.value) is None

    captured: list[tuple[str, dict[str, object]]] = []

    def fetch_all(query: str, params: dict[str, object]) -> list[dict[str, object]]:
        captured.append((" ".join(query.split()), dict(params)))
        return [
            {
                "payload": payload,
                "observed_at": snapshot.observed_at,
                "imported_at": snapshot.imported_at,
                "id": snapshot.id.value,
            }
        ]

    monkeypatch.setattr(repo, "_fetch_all", fetch_all)
    page = repo.list_snapshots(
        tenant,
        Pagination(limit=10),
        cluster_key="CLUSTER-PAR-01",
        provider="KUBERNETES",
        site_code="PAR-01",
    )
    assert page.items == (snapshot,)
    query, params = captured[-1]
    assert "cluster_key = %(cluster_key)s" in query
    assert params["cluster_key"] == "cluster-par-01"
    assert params["provider"] == "kubernetes"
    assert params["site_code"] == "par-01"
