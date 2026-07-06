# OpenInfra v0.29.22 — Validation Report

## Scope

Delivery v0.29.22 hardens `openinfra-web` after v0.29.21:

- add `/status` BFF runtime status without secrets;
- display protected-form status in the dashboard;
- sanitize backend raw `missing bearer token` responses before returning to the browser;
- update CDC v4.8.1 and roadmap v2 traceability.

## Validation results

| Check | Result |
| --- | --- |
| `PYTHONPATH=src python -m compileall -q src scripts tests` | PASS |
| `PYTHONPATH=src python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.22 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 757 requirements, 562 tests |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers` | PASS — 6 profiles |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profiles |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS — 757 requirements |
| `PYTHONPATH=src python -m pytest --collect-only --no-cov` | PASS — 394 tests collected |
| `PYTHONPATH=src python -m pytest ... --cov-append --cov-fail-under=0` | PASS — 394 tests executed in batches |
| `python -m coverage report --fail-under=98` | PASS — 98% |
| `PYTHONPATH=src python scripts/quality_gate.py` | PASS |

## Batch test execution

The complete test suite was executed by batches because a single monolithic `pytest` run timed out in the interactive environment. Coverage data was combined with `coverage append` and then checked globally.

Executed batches:

- `tests/unit` — 149 tests;
- `tests/integration` batch 1 — 50 tests;
- `tests/integration` batch 2 — 69 tests;
- `tests/integration` batch 3 — 67 tests;
- `tests/integration` batch 4 — 56 tests;
- `tests/architecture` — 3 tests.

## Not executed locally

| Check | Reason |
| --- | --- |
| `ruff format --check src tests scripts docker` | `ruff` is not installed in this environment |
| `ruff check src tests scripts docker` | `ruff` is not installed in this environment |
| `mypy src/openinfra` | `mypy` is not installed in this environment |
| `bandit -q -r src/openinfra` | `bandit` is not installed in this environment |
| `pip-audit --dry-run` | `pip-audit` is not installed in this environment |
| `python -m build` | `build` is not installed in this environment |
| `npm run build` | `web/node_modules` is absent |
| Docker Compose live smoke | Docker is unavailable in this environment |
