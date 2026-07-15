from __future__ import annotations

from datetime import UTC, datetime

from openinfra.application.container import ApplicationFactory
from openinfra.application.kubernetes_gitops_services import (
    AssessKubernetesGitOpsDriftCommand,
    AssessLatestKubernetesGitOpsDriftCommand,
    GetKubernetesGitOpsStateCommand,
    GetLatestKubernetesGitOpsStateCommand,
    ImportKubernetesGitOpsStateCommand,
    ListKubernetesGitOpsStatesCommand,
)
from openinfra.application.kubernetes_topology_services import (
    GetKubernetesCapacityTrendCommand,
    GetKubernetesTopologyCommand,
    GetLatestKubernetesTopologyCommand,
    ImportKubernetesTopologyCommand,
    ListKubernetesTopologiesCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand


def _guard_methods(target: object, names: tuple[str, ...], state: dict[str, int]) -> None:
    for name in names:
        original = getattr(target, name)

        def guarded(*args, _original=original, _name=name, **kwargs):
            assert state["depth"] > 0, f"{_name} called outside unit of work"
            return _original(*args, **kwargs)

        setattr(target, name, guarded)


def test_kubernetes_postgresql_repository_contract_requires_active_unit_of_work(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "u" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-uow-admin", ("admin",), token)
    )

    state = {"depth": 0}
    delegate = app.transaction_manager

    class GuardedUnitOfWork:
        def __init__(self) -> None:
            self._delegate = delegate.begin()

        def __enter__(self):
            self._delegate.__enter__()
            state["depth"] += 1
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            try:
                self._delegate.__exit__(exc_type, exc, traceback)
            finally:
                state["depth"] -= 1

        def commit(self) -> None:
            self._delegate.commit()

        def rollback(self) -> None:
            self._delegate.rollback()

    class GuardedTransactionManager:
        @staticmethod
        def begin():
            return GuardedUnitOfWork()

    topology_service = app.kubernetes_topology_service
    gitops_service = app.kubernetes_gitops_service
    topology_service._transaction_manager = GuardedTransactionManager()
    gitops_service._transaction_manager = GuardedTransactionManager()

    _guard_methods(
        app.kubernetes_topology_repository,
        (
            "find_snapshot_by_fingerprint",
            "save_snapshot",
            "append_event",
            "get_snapshot",
            "find_latest_snapshot",
            "list_snapshots",
        ),
        state,
    )
    _guard_methods(
        app.kubernetes_gitops_repository,
        (
            "find_state_by_fingerprint",
            "save_state",
            "append_event",
            "get_state",
            "find_latest_state",
            "list_states",
        ),
        state,
    )
    _guard_methods(app.flow_matrix_repository, ("list_declarations",), state)
    _guard_methods(app.sbom_repository, ("list_documents", "list_findings"), state)

    snapshot = topology_service.import_snapshot(
        ImportKubernetesTopologyCommand(
            "default",
            token,
            "cluster-uow-01",
            "cluster-uow-01",
            "kubernetes",
            "v1.34.1",
            "discovery:cluster-uow-01",
            datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
            (
                {"kind": "namespace", "uid": "ns-prod", "name": "production"},
                {
                    "kind": "node",
                    "uid": "node-01",
                    "name": "worker-01",
                    "capacity": {
                        "cpu_millicores": 4000,
                        "memory_bytes": 8_589_934_592,
                    },
                },
                {
                    "kind": "pod",
                    "uid": "pod-01",
                    "name": "api-01",
                    "namespace": "production",
                    "node_name": "worker-01",
                    "capacity": {
                        "cpu_request_millicores": 500,
                        "cpu_limit_millicores": 1000,
                        "cpu_usage_millicores": 400,
                        "memory_request_bytes": 268_435_456,
                        "memory_limit_bytes": 536_870_912,
                        "memory_usage_bytes": 201_326_592,
                    },
                },
            ),
            "eu-west",
            "par-01",
            "pytest",
        )
    )
    assert (
        topology_service.import_snapshot(
            ImportKubernetesTopologyCommand(
                "default",
                token,
                "cluster-uow-01",
                "cluster-uow-01",
                "kubernetes",
                "v1.34.1",
                "discovery:cluster-uow-01",
                datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
                (
                    {"kind": "namespace", "uid": "ns-prod", "name": "production"},
                    {
                        "kind": "node",
                        "uid": "node-01",
                        "name": "worker-01",
                        "capacity": {
                            "cpu_millicores": 4000,
                            "memory_bytes": 8_589_934_592,
                        },
                    },
                    {
                        "kind": "pod",
                        "uid": "pod-01",
                        "name": "api-01",
                        "namespace": "production",
                        "node_name": "worker-01",
                        "capacity": {
                            "cpu_request_millicores": 500,
                            "cpu_limit_millicores": 1000,
                            "cpu_usage_millicores": 400,
                            "memory_request_bytes": 268_435_456,
                            "memory_limit_bytes": 536_870_912,
                            "memory_usage_bytes": 201_326_592,
                        },
                    },
                ),
                "eu-west",
                "par-01",
                "pytest",
            )
        ).id
        == snapshot.id
    )

    topology_service.get_snapshot(GetKubernetesTopologyCommand("default", token, snapshot.id.value))
    topology_service.get_latest_snapshot(
        GetLatestKubernetesTopologyCommand("default", token, "cluster-uow-01")
    )
    topology_service.list_snapshots(
        ListKubernetesTopologiesCommand("default", token, cluster_key="cluster-uow-01")
    )
    topology_service.exposure(GetKubernetesTopologyCommand("default", token, snapshot.id.value))
    topology_service.security(GetKubernetesTopologyCommand("default", token, snapshot.id.value))
    topology_service.capacity_trend(
        GetKubernetesCapacityTrendCommand("default", token, "cluster-uow-01", limit=2)
    )

    gitops_state = gitops_service.import_state(
        ImportKubernetesGitOpsStateCommand(
            "default",
            token,
            "cluster-uow-01",
            "https://git.example.net/platform/kubernetes.git",
            "a" * 40,
            "clusters/prod",
            "platform",
            "production",
            datetime(2026, 7, 15, 11, 55, tzinfo=UTC),
            {"required_labels": [], "required_annotations": [], "allowed_environments": []},
            (
                {
                    "kind": "namespace",
                    "name": "production",
                    "owner": "platform",
                    "environment": "production",
                },
            ),
            "pytest",
        )
    )
    gitops_service.get_state(
        GetKubernetesGitOpsStateCommand("default", token, gitops_state.id.value)
    )
    gitops_service.get_latest_state(
        GetLatestKubernetesGitOpsStateCommand("default", token, "cluster-uow-01")
    )
    gitops_service.list_states(
        ListKubernetesGitOpsStatesCommand("default", token, cluster_key="cluster-uow-01")
    )
    gitops_service.assess(
        AssessKubernetesGitOpsDriftCommand(
            "default", token, gitops_state.id.value, snapshot.id.value, "pytest"
        )
    )
    gitops_service.assess_latest(
        AssessLatestKubernetesGitOpsDriftCommand("default", token, "cluster-uow-01", "pytest")
    )
