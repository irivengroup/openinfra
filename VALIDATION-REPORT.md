# OpenInfra v0.29.30 — validation report

## Scope

OpenInfra v0.29.30 delivers the initial P10/DCIM room digital twin:

- `GET /api/v1/dcim/digital-twin` HTTP API contract.
- `openinfra dcim digital-twin` CLI command.
- `Jumeau numérique salle` dashboard operation.
- Consolidated `dcim_digital_twin` payload containing `summary`, `room_plan`, `racks`, `floor_equipment`, `cables` and `integrity`.
- Rack-level aggregation of equipment, patch panels, ports, cables, power circuits, power reservations, energy/cooling capacity and rack elevations.
- No parallel storage: existing DCIM repositories and services remain the source of truth.

## Validation results

| Validation | Result |
| --- | --- |
| `ruff format --check src tests scripts docker` | PASS |
| `ruff check src tests scripts docker` | PASS |
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.30 |
| `PYTHONPATH=src mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `pip-audit --dry-run` | PASS — no known vulnerabilities found |
| CDC `validate_docs.py` | PASS — 768 requirements, 519 entities |
| CDC `validate_storage_multisite.py` | PASS — 768 requirements |
| Roadmap `validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 41 tests |
| `validate_enterprise_alignment.py` | PASS |
| `validate_autonomous_installer.py` | PASS — 6 installers |
| `native_runtime_smoke.py` | PASS |
| installer dry-run/verify-only | PASS — 6 profiles |
| `pytest --collect-only --no-cov` | PASS — 409 tests collected |
| pytest batches with coverage append | PASS — 409 tests executed |
| `coverage report --fail-under=98` | PASS — 98.0006% exact, displayed 98% |
| `python scripts/quality_gate.py` | PASS |
| `python -m build` | PASS |
| `python scripts/verify_artifact.py dist/openinfra-0.29.30-py3-none-any.whl` | PASS |

## Not executed locally

| Validation | Reason |
| --- | --- |
| `npm run build` | `web/node_modules` absent in the execution environment |
| Docker Compose live runtime | `docker` command absent in the execution environment |

## Notes

The single-process full pytest run exceeded the interactive environment timeout. The complete suite was therefore executed by deterministic file batches with coverage append, then validated by the final `coverage report --fail-under=98` gate.
