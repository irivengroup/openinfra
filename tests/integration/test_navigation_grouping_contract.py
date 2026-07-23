from __future__ import annotations

from pathlib import Path

from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL

ROOT = Path(__file__).resolve().parents[2]
RUNTIMES = (REACT_PORTAL, RUNTIME_PORTAL)


def test_network_flows_and_compliance_are_grouped_under_ipam() -> None:
    operation_ids = (
        "flow-declaration-upsert",
        "flow-declaration-list",
        "flow-declaration-retire",
        "flow-observation-submit",
        "flow-observation-list",
        "flow-matrix",
        "network-config-baseline-upsert",
        "network-config-baseline-list",
        "network-config-baseline-retire",
        "network-config-observation-submit",
        "network-config-observation-list",
        "network-config-assessment",
    )
    for path in RUNTIMES:
        source = path.read_text(encoding="utf-8")
        assert "Conformité réseau" in source
        assert "Flux déclarés" in source
        assert "Flux observés" in source
        assert "Conformité des flux" in source
        assert "id: 'flows'" not in source
        assert 'id: "flows"' not in source
        assert "id: 'network-config'" not in source
        assert 'id: "network-config"' not in source
        for operation_id in operation_ids:
            assert operation_id in source


def test_certificates_are_grouped_under_security_without_top_level_component() -> None:
    for path in RUNTIMES:
        source = path.read_text(encoding="utf-8")
        assert "Inventaire PKI" in source
        assert "Endpoints TLS" in source
        assert "Conformité PKI" in source
        assert "id: 'certificates'" not in source
        assert 'id: "certificates"' not in source
        assert "certificate-assessment" in source
