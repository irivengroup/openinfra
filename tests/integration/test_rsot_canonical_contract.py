from __future__ import annotations

import importlib.util
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BuiltinRolePolicy
from openinfra.domain.common import ValidationError
from openinfra.domain.editions import FeatureCapability
from openinfra.domain.security import SecurityRole
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer

LEGACY_RSOT_ALIASES = ("itrm", "ri", "sot")
LEGACY_RSOT_MODULES = (
    "openinfra.application.it_resources_management_services",
    "openinfra.application.it_resources_management_quality_services",
    "openinfra.application.ressources_inventory_quality_services",
)
LEGACY_RSOT_CAPABILITIES = (
    "core_source_of_truth",
    "core_ressources_inventory",
    "core_resources_inventory",
    "core_sot",
    "core_ri",
)


def test_cli_rejects_removed_rsot_aliases() -> None:
    for alias in LEGACY_RSOT_ALIASES:
        with pytest.raises(SystemExit) as exc_info:
            OpenInfraCLI().run([alias, "resource-taxonomy"])
        assert exc_info.value.code == 2


def test_http_api_returns_not_found_for_removed_rsot_aliases(tmp_path: Path) -> None:
    application = ApplicationFactory().create_json_application(tmp_path / "state.json")
    server = OpenInfraThreadingServer(("127.0.0.1", 0), application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        for alias in LEGACY_RSOT_ALIASES:
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(
                    f"{base_url}/api/v1/{alias}/objects",
                    timeout=5,
                )
            assert exc_info.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_rbac_rejects_removed_rsot_roles() -> None:
    policy = BuiltinRolePolicy()
    for alias in LEGACY_RSOT_ALIASES:
        for suffix in ("reader", "operator", "governance-admin"):
            role = SecurityRole.from_value(f"{alias}:{suffix}")
            with pytest.raises(ValidationError, match="unsupported security role"):
                policy.permissions_for((role,))


def test_feature_registry_rejects_removed_rsot_capability_aliases() -> None:
    assert FeatureCapability.from_value("core_rsot") is FeatureCapability.CORE_RSOT
    for removed_member in (
        "CORE_IT_RESOURCES_MANAGEMENT",
        "CORE_RESSOURCES_INVENTORY",
        "CORE_SOURCE_OF_TRUTH",
    ):
        assert not hasattr(FeatureCapability, removed_member)
    for alias in LEGACY_RSOT_CAPABILITIES:
        with pytest.raises(ValidationError, match="unsupported feature capability"):
            FeatureCapability.from_value(alias)


def test_removed_rsot_compatibility_modules_are_absent() -> None:
    for module_name in LEGACY_RSOT_MODULES:
        assert importlib.util.find_spec(module_name) is None
