# OpenInfra v0.29.35 validation report

## Scope

OpenInfra v0.29.35 delivers Discovery Enterprise proxy enrollment config verification and a focused openinfra-web dashboard UX correction.

## Functional changes

- Added `openinfra discovery proxy-enroll-verify` to validate generated Enterprise proxy enrollment config files locally.
- Enforced Enterprise-only verification gate for proxy enrollment configs.
- Validated enrollment JSON schema, backend URLs, HTTP status codes, backend JSON responses, global enrolled flag and POSIX file permissions.
- Added `--allow-partial` to report partial HA backend enrollment as warning while preserving schema errors.
- Fixed CLI debt: `openinfra discovery job-authorize` returns a single JSON document.
- Changed openinfra-web home title from the long product title to `Dashboard`.
- Scoped home metrics and component statistics strictly to the Dashboard page; component pages render only their contextual title, form and result.

## Tests and quality gates

| Validation | Result |
| --- | --- |
| `ruff format --check src tests scripts docker` | PASS |
| `ruff check src tests scripts docker` | PASS |
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.35 |
| `mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `pip-audit --dry-run` | PASS |
| CDC `validate_docs.py` | PASS — 774 requirements, 519 entities |
| CDC `validate_storage_multisite.py` | PASS — 774 requirements |
| Roadmap `validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 47 tests |
| `validate_enterprise_alignment.py` | PASS |
| `validate_autonomous_installer.py` | PASS — 6 profiles |
| `native_runtime_smoke.py` | PASS |
| Installer validate/dry-run | PASS — 6 profiles |
| `pytest --collect-only --no-cov` | PASS — 436 tests collected |
| pytest batches with cumulative coverage | PASS — all collected test files executed |
| `coverage report --fail-under=98` | PASS — 98.01072865444792 % |
| `quality_gate.py` | PASS |
| `python -m build` | PASS |
| `verify_artifact.py` | PASS |
| ZIP integrity | PASS |
| Archive cleanup | PASS |

## Not executed locally

- `npm run build`: `web/node_modules` is absent in the execution environment.
- Docker Compose live: Docker CLI is absent in the execution environment.
