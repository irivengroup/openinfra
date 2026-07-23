from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL

SOURCES = (REACT_PORTAL, RUNTIME_PORTAL)


def test_kubernetes_topology_is_exposed_under_discovery_with_route_parity() -> None:
    operations = (
        "kubernetes-topologies-list",
        "kubernetes-topology-latest",
        "kubernetes-topology-graph",
        "kubernetes-topology-import",
    )
    routes = (
        "/v1/kubernetes/topologies",
        "/v1/kubernetes/topologies/latest",
        "/v1/kubernetes/topologies/latest-topology",
        "/v1/kubernetes/topologies/import",
    )
    for source_path in SOURCES:
        source = source_path.read_text(encoding="utf-8")
        for operation in operations:
            assert operation in source
        for route in routes:
            assert route in source
        assert 'id: "kubernetes"' not in source
        assert "id: 'kubernetes'" not in source


def test_kubernetes_import_uses_typed_json_and_datetime_controls() -> None:
    for source_path in SOURCES:
        source = source_path.read_text(encoding="utf-8")
        assert '"name": "resources"' in source
        assert '"type": "json"' in source
        assert '"name": "observed_at"' in source
        assert '"format": "date-time"' in source
