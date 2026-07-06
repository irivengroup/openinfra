# OpenInfra v0.29.21 — Validation Report

## Scope

- UI: dashboard titlebar vertical spacing, responsive CSS retained in React source and runtime asset.
- Web BFF: authenticated form proxy no longer propagates a raw backend `missing bearer token` error to the browser.
- Runtime auth: `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` blank values fall back to `OPENINFRA_BOOTSTRAP_TOKEN` server-side.
- Quality: Ruff format/check regression fixed for `tests/integration/test_http_api.py` and all impacted files.

## Passed validations

| Validation | Result |
|---|---:|
| `python -m compileall -q src tests scripts docker` | PASS |
| `ruff format --check src tests scripts docker` | PASS |
| `ruff check src tests scripts docker` | PASS |
| `mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python -m openinfra version` | PASS — 0.29.21 |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS — 756 requirements, 519 entities |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS — 756 requirements |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 31 tests |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profiles |
| `python scripts/native_runtime_smoke.py` | PASS |
| targeted web/API regression tests | PASS — 33 tests |
| full pytest by batches with combined coverage | PASS — 393 tests, 98% coverage |
| `python scripts/quality_gate.py` | PASS |
| `python -m build` | PASS |
| `python scripts/verify_artifact.py dist/openinfra-0.29.21-py3-none-any.whl` | PASS |

## Not executed locally

| Validation | Reason |
|---|---|
| `pip-audit -r requirements/runtime.txt` | Failed due environment DNS/network unavailability while querying PyPI vulnerability metadata. |
| `npm run build` | `web/node_modules` absent in the execution environment. Runtime JS syntax was still checked with `node --check`. |
| Docker Compose live runtime | Docker daemon unavailable in the execution environment. |

## Notes

The single CI failure reported by the user, `ruff format --check src tests scripts docker`, has been corrected and revalidated. The final archive excludes caches, coverage files, build outputs and temporary artifacts.
