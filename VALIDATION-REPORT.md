# OpenInfra 0.29.60 — Ruff hotfix validation report

## Scope

This hotfix repackages OpenInfra 0.29.60 after applying Ruff formatting and lint corrections reported by CI. No functional behavior, public CLI/API contract, CDC requirement or roadmap milestone was changed.

## Files changed by hotfix

- src/openinfra/application/external_itsm_services.py
- src/openinfra/application/import_services.py
- src/openinfra/application/search_services.py
- src/openinfra/domain/data_import.py
- src/openinfra/domain/external_itsm.py
- src/openinfra/interfaces/cli.py
- src/openinfra/interfaces/http_api.py
- src/openinfra/interfaces/web.py
- tests/integration/test_external_itsm_integrations.py
- tests/integration/test_http_api.py
- tests/integration/test_import_services.py
- tests/integration/test_openinfra_web.py
- tests/integration/test_postgresql_migration.py
- tests/unit/test_data_import_domain.py
- tests/unit/test_external_itsm_domain.py

## Validations executed

| Command | Status |
| --- | --- |
| `python -m ruff format --check src tests scripts docker` | PASS — 133 files already formatted |
| `python -m ruff check src tests scripts docker` | PASS |
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.60 |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 installers |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m pytest --collect-only --no-cov` | PASS — 493 tests collected |
| `PYTHONPATH=src python -m pytest -o addopts='' -q tests/architecture tests/unit` | PASS — 196 tests |
| integration test batches | PASS — 297 tests |
| aggregated coverage by deterministic batches | PASS — 98 % |
| `python scripts/quality_gate.py` | PASS |
| archive cleanup | PASS |
| `zip -T openinfra-python-0.29.60.zip` | PASS |
| `python scripts/verify_artifact.py openinfra-python-0.29.60.zip` | PASS |

## Notes

The monolithic `PYTHONPATH=src python -m pytest` command exceeded the local execution limit before completion. The complete suite was therefore executed by deterministic batches and coverage data was combined with `coverage combine`.

## Not executed locally

- `mypy`
- `bandit`
- `pip-audit`
- `python -m build`
- Vite production build
- Docker Compose live runtime
