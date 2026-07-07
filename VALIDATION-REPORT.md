# OpenInfra v0.29.29 — validation report

Date: 2026-07-07

## Scope

OpenInfra v0.29.29 delivers P10/DCIM energy and cooling dashboard parity and ITRM taxonomy UX hardening:

- DCIM dashboard operations for power devices, power circuits, cooling zones, power reservations and rack energy/cooling capacity.
- API discovery and OpenAPI documentation for existing DCIM energy/cooling backend contracts.
- ITRM category/type select fields display human-readable labels while keeping normalized internal values in submitted payloads.
- Obsolete generic resource types `physical-server` and `disk` removed from the taxonomy; server default is now `rack-server`.

## Validation results

| Validation | Result |
| --- | --- |
| `ruff format --check src tests scripts docker` | PASS |
| `ruff check src tests scripts docker` | PASS |
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python -m openinfra.interfaces.cli version` | PASS — 0.29.29 |
| `mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `pip-audit --dry-run` | PASS |
| `python -m build` | PASS |
| `python scripts/verify_artifact.py dist/openinfra-0.29.29-py3-none-any.whl` | PASS |
| CDC `validate_docs.py` | PASS — 767 requirements, 519 entities |
| CDC `validate_storage_multisite.py` | PASS — 767 requirements |
| Roadmap `validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 40 tests |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profiles |
| `python scripts/native_runtime_smoke.py` | PASS |
| installer validate | PASS — 6 profiles |
| installer dry-run | PASS — 6 profiles |
| `pytest --collect-only --no-cov` | PASS — 407 tests collected |
| pytest by batches with combined coverage | PASS — 407 tests executed |
| `coverage report --fail-under=98` | PASS — 98.0096 % |
| `python scripts/quality_gate.py` | PASS |
| `zip -T` on generated archives | PASS |
| archive cleanup inspection | PASS |

The single full `pytest` command with coverage exceeded the interactive timeout, so the complete suite was executed in four deterministic batches with `coverage --append`, followed by the final global `coverage report --fail-under=98` gate.

## Not executed locally

- `npm run build`: `web/node_modules` is not present in the execution environment.
- Docker Compose live runtime: Docker is not available in the execution environment.
