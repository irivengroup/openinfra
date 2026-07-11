from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.multisite_services import (
    ConfigureDisasterRecoveryPlanCommand,
    DisableDisasterRecoveryPlanCommand,
    ExecuteDisasterRecoveryDrillCommand,
    GetDisasterRecoveryDrillCommand,
    GetDisasterRecoveryPlanCommand,
    ListDisasterRecoveryDrillsCommand,
    ListDisasterRecoveryPlansCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import EntityId, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import Site


def _application(tmp_path: Path, edition: str = "pro"):
    state = tmp_path / f"dr-{edition}.json"
    app = ApplicationFactory().create_json_application(state, seed=True, edition=edition)
    token = "d" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "dr-admin", ("admin",), token)
    )
    with app.transaction_manager.begin() as unit_of_work:
        app.dcim_repository.add_site(
            Site.create(
                TenantId.from_value("default"),
                "LON1",
                "London 1",
                "GB",
                "London",
                "England",
                "1 Datacenter Way",
                "E1 1AA",
                "lon1@example.invalid",
                "+442000000001",
            )
        )
        unit_of_work.commit()
    return state, app, token


def _configure(app: object, token: str):
    return app.multisite_service.configure_disaster_recovery_plan(  # type: ignore[attr-defined]
        ConfigureDisasterRecoveryPlanCommand(
            "default",
            token,
            "Paris to London",
            "PAR1",
            "LON1",
            "asynchronous",
            300,
            1800,
            86400,
            "pytest",
        )
    )


def test_dr_plan_drills_persistence_audit_and_filters(tmp_path: Path) -> None:
    state, app, token = _application(tmp_path)
    plan = _configure(app, token)
    revised = app.multisite_service.configure_disaster_recovery_plan(
        ConfigureDisasterRecoveryPlanCommand(
            "default", token, "Critical Paris to London", "PAR1", "LON1", "sync", 60, 600, 3600
        )
    )
    assert revised.id == plan.id and revised.rpo_seconds == 60
    assert (
        app.multisite_service.get_disaster_recovery_plan(
            GetDisasterRecoveryPlanCommand("default", token, plan.id.value)
        )
        == revised
    )
    assert app.multisite_service.list_disaster_recovery_plans(
        ListDisasterRecoveryPlansCommand("default", token)
    ).items == (revised,)

    passed = app.multisite_service.execute_disaster_recovery_drill(
        ExecuteDisasterRecoveryDrillCommand(
            "default", token, plan.id.value, 30, 1800, 300, True, True, True, True, "pytest"
        )
    )
    failed = app.multisite_service.execute_disaster_recovery_drill(
        ExecuteDisasterRecoveryDrillCommand(
            "default", token, plan.id.value, 61, 3601, 601, False, False, False, False, "pytest"
        )
    )
    assert passed.status.value == "passed"
    assert failed.status.value == "failed"
    with pytest.raises(ValidationError, match="immutable"):
        app.multisite_repository.save_dr_drill(replace(passed, executed_by="tampered"))
    assert (
        app.multisite_service.get_disaster_recovery_drill(
            GetDisasterRecoveryDrillCommand("default", token, passed.id.value)
        )
        == passed
    )
    failed_page = app.multisite_service.list_disaster_recovery_drills(
        ListDisasterRecoveryDrillsCommand("default", token, plan_id=plan.id.value, status="failed")
    )
    assert failed_page.items == (failed,)
    with pytest.raises(ValidationError, match="passed or failed"):
        app.multisite_service.list_disaster_recovery_drills(
            ListDisasterRecoveryDrillsCommand("default", token, status="unknown")
        )

    reopened = ApplicationFactory().create_json_application(state, seed=False, edition="pro")
    assert (
        reopened.multisite_repository.get_dr_plan(TenantId.from_value("default"), plan.id.value)
        is not None
    )
    assert (
        reopened.multisite_repository.get_dr_drill(TenantId.from_value("default"), passed.id.value)
        == passed
    )
    actions = {event["action"] for event in reopened.store.data["audit_events"]}
    assert "multisite.dr_plan.configured" in actions
    assert "multisite.dr_drill.executed" in actions
    drill_audit = next(
        event
        for event in reopened.store.data["audit_events"]
        if event["action"] == "multisite.dr_drill.executed"
    )
    assert drill_audit["metadata"]["automatic_promotion"] is False

    disabled = app.multisite_service.disable_disaster_recovery_plan(
        DisableDisasterRecoveryPlanCommand("default", token, plan.id.value, "pytest")
    )
    assert disabled.active is False
    assert (
        app.multisite_service.list_disaster_recovery_plans(
            ListDisasterRecoveryPlansCommand("default", token)
        ).items
        == ()
    )
    assert app.multisite_service.list_disaster_recovery_plans(
        ListDisasterRecoveryPlansCommand("default", token, active_only=False)
    ).items == (disabled,)
    with pytest.raises(ValidationError, match="active plan"):
        app.multisite_service.execute_disaster_recovery_drill(
            ExecuteDisasterRecoveryDrillCommand(
                "default", token, plan.id.value, 0, 0, 0, True, True, True, True
            )
        )


def test_dr_service_guards_sites_ids_and_edition(tmp_path: Path) -> None:
    _state, app, token = _application(tmp_path / "pro")
    with pytest.raises(NotFoundError, match="primary"):
        app.multisite_service.configure_disaster_recovery_plan(
            ConfigureDisasterRecoveryPlanCommand(
                "default", token, "Unknown primary", "MAD1", "LON1", "async", 300, 1800, 86400
            )
        )
    with pytest.raises(NotFoundError, match="recovery"):
        app.multisite_service.configure_disaster_recovery_plan(
            ConfigureDisasterRecoveryPlanCommand(
                "default", token, "Unknown recovery", "PAR1", "MAD1", "async", 300, 1800, 86400
            )
        )
    unknown = EntityId.new().value
    with pytest.raises(NotFoundError, match="DR plan"):
        app.multisite_service.get_disaster_recovery_plan(
            GetDisasterRecoveryPlanCommand("default", token, unknown)
        )
    with pytest.raises(NotFoundError, match="DR plan"):
        app.multisite_service.disable_disaster_recovery_plan(
            DisableDisasterRecoveryPlanCommand("default", token, unknown)
        )
    with pytest.raises(NotFoundError, match="DR drill"):
        app.multisite_service.get_disaster_recovery_drill(
            GetDisasterRecoveryDrillCommand("default", token, unknown)
        )

    plan = _configure(app, token)
    app.dcim_repository._store.data["sites"].pop("default:PAR1")
    with pytest.raises(NotFoundError, match="primary DCIM site"):
        app.multisite_service.execute_disaster_recovery_drill(
            ExecuteDisasterRecoveryDrillCommand(
                "default", token, plan.id.value, 0, 0, 0, True, True, True, True
            )
        )
    app.dcim_repository.add_site(
        Site.create(
            TenantId.from_value("default"),
            "PAR1",
            "Paris 1",
            "FR",
            "Paris",
            "Île-de-France",
            "1 Datacenter Way",
            "75001",
            "par1@example.invalid",
            "+33100000001",
        )
    )
    app.dcim_repository._store.data["sites"].pop("default:LON1")
    with pytest.raises(NotFoundError, match="recovery DCIM site"):
        app.multisite_service.execute_disaster_recovery_drill(
            ExecuteDisasterRecoveryDrillCommand(
                "default", token, plan.id.value, 0, 0, 0, True, True, True, True
            )
        )

    lite_state, lite, lite_token = _application(tmp_path / "lite", "lite")
    assert lite_state.exists()
    with pytest.raises(ValidationError, match="multisite_disaster_recovery"):
        lite.multisite_service.list_disaster_recovery_plans(
            ListDisasterRecoveryPlansCommand("default", lite_token)
        )
