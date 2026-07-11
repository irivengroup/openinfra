from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REACT = ROOT / "web/src/main.jsx"
STATIC = ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"


def test_greenops_is_grouped_under_dcim_with_complete_route_parity() -> None:
    operation_ids = (
        "greenops-source-create",
        "greenops-sources",
        "greenops-policy-upsert",
        "greenops-policy-get",
        "greenops-factor-create",
        "greenops-factors",
        "greenops-measurement-ingest",
        "greenops-measurements",
        "greenops-report-generate",
        "greenops-report-get",
        "greenops-reports",
        "greenops-report-export",
        "greenops-anomalies",
        "greenops-forecasts",
        "greenops-candidates",
        "greenops-scores",
    )
    routes = (
        "/v1/greenops/measurement-sources/create",
        "/v1/greenops/measurement-sources",
        "/v1/greenops/policies/upsert",
        "/v1/greenops/policies/get",
        "/v1/greenops/carbon-factors/create",
        "/v1/greenops/carbon-factors",
        "/v1/greenops/energy-measurements/ingest",
        "/v1/greenops/energy-measurements",
        "/v1/greenops/reports/generate",
        "/v1/greenops/reports/get",
        "/v1/greenops/reports",
        "/v1/greenops/reports/export",
        "/v1/greenops/anomalies",
        "/v1/greenops/capacity-forecasts",
        "/v1/greenops/consolidation-candidates",
        "/v1/greenops/green-scores",
    )
    for path in (REACT, STATIC):
        source = path.read_text(encoding="utf-8")
        assert "GreenOps — sources & politiques" in source
        assert "GreenOps — mesures" in source
        assert "GreenOps — rapports & empreinte" in source
        assert "GreenOps — capacité & recommandations" in source
        assert "id: 'greenops'" not in source
        assert 'id: "greenops"' not in source
        for operation_id in operation_ids:
            assert operation_id in source
        for route in routes:
            assert route in source


def test_greenops_temporal_fields_use_native_calendar_controls() -> None:
    for path in (REACT, STATIC):
        source = path.read_text(encoding="utf-8")
        assert "type: 'date'" in source or 'type: "date"' in source
        assert "type: 'datetime-local'" in source or 'type: "datetime-local"' in source
        assert "greenops-report-export" in source
        assert "download: true" in source
