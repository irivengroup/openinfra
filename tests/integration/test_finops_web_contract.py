from __future__ import annotations

from pathlib import Path

from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL
from tests.runtime_i18n_contract import assert_runtime_i18n_contract

ROOT = Path(__file__).resolve().parents[2]
REACT = REACT_PORTAL
STATIC = RUNTIME_PORTAL
SOURCE_I18N = ROOT / "web/src/i18n.js"
RUNTIME_I18N = ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js"


def test_finops_is_grouped_under_itam_with_complete_route_parity() -> None:
    operation_ids = (
        "finops-rule-create",
        "finops-rules",
        "finops-import-submit",
        "finops-import-get",
        "finops-imports",
        "finops-import-run",
        "finops-import-cancel",
        "finops-costs",
        "finops-budget-upsert",
        "finops-budgets",
        "finops-period-close",
        "finops-periods",
        "finops-report-generate",
        "finops-report-get",
        "finops-reports",
        "finops-report-export",
        "finops-anomalies",
        "finops-forecasts",
    )
    routes = (
        "/v1/finops/allocation-rules/create",
        "/v1/finops/allocation-rules",
        "/v1/finops/import-jobs/submit",
        "/v1/finops/import-jobs/get",
        "/v1/finops/import-jobs",
        "/v1/finops/import-jobs/run",
        "/v1/finops/import-jobs/cancel",
        "/v1/finops/cost-records",
        "/v1/finops/budgets/upsert",
        "/v1/finops/budgets",
        "/v1/finops/periods/close",
        "/v1/finops/periods",
        "/v1/finops/reports/generate",
        "/v1/finops/reports/get",
        "/v1/finops/reports",
        "/v1/finops/reports/export",
        "/v1/finops/anomalies",
        "/v1/finops/forecasts",
    )
    for path in (REACT, STATIC):
        source = path.read_text(encoding="utf-8")
        assert "Règles d\u2019allocation" in source
        assert "Imports & coûts" in source
        assert "Budgets & périodes" in source
        assert "Showback / chargeback" in source
        assert "Prévisions & anomalies" in source
        assert "id: 'finops'" not in source
        assert 'id: "finops"' not in source
        for operation_id in operation_ids:
            assert operation_id in source
        for route in routes:
            assert route in source


def test_finops_dates_use_calendars_and_runtime_i18n_is_generated() -> None:
    react = REACT.read_text(encoding="utf-8")
    static = STATIC.read_text(encoding="utf-8")
    for source in (react, static):
        assert source.count('"name": "period_start"') >= 3
        assert source.count('"type": "date"') >= 6
    source_i18n = SOURCE_I18N.read_text(encoding="utf-8")
    assert_runtime_i18n_contract(
        "Network compliance",
        "Allocation rules",
        "Imports & costs",
        "Budgets & periods",
        "Forecasts & anomalies",
        "Generate showback or chargeback",
    )
    for text in (
        "Network compliance",
        "Allocation rules",
        "Imports & costs",
        "Budgets & periods",
        "Forecasts & anomalies",
        "Generate showback or chargeback",
    ):
        assert text in source_i18n
