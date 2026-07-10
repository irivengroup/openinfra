from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.application.discovery_services import (
    DisableDiscoveryIntegrationProfileCommand,
    EnrollDiscoveryProxyCommand,
    GetDiscoveryEvidenceCommand,
    GetDiscoveryReconciliationCommand,
    ListDiscoveryEvidenceCommand,
    ListDiscoveryReconciliationsCommand,
    ReconcileDiscoveryEvidenceCommand,
    ResolveDiscoveryReconciliationCommand,
    SubmitDiscoveryEvidenceCommand,
    UpdateDiscoveryIntegrationProfileCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ConflictError, ValidationError
from openinfra.domain.discovery import DiscoveryEvidence


def _application(tmp_path: Path) -> tuple[OpenInfraApplication, str, Path]:
    state_path = tmp_path / "state.json"
    app = ApplicationFactory().create_json_application(state_path)
    token = "r" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="governance-admin",
            roles=("rsot:governance-admin",),
            token=token,
        )
    )
    return app, token, state_path


def _submit(
    app: OpenInfraApplication,
    token: str,
    *,
    source: str,
    source_ref: str,
    external_id: str,
    cores: int,
    evidence_id: str | None = None,
) -> DiscoveryEvidence:
    return app.discovery_service.submit_evidence(
        SubmitDiscoveryEvidenceCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            object_key="server/srv-app-01",
            object_kind="server",
            source=source,
            source_ref=source_ref,
            scope="site/par1",
            external_id=external_id,
            confidence=0.9,
            payload={"name": "srv-app-01", "cpu": {"cores": cores}},
            observed_at="2026-07-10T12:00:00+00:00",
            evidence_id=evidence_id,
        )
    )


def test_evidence_reconciliation_lifecycle_is_audited_idempotent_and_rsot_safe(
    tmp_path: Path,
) -> None:
    app, token, state_path = _application(tmp_path)
    vmware = _submit(
        app,
        token,
        source="vmware",
        source_ref="vcenter-par1",
        external_id="vm-4201",
        cores=8,
    )
    aws = _submit(
        app,
        token,
        source="aws",
        source_ref="aws-prod-eu-west-3",
        external_id="i-0123456789",
        cores=16,
    )

    listed = app.discovery_service.list_evidence(
        ListDiscoveryEvidenceCommand(
            "default",
            token,
            limit=10,
            object_key="server/srv-app-01",
        )
    )
    assert {item.id.value for item in listed.items} == {vmware.id.value, aws.id.value}
    assert (
        app.discovery_service.get_evidence(
            GetDiscoveryEvidenceCommand("default", token, vmware.id.value)
        ).payload_hash
        == vmware.payload_hash
    )

    command = ReconcileDiscoveryEvidenceCommand(
        tenant_id="default",
        actor="pytest",
        admin_token=token,
        object_key="server/srv-app-01",
        evidence_ids=(vmware.id.value, aws.id.value),
        max_age_seconds=86_400,
    )
    case = app.discovery_service.reconcile_evidence(command)
    repeated = app.discovery_service.reconcile_evidence(command)

    assert repeated.id == case.id
    assert case.status.value == "conflict"
    assert case.rsot_write_executed is False
    assert len(case.conflicts) == 1

    resolved = app.discovery_service.resolve_reconciliation(
        ResolveDiscoveryReconciliationCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            case_id=case.id.value,
            selected_evidence_by_path={"cpu.cores": vmware.id.value},
            justification="VMware is authoritative for this on-premise workload.",
        )
    )
    assert resolved.status.value == "resolved"
    assert resolved.merged_payload["cpu"] == {"cores": 8}
    assert resolved.rsot_write_executed is False
    assert (
        app.discovery_service.get_reconciliation(
            GetDiscoveryReconciliationCommand("default", token, case.id.value)
        ).status.value
        == "resolved"
    )
    assert (
        len(
            app.discovery_service.list_reconciliations(
                ListDiscoveryReconciliationsCommand("default", token, status="resolved")
            ).items
        )
        == 1
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["source_objects"] == {}
    actions = [event["action"] for event in state["audit_events"]]
    assert actions.count("discovery.evidence.submitted") == 2
    assert actions.count("discovery.reconciliation.evaluated") == 1
    assert actions.count("discovery.reconciliation.resolved") == 1
    assert all("payload" not in event["metadata"] for event in state["audit_events"])


def test_evidence_is_immutable_by_identifier(tmp_path: Path) -> None:
    app, token, _ = _application(tmp_path)
    evidence_id = "01111111-2222-4333-8444-555555555555"
    _submit(
        app,
        token,
        source="vmware",
        source_ref="vcenter-par1",
        external_id="vm-4201",
        cores=8,
        evidence_id=evidence_id,
    )

    with pytest.raises(ConflictError, match="immutable"):
        _submit(
            app,
            token,
            source="vmware",
            source_ref="vcenter-par1",
            external_id="vm-4201",
            cores=32,
            evidence_id=evidence_id,
        )


def test_discovery_service_rejects_missing_objects_duplicate_ids_and_invalid_dates(
    tmp_path: Path,
) -> None:
    app, token, _ = _application(tmp_path)

    submitted_without_observed_at = app.discovery_service.submit_evidence(
        SubmitDiscoveryEvidenceCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            object_key="server/service-edge-01",
            object_kind="server",
            source="manual",
            source_ref="operator-console",
            scope="site/par1",
            external_id="service-edge-01",
            confidence=0.8,
            payload={"name": "service-edge-01"},
            observed_at=None,
        )
    )
    assert submitted_without_observed_at.observed_at.tzinfo is not None

    for observed_at, message in (
        ("not-a-date", "ISO-8601"),
        ("2026-07-10T12:00:00", "include a timezone"),
    ):
        with pytest.raises(ValidationError, match=message):
            app.discovery_service.submit_evidence(
                SubmitDiscoveryEvidenceCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=token,
                    object_key="server/service-edge-02",
                    object_kind="server",
                    source="manual",
                    source_ref="operator-console",
                    scope="site/par1",
                    external_id="service-edge-02",
                    confidence=0.8,
                    payload={"name": "service-edge-02"},
                    observed_at=observed_at,
                )
            )

    with pytest.raises(ValidationError, match="evidence is not registered"):
        app.discovery_service.get_evidence(
            GetDiscoveryEvidenceCommand("default", token, "missing-evidence")
        )
    with pytest.raises(ValidationError, match="two distinct evidence ids"):
        app.discovery_service.reconcile_evidence(
            ReconcileDiscoveryEvidenceCommand(
                "default",
                "pytest",
                token,
                "server/service-edge-01",
                (submitted_without_observed_at.id.value,) * 2,
            )
        )
    with pytest.raises(ValidationError, match="missing-evidence"):
        app.discovery_service.reconcile_evidence(
            ReconcileDiscoveryEvidenceCommand(
                "default",
                "pytest",
                token,
                "server/service-edge-01",
                (submitted_without_observed_at.id.value, "missing-evidence"),
            )
        )
    with pytest.raises(ValidationError, match="case is not registered"):
        app.discovery_service.get_reconciliation(
            GetDiscoveryReconciliationCommand("default", token, "missing-case")
        )
    with pytest.raises(ValidationError, match="case is not registered"):
        app.discovery_service.resolve_reconciliation(
            ResolveDiscoveryReconciliationCommand(
                "default",
                "pytest",
                token,
                "missing-case",
                {},
                "Validated operator decision",
            )
        )


def test_discovery_service_rejects_missing_integration_profiles_and_proxy_endpoint(
    tmp_path: Path,
) -> None:
    app, _, _ = _application(tmp_path)
    security_token = "s" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="security-admin",
            roles=("security:admin",),
            token=security_token,
        )
    )

    with pytest.raises(ValidationError, match="integration profile is not registered"):
        app.discovery_service.update_integration_profile(
            UpdateDiscoveryIntegrationProfileCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=security_token,
                profile_id="missing-profile",
                name="Missing profile",
            )
        )
    with pytest.raises(ValidationError, match="integration profile is not registered"):
        app.discovery_service.disable_integration_profile(
            DisableDiscoveryIntegrationProfileCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=security_token,
                profile_id="missing-profile",
                reason="security validation",
            )
        )
    with pytest.raises(ValidationError, match="endpoint URL is mandatory"):
        app.discovery_service.enroll_proxy(
            EnrollDiscoveryProxyCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=security_token,
                name="Proxy PAR1",
                kind="site-proxy",
                certificate_fingerprint="a" * 64,
                scopes=("site/par1",),
                version="0.29.82",
                endpoint_url=" ",
            )
        )
