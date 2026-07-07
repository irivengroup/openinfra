# OpenInfra v0.29.44 — Validation report

## Scope

Release v0.29.44 consolidates two increments:

- ITAM support coverage report per physical asset, exposed through domain/service/API/CLI/OpenAPI.
- UX regression fix for the web sidebar accordion: expanded component menus remain in normal vertical flow, push lower components down, remove the fixed `34rem` panel cap, and keep the sidebar independently scrollable under the fixed header.

## Changed areas

- `src/openinfra/domain/itam.py`
- `src/openinfra/application/itam_services.py`
- `src/openinfra/interfaces/http_api.py`
- `src/openinfra/interfaces/cli.py`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`
- `web/src/openinfra-theme.css`
- `scripts/validate_frontend.py`
- `tests/integration/test_openinfra_web.py`
- `tests/integration/test_runtime_docker_environment.py`
- `scripts/docker_environment.py`
- `README.md`, `CHANGELOG.md`, `docs/ui/OPENINFRA_WEB.md`, `docs/architecture/ARCHITECTURE.md`
- CDC v4.8.1 and Roadmap v2 matrices

## Validation commands executed

| Validation | Result |
| --- | --- |
| `python -m compileall -q src tests scripts` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.44` |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py` | PASS — 6 profiles |
| `PYTHONPATH=src python scripts/security_gate.py` | PASS |
| `PYTHONPATH=src:. pytest --collect-only --no-cov` | PASS — 447 tests collected |
| `PYTHONPATH=src:. pytest tests/unit --no-cov -q` | PASS — 174 tests |
| Integration/architecture pytest batches with `--no-cov` | PASS — 273 tests |
| Coverage aggregation in batches with `--cov-append` | PASS |
| `coverage report --fail-under=98` | PASS — 98% |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |

## Targeted regression checks

- `tests/integration/test_openinfra_web.py` verifies that `.openinfra-accordion-panel.show` uses `max-height: none` and `overflow: visible`.
- The frontend validator rejects the old sidebar cap `max-height: 34rem` and `transition: max-height`.
- The CSS keeps `.openinfra-sidebar` as the scroll container with `overflow-y: auto`, `overflow-x: hidden`, `overscroll-behavior: contain`, and `scrollbar-gutter: stable`.
- Runtime Docker image tag tests were realigned to `0.29.44` to avoid stale test expectations.

## Not executable in this environment

- `ruff`, `mypy`, `bandit`, `pip-audit`: command binaries unavailable.
- `python -m build`: module `build` unavailable.
- `npm run build`: `web/node_modules` / `vite` unavailable.
- Docker Compose live execution: Docker unavailable.

## Packaging checks

- Caches and temporary artifacts removed before final archive.
- Archive integrity checked with `zip -T`.
- Artifact content checked with `scripts/verify_artifact.py`.
