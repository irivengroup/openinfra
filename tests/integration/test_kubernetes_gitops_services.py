from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.kubernetes_gitops_services import (
    AssessKubernetesGitOpsDriftCommand,
    AssessLatestKubernetesGitOpsDriftCommand,
    GetKubernetesGitOpsStateCommand,
    GetLatestKubernetesGitOpsStateCommand,
    ImportKubernetesGitOpsStateCommand,
    ListKubernetesGitOpsStatesCommand,
)
from openinfra.application.kubernetes_topology_services import ImportKubernetesTopologyCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import AccessDeniedError, NotFoundError
from openinfra.domain.kubernetes_gitops import KubernetesGitOpsComplianceStatus

COMMIT = "b" * 40


def _app(tmp_path: Path) -> tuple[object, str]:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "g" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "gitops-admin", ("admin",), token)
    )
    return app, token


def _observed_resources(replicas: int = 2) -> tuple[dict[str, object], ...]:
    return (
        {
            "kind": "namespace",
            "uid": "ns-prod",
            "name": "production",
            "labels": {
                "app.kubernetes.io/name": "production",
                "app.kubernetes.io/owner": "platform",
                "app.kubernetes.io/environment": "production",
            },
            "attributes": {"annotations": {"openinfra.io/change-ref": "chg-001"}},
        },
        {
            "kind": "workload",
            "uid": "deploy-api",
            "name": "api",
            "namespace": "production",
            "labels": {
                "app.kubernetes.io/name": "api",
                "app.kubernetes.io/owner": "payments",
                "app.kubernetes.io/environment": "production",
            },
            "attributes": {
                "annotations": {"openinfra.io/change-ref": "chg-001"},
                "replicas": replicas,
            },
        },
    )


def _expected_resources() -> tuple[dict[str, object], ...]:
    return (
        {
            "kind": "namespace",
            "name": "production",
            "labels": {
                "app.kubernetes.io/name": "production",
                "app.kubernetes.io/owner": "platform",
                "app.kubernetes.io/environment": "production",
            },
            "annotations": {"openinfra.io/change-ref": "chg-001"},
            "owner": "platform",
            "environment": "production",
        },
        {
            "kind": "workload",
            "name": "api",
            "namespace": "production",
            "labels": {
                "app.kubernetes.io/name": "api",
                "app.kubernetes.io/owner": "payments",
                "app.kubernetes.io/environment": "production",
            },
            "annotations": {"openinfra.io/change-ref": "chg-001"},
            "owner": "payments",
            "environment": "production",
            "attributes": {"replicas": 3},
        },
    )


def _policy() -> dict[str, object]:
    return {
        "required_labels": ["app.kubernetes.io/name"],
        "required_annotations": ["openinfra.io/change-ref"],
        "allowed_environments": ["production", "staging"],
    }


def seeded_gitops_application(
    state_path: Path, *, observed_replicas: int = 2
) -> tuple[object, str, object, object]:
    """Build a persisted application with one observed and one expected GitOps state."""
    app, token = _app(state_path.parent)
    # Rebind to the exact state path expected by HTTP/CLI tests when needed.
    if state_path.name != "state.json":
        app = ApplicationFactory().create_json_application(state_path, seed=False)
        token = "g" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "gitops-admin", ("admin",), token)
        )
    observed = app.kubernetes_topology_service.import_snapshot(
        ImportKubernetesTopologyCommand(
            "default",
            token,
            "cluster-par-01",
            "prod-par-01",
            "kubernetes",
            "v1.34.1",
            "discovery:cluster-par-01",
            datetime(2026, 7, 15, 7, 5, tzinfo=UTC),
            _observed_resources(observed_replicas),
            "eu-west",
            "par-01",
            "pytest",
        )
    )
    expected = app.kubernetes_gitops_service.import_state(
        ImportKubernetesGitOpsStateCommand(
            "default",
            token,
            "cluster-par-01",
            "https://git.example.net/platform/kubernetes.git",
            COMMIT,
            "clusters/prod-par-01",
            "platform",
            "production",
            datetime(2026, 7, 15, 7, 0, tzinfo=UTC),
            _policy(),
            _expected_resources(),
            "pytest",
        )
    )
    return app, token, expected, observed


def test_gitops_service_import_list_latest_and_drift_audit(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    observed = app.kubernetes_topology_service.import_snapshot(
        ImportKubernetesTopologyCommand(
            "default",
            token,
            "cluster-par-01",
            "prod-par-01",
            "kubernetes",
            "v1.34.1",
            "discovery:cluster-par-01",
            datetime(2026, 7, 15, 7, 5, tzinfo=UTC),
            _observed_resources(),
            "eu-west",
            "par-01",
            "pytest",
        )
    )
    command = ImportKubernetesGitOpsStateCommand(
        "default",
        token,
        "cluster-par-01",
        "https://git.example.net/platform/kubernetes.git",
        COMMIT,
        "clusters/prod-par-01",
        "platform",
        "production",
        datetime(2026, 7, 15, 7, 0, tzinfo=UTC),
        _policy(),
        _expected_resources(),
        "pytest",
    )
    state = app.kubernetes_gitops_service.import_state(command)
    assert app.kubernetes_gitops_service.import_state(command).id == state.id
    assert (
        app.kubernetes_gitops_service.get_state(
            GetKubernetesGitOpsStateCommand("default", token, state.id.value)
        ).fingerprint
        == state.fingerprint
    )
    assert (
        app.kubernetes_gitops_service.get_latest_state(
            GetLatestKubernetesGitOpsStateCommand("default", token, "cluster-par-01")
        ).id
        == state.id
    )
    page = app.kubernetes_gitops_service.list_states(
        ListKubernetesGitOpsStatesCommand(
            "default",
            token,
            limit=1,
            cluster_key="cluster-par-01",
            environment="production",
            owner="platform",
        )
    )
    assert [item.id for item in page.items] == [state.id]

    report = app.kubernetes_gitops_service.assess(
        AssessKubernetesGitOpsDriftCommand(
            "default", token, state.id.value, observed.id.value, "pytest"
        )
    )
    assert report.status is KubernetesGitOpsComplianceStatus.DRIFT
    assert report.as_dict()["automatic_remediation"] is False
    latest = app.kubernetes_gitops_service.assess_latest(
        AssessLatestKubernetesGitOpsDriftCommand("default", token, "cluster-par-01", "pytest")
    )
    assert latest.fingerprint == report.fingerprint
    gitops_events = list(app.store.data["kubernetes_gitops_event_outbox"].values())
    assert {item["name"] for item in gitops_events} == {
        "kubernetes.gitops.state.imported",
        "kubernetes.gitops.drift.detected",
    }
    actions = [item.get("action") for item in app.store.data["audit_events"]]
    assert "kubernetes.gitops.state.imported" in actions
    assert actions.count("kubernetes.gitops.assessed") == 2


def test_gitops_service_latest_prefers_newer_expected_state_and_handles_not_found(
    tmp_path: Path,
) -> None:
    app, token = _app(tmp_path)
    first = app.kubernetes_gitops_service.import_state(
        ImportKubernetesGitOpsStateCommand(
            "default",
            token,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            datetime(2026, 7, 15, 6, 0, tzinfo=UTC),
            _policy(),
            _expected_resources(),
        )
    )
    second = app.kubernetes_gitops_service.import_state(
        ImportKubernetesGitOpsStateCommand(
            "default",
            token,
            "cluster-par-01",
            "https://git.example/repo.git",
            "c" * 40,
            "clusters/prod",
            "platform",
            "production",
            first.captured_at + timedelta(minutes=10),
            _policy(),
            _expected_resources(),
        )
    )
    assert second.id != first.id
    assert (
        app.kubernetes_gitops_service.get_latest_state(
            GetLatestKubernetesGitOpsStateCommand("default", token, "cluster-par-01")
        ).id
        == second.id
    )
    with pytest.raises(NotFoundError, match="GitOps state"):
        app.kubernetes_gitops_service.get_state(
            GetKubernetesGitOpsStateCommand(
                "default", token, "00000000-0000-0000-0000-000000000000"
            )
        )
    with pytest.raises(NotFoundError, match="topology snapshot"):
        app.kubernetes_gitops_service.assess(
            AssessKubernetesGitOpsDriftCommand(
                "default",
                token,
                second.id.value,
                "00000000-0000-0000-0000-000000000000",
            )
        )


def test_gitops_service_enforces_kubernetes_read_write_roles(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    operator_token = "o" * 40
    reader_token = "r" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            "default", "pytest", "kubernetes-operator", ("kubernetes:operator",), operator_token
        )
    )
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            "default", "pytest", "kubernetes-reader", ("kubernetes:reader",), reader_token
        )
    )
    command = ImportKubernetesGitOpsStateCommand(
        "default",
        operator_token,
        "cluster-par-01",
        "https://git.example/repo.git",
        COMMIT,
        "clusters/prod",
        "platform",
        "production",
        datetime.now(UTC),
        _policy(),
        _expected_resources(),
    )
    state = app.kubernetes_gitops_service.import_state(command)
    assert (
        app.kubernetes_gitops_service.get_state(
            GetKubernetesGitOpsStateCommand("default", reader_token, state.id.value)
        ).id
        == state.id
    )
    with pytest.raises(AccessDeniedError):
        app.kubernetes_gitops_service.import_state(
            ImportKubernetesGitOpsStateCommand(
                command.tenant_id,
                reader_token,
                command.cluster_key,
                command.repository_ref,
                command.revision,
                command.source_path,
                command.owner,
                command.environment,
                command.captured_at,
                command.policy,
                command.resources,
            )
        )


def test_gitops_service_not_found_paths_and_compliant_assessment_do_not_emit_drift_event(
    tmp_path: Path,
) -> None:
    app, token = _app(tmp_path)
    with pytest.raises(NotFoundError, match="GitOps state"):
        app.kubernetes_gitops_service.get_latest_state(
            GetLatestKubernetesGitOpsStateCommand("default", token, "missing-cluster")
        )
    with pytest.raises(NotFoundError, match="GitOps state"):
        app.kubernetes_gitops_service.assess(
            AssessKubernetesGitOpsDriftCommand(
                "default",
                token,
                "00000000-0000-0000-0000-000000000000",
                "00000000-0000-0000-0000-000000000000",
            )
        )
    with pytest.raises(NotFoundError, match="GitOps state"):
        app.kubernetes_gitops_service.assess_latest(
            AssessLatestKubernetesGitOpsDriftCommand("default", token, "missing-cluster", "pytest")
        )

    expected = app.kubernetes_gitops_service.import_state(
        ImportKubernetesGitOpsStateCommand(
            "default",
            token,
            "cluster-no-observation",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            datetime(2026, 7, 15, 7, 0, tzinfo=UTC),
            _policy(),
            _expected_resources(),
        )
    )
    assert expected.cluster_key == "cluster-no-observation"
    with pytest.raises(NotFoundError, match="topology snapshot"):
        app.kubernetes_gitops_service.assess_latest(
            AssessLatestKubernetesGitOpsDriftCommand(
                "default", token, "cluster-no-observation", "pytest"
            )
        )

    app2, token2, _, _ = seeded_gitops_application(
        tmp_path / "compliant-state.json", observed_replicas=3
    )
    report = app2.kubernetes_gitops_service.assess_latest(
        AssessLatestKubernetesGitOpsDriftCommand("default", token2, "cluster-par-01", "pytest")
    )
    assert report.status is KubernetesGitOpsComplianceStatus.COMPLIANT
    assert {
        item["name"] for item in app2.store.data["kubernetes_gitops_event_outbox"].values()
    } == {"kubernetes.gitops.state.imported"}
