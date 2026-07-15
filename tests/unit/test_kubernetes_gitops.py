from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.kubernetes_gitops import (
    KubernetesGitOpsComplianceReport,
    KubernetesGitOpsComplianceStatus,
    KubernetesGitOpsDriftKind,
    KubernetesGitOpsPolicy,
    KubernetesGitOpsResource,
    KubernetesGitOpsState,
    KubernetesGitOpsValidator,
)
from openinfra.domain.kubernetes_topology import KubernetesResource, KubernetesTopologySnapshot

COMMIT = "a" * 40


def _policy() -> KubernetesGitOpsPolicy:
    return KubernetesGitOpsPolicy.create(
        required_labels=("app.kubernetes.io/name",),
        required_annotations=("openinfra.io/change-ref",),
        allowed_environments=("production", "staging"),
    )


def _expected_resources() -> tuple[KubernetesGitOpsResource, ...]:
    return (
        KubernetesGitOpsResource.create(
            "namespace",
            "production",
            labels={
                "app.kubernetes.io/name": "production",
                "app.kubernetes.io/owner": "platform",
                "app.kubernetes.io/environment": "production",
            },
            annotations={"openinfra.io/change-ref": "chg-2026-001"},
            owner="platform",
            environment="production",
        ),
        KubernetesGitOpsResource.create(
            "workload",
            "api",
            namespace="production",
            labels={
                "app.kubernetes.io/name": "api",
                "app.kubernetes.io/owner": "payments",
                "app.kubernetes.io/environment": "production",
            },
            annotations={"openinfra.io/change-ref": "chg-2026-001"},
            owner="payments",
            environment="production",
            attributes={"replicas": 3, "strategy": {"type": "RollingUpdate"}},
        ),
    )


def _state() -> KubernetesGitOpsState:
    return KubernetesGitOpsState.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "https://git.example.net/platform/kubernetes.git",
        COMMIT,
        "clusters/prod-par-01",
        "platform",
        "production",
        datetime(2026, 7, 15, 7, 0, tzinfo=UTC),
        _policy(),
        _expected_resources(),
    )


def _observed(*, replicas: int = 3) -> KubernetesTopologySnapshot:
    resources = (
        KubernetesResource.create(
            "namespace",
            "ns-prod",
            "production",
            labels={
                "app.kubernetes.io/name": "production",
                "app.kubernetes.io/owner": "platform",
                "app.kubernetes.io/environment": "production",
            },
            attributes={"annotations": {"openinfra.io/change-ref": "chg-2026-001"}},
        ),
        KubernetesResource.create(
            "workload",
            "deploy-api",
            "api",
            namespace="production",
            labels={
                "app.kubernetes.io/name": "api",
                "app.kubernetes.io/owner": "payments",
                "app.kubernetes.io/environment": "production",
            },
            attributes={
                "annotations": {"openinfra.io/change-ref": "chg-2026-001"},
                "replicas": replicas,
                "strategy": {"type": "RollingUpdate", "rollingUpdate": {"maxSurge": 1}},
            },
        ),
    )
    return KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "discovery:cluster-par-01",
        datetime(2026, 7, 15, 7, 5, tzinfo=UTC),
        resources,
    )


def test_gitops_state_is_deterministic_and_requires_immutable_git_revision() -> None:
    first = _state()
    second = KubernetesGitOpsState.create(
        first.tenant_id,
        first.cluster_key,
        first.repository_ref,
        first.revision,
        first.source_path,
        first.owner,
        first.environment,
        first.captured_at,
        first.policy,
        tuple(reversed(first.resources)),
    )
    assert first.fingerprint == second.fingerprint
    assert first.as_dict()["resource_count"] == 2
    with pytest.raises(ValidationError, match="full 40 or 64 hexadecimal commit digest"):
        KubernetesGitOpsValidator.revision("main")
    with pytest.raises(ValidationError, match="must not embed credentials"):
        KubernetesGitOpsValidator.repository_ref("https://user:password@git.example/repo.git")
    with pytest.raises(ValidationError, match="relative path"):
        KubernetesGitOpsValidator.source_path("/clusters/prod")
    with pytest.raises(ValidationError, match="parent segments"):
        KubernetesGitOpsValidator.source_path("clusters/../prod")


def test_gitops_policy_and_expected_resources_enforce_governance_without_secrets() -> None:
    with pytest.raises(ValidationError, match="sensitive keys"):
        KubernetesGitOpsResource.create(
            "workload",
            "api",
            namespace="production",
            labels={"app.kubernetes.io/name": "api"},
            annotations={"openinfra.io/api-token": "never"},
            owner="payments",
            environment="production",
        )
    with pytest.raises(ValidationError, match="misses required annotation"):
        KubernetesGitOpsState.create(
            TenantId.from_value("default"),
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            datetime.now(UTC),
            _policy(),
            (
                KubernetesGitOpsResource.create(
                    "namespace",
                    "production",
                    labels={"app.kubernetes.io/name": "production"},
                    owner="platform",
                    environment="production",
                ),
            ),
        )
    assert KubernetesGitOpsPolicy.from_dict(_policy().as_dict()).as_dict() == _policy().as_dict()


def test_gitops_compliance_report_is_deterministic_and_detects_attribute_drift() -> None:
    expected = _state()
    observed = _observed(replicas=2)
    first = KubernetesGitOpsComplianceReport.evaluate(
        expected, observed, datetime(2026, 7, 15, 7, 10, tzinfo=UTC)
    )
    second = KubernetesGitOpsComplianceReport.evaluate(
        expected, observed, datetime(2026, 7, 15, 7, 11, tzinfo=UTC)
    )
    assert first.status is KubernetesGitOpsComplianceStatus.DRIFT
    assert first.fingerprint == second.fingerprint
    assert first.as_dict()["automatic_remediation"] is False
    assert any(
        item.kind is KubernetesGitOpsDriftKind.ATTRIBUTE_MISMATCH
        and item.path == "/attributes/replicas"
        for item in first.drifts
    )


def test_gitops_compliance_detects_metadata_owner_environment_missing_and_unexpected() -> None:
    expected = _state()
    observed = KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "discovery:cluster-par-01",
        datetime(2026, 7, 15, 7, 5, tzinfo=UTC),
        (
            KubernetesResource.create(
                "namespace",
                "ns-prod",
                "production",
                labels={"app.kubernetes.io/name": "wrong"},
                attributes={"annotations": {}},
            ),
            KubernetesResource.create(
                "workload",
                "deploy-worker",
                "worker",
                namespace="production",
                labels={"app.kubernetes.io/name": "worker"},
                attributes={"annotations": {}},
            ),
        ),
    )
    report = KubernetesGitOpsComplianceReport.evaluate(expected, observed)
    kinds = {item.kind for item in report.drifts}
    assert KubernetesGitOpsDriftKind.LABEL_MISMATCH in kinds
    assert KubernetesGitOpsDriftKind.MISSING_ANNOTATION in kinds
    assert KubernetesGitOpsDriftKind.MISSING_OWNER in kinds
    assert KubernetesGitOpsDriftKind.MISSING_ENVIRONMENT in kinds
    assert KubernetesGitOpsDriftKind.MISSING_RESOURCE in kinds
    assert KubernetesGitOpsDriftKind.UNEXPECTED_RESOURCE in kinds


def test_gitops_compliance_is_compliant_for_expected_subset_of_observed_attributes() -> None:
    report = KubernetesGitOpsComplianceReport.evaluate(_state(), _observed())
    assert report.status is KubernetesGitOpsComplianceStatus.COMPLIANT
    assert report.drifts == ()
    assert report.summary()["total"] == 0


def test_gitops_compliance_rejects_cross_tenant_and_cross_cluster_comparison() -> None:
    expected = _state()
    observed = _observed()
    other_cluster = KubernetesTopologySnapshot.create(
        observed.tenant_id,
        "cluster-lyo-01",
        observed.cluster_name,
        observed.provider,
        observed.kubernetes_version,
        observed.source_ref,
        observed.observed_at,
        observed.resources,
    )
    with pytest.raises(ValidationError, match="same cluster"):
        KubernetesGitOpsComplianceReport.evaluate(expected, other_cluster)

    other_tenant = KubernetesGitOpsState.create(
        TenantId.from_value("other"),
        expected.cluster_key,
        expected.repository_ref,
        expected.revision,
        expected.source_path,
        expected.owner,
        expected.environment,
        expected.captured_at,
        expected.policy,
        expected.resources,
    )
    with pytest.raises(ValidationError, match="same tenant"):
        KubernetesGitOpsComplianceReport.evaluate(other_tenant, observed)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "1 to 1024 characters"),
        ("https://git.example/repo with-space.git", "whitespace or control"),
        ("ftp://git.example/repo.git", "HTTPS or SSH"),
        ("https:///repo.git", "define a host"),
        ("https://git.example/repo.git?token=abc", "query or fragment"),
    ],
)
def test_gitops_repository_reference_rejects_unsafe_values(value: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        KubernetesGitOpsValidator.repository_ref(value)


def test_gitops_metadata_validators_reject_invalid_and_oversized_payloads() -> None:
    with pytest.raises(ValidationError, match="annotations cannot exceed 64 entries"):
        KubernetesGitOpsValidator.annotations({f"key-{index}": "value" for index in range(65)})
    with pytest.raises(ValidationError, match="invalid Kubernetes annotation key"):
        KubernetesGitOpsValidator.annotations({"invalid key": "value"})
    with pytest.raises(ValidationError, match="exceeds 4096 characters"):
        KubernetesGitOpsValidator.annotations({"openinfra.io/change-ref": "x" * 4097})
    with pytest.raises(ValidationError, match="exceed 32768 bytes"):
        KubernetesGitOpsValidator.annotations(
            {f"openinfra.io/key-{index}": "x" * 600 for index in range(60)}
        )
    with pytest.raises(ValidationError, match="cannot exceed 64 entries"):
        KubernetesGitOpsValidator.metadata_keys(
            tuple(f"key-{index}" for index in range(65)), "required_labels"
        )
    with pytest.raises(ValidationError, match="invalid Kubernetes metadata key"):
        KubernetesGitOpsValidator.metadata_keys(("invalid key",), "required_labels")
    with pytest.raises(ValidationError, match="sensitive keys"):
        KubernetesGitOpsValidator.metadata_keys(("openinfra.io/api-token",), "required_labels")
    assert KubernetesGitOpsValidator.metadata_value("   ", "owner") is None


def test_gitops_policy_and_resource_from_dict_reject_invalid_shapes() -> None:
    with pytest.raises(ValidationError, match="required metadata policies must be JSON arrays"):
        KubernetesGitOpsPolicy.from_dict({"required_labels": "not-a-list"})
    with pytest.raises(ValidationError, match="allowed_environments must be a JSON array"):
        KubernetesGitOpsPolicy.from_dict({"allowed_environments": "production"})
    with pytest.raises(ValidationError, match="must not define namespace"):
        KubernetesGitOpsResource.create("namespace", "production", namespace="production")
    with pytest.raises(ValidationError, match="requires a namespace"):
        KubernetesGitOpsResource.create("workload", "api")
    with pytest.raises(ValidationError, match="labels and annotations must be JSON objects"):
        KubernetesGitOpsResource.from_dict(
            {"kind": "namespace", "name": "prod", "labels": ["invalid"]}
        )
    with pytest.raises(ValidationError, match="attributes must be a JSON object"):
        KubernetesGitOpsResource.from_dict(
            {"kind": "namespace", "name": "prod", "attributes": ["invalid"]}
        )


def test_gitops_state_rejects_invalid_policy_resource_sets_and_fingerprint() -> None:
    tenant = TenantId.from_value("default")
    now = datetime(2026, 7, 15, 7, 0, tzinfo=UTC)
    base = KubernetesGitOpsResource.create(
        "namespace",
        "production",
        labels={"app.kubernetes.io/name": "production"},
        owner="platform",
        environment="production",
    )
    permissive = KubernetesGitOpsPolicy.create(require_owner=False, require_environment=False)
    with pytest.raises(ValidationError, match="at least one expected resource"):
        KubernetesGitOpsState.create(
            tenant,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            now,
            permissive,
            (),
        )
    original_limit = KubernetesGitOpsState._MAX_RESOURCES
    KubernetesGitOpsState._MAX_RESOURCES = 1
    try:
        with pytest.raises(ValidationError, match="cannot exceed 1 expected resources"):
            KubernetesGitOpsState.create(
                tenant,
                "cluster-par-01",
                "https://git.example/repo.git",
                COMMIT,
                "clusters/prod",
                "platform",
                "production",
                now,
                permissive,
                (base, KubernetesGitOpsResource.create("node", "worker-01")),
            )
    finally:
        KubernetesGitOpsState._MAX_RESOURCES = original_limit
    with pytest.raises(ValidationError, match="duplicate GitOps resource identity"):
        KubernetesGitOpsState.create(
            tenant,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            now,
            permissive,
            (base, base),
        )
    required_label_policy = KubernetesGitOpsPolicy.create(
        required_labels=("app.kubernetes.io/managed-by",),
        require_owner=False,
        require_environment=False,
    )
    with pytest.raises(ValidationError, match="misses required label"):
        KubernetesGitOpsState.create(
            tenant,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            now,
            required_label_policy,
            (base,),
        )
    owner_required = KubernetesGitOpsPolicy.create(require_owner=True, require_environment=False)
    no_owner = KubernetesGitOpsResource.create("namespace", "production")
    with pytest.raises(ValidationError, match="requires an owner"):
        KubernetesGitOpsState.create(
            tenant,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            now,
            owner_required,
            (no_owner,),
        )
    environment_required = KubernetesGitOpsPolicy.create(
        require_owner=False, require_environment=True
    )
    with pytest.raises(ValidationError, match="requires an environment"):
        KubernetesGitOpsState.create(
            tenant,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            now,
            environment_required,
            (no_owner,),
        )
    allowed = KubernetesGitOpsPolicy.create(
        allowed_environments=("production",), require_owner=False, require_environment=False
    )
    staging = KubernetesGitOpsResource.create("namespace", "production", environment="staging")
    with pytest.raises(ValidationError, match="uses a disallowed environment"):
        KubernetesGitOpsState.create(
            tenant,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "production",
            now,
            allowed,
            (staging,),
        )
    with pytest.raises(ValidationError, match="state environment is not allowed"):
        KubernetesGitOpsState.create(
            tenant,
            "cluster-par-01",
            "https://git.example/repo.git",
            COMMIT,
            "clusters/prod",
            "platform",
            "staging",
            now,
            allowed,
            (base,),
        )
    state = _state()
    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        KubernetesGitOpsState.restore(
            state.id,
            state.tenant_id,
            state.cluster_key,
            state.repository_ref,
            state.revision,
            state.source_path,
            state.owner,
            state.environment,
            state.captured_at,
            state.imported_at,
            state.policy,
            state.resources,
            "0" * 64,
        )


def test_gitops_compliance_covers_governance_and_nested_attribute_drift_variants() -> None:
    expected = _state()
    observed = KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "discovery:cluster-par-01",
        datetime(2026, 7, 15, 7, 5, tzinfo=UTC),
        (
            KubernetesResource.create(
                "namespace",
                "ns-prod",
                "production",
                labels={
                    "app.kubernetes.io/name": "production",
                    "app.kubernetes.io/owner": "other-team",
                    "app.kubernetes.io/environment": "qa",
                },
                attributes={"annotations": "invalid-shape"},
            ),
            KubernetesResource.create(
                "workload",
                "deploy-api",
                "api",
                namespace="production",
                labels={"app.kubernetes.io/name": "api"},
                attributes={
                    "annotations": {
                        "openinfra.io/change-ref": "wrong",
                        "openinfra.io/owner": "payments",
                        "openinfra.io/environment": "production",
                    },
                    "strategy": "Recreate",
                },
            ),
        ),
    )
    report = KubernetesGitOpsComplianceReport.evaluate(expected, observed)
    kinds = {item.kind for item in report.drifts}
    assert KubernetesGitOpsDriftKind.ANNOTATION_MISMATCH in kinds
    assert KubernetesGitOpsDriftKind.OWNER_MISMATCH in kinds
    assert KubernetesGitOpsDriftKind.ENVIRONMENT_MISMATCH in kinds
    assert KubernetesGitOpsDriftKind.ENVIRONMENT_NOT_ALLOWED in kinds
    assert KubernetesGitOpsDriftKind.MISSING_ATTRIBUTE in kinds
    assert KubernetesGitOpsDriftKind.ATTRIBUTE_MISMATCH in kinds
    assert report.summary()["total"] == len(report.drifts)
    assert report.as_dict()["automatic_remediation"] is False
