# OpenInfra Validation Report — v0.23.1

Date: 2026-07-04  
Version: 0.23.1  
Scope: corrective runtime API release after v0.23.0 DDI integration baseline.

## Delivered change

OpenInfra v0.23.1 fixes the operational behavior observed when opening `http://127.0.0.1:8080/` after Docker Compose startup. The API root now returns a deterministic JSON discovery document instead of `{"error": "not_found"}`. The release also improves runtime observability by writing one JSON startup event to stdout so `docker logs openinfra-api` confirms that the API process started, which backend is active and which operational endpoints are available.

No DDI feature delivered in v0.23.0 was removed or changed. pgAdmin4 remains integrated and keeps the default `OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld`. PostgreSQL migration fixes from v0.22.3 are preserved.

## Functional scope

- Added `GET /` discovery response with service name, version, status and links to `/health`, `/ready`, `/api/v1/version` and `/api/v1/database/schema`.
- Added `GET /api/v1` discovery response for the versioned API base path.
- Added JSON startup log event `openinfra_api_started` in `openinfra-api`, emitted on stdout without secrets.
- Updated Docker runtime smoke validation so it checks the new discovery document.
- Removed the stale Docker smoke version comparison against `0.17.6`; the smoke now compares `/api/v1/version` with `openinfra.__version__`.
- Updated OpenAPI, README, architecture notes, runtime runbook, traceability and validation documentation.
- Bumped project version and Docker image defaults to `0.23.1`.

## Files changed

- `VERSION`
- `pyproject.toml`
- `src/openinfra/__init__.py`
- `src/openinfra/interfaces/http_api.py`
- `docker/openinfra-runtime-smoke.py`
- `tests/integration/test_http_api.py`
- `tests/integration/test_runtime_docker_environment.py`
- `tests/integration/test_cli.py`
- `tests/integration/test_ipam_ddi_services.py`
- `.env.example`
- `compose.yaml`
- `scripts/docker_environment.py`
- `scripts/quality_gate.py`
- `README.md`
- `CHANGELOG.md`
- `docs/api/openapi.yaml`
- `docs/architecture/ARCHITECTURE.md`
- `docs/TRACEABILITY.md`
- `docs/runbooks/RUNTIME_DOCKER.md`
- `docs/runbooks/VALIDATION.md`
- `VALIDATION-REPORT.md`
- `SHA256SUMS.txt`

## Regression coverage added

- HTTP integration test validates `GET /` returns `service=openinfra-api`, `version=0.23.1`, `/health`, `/ready` and the API discovery object.
- HTTP integration test validates `GET /api/v1` returns the same API base-path contract.
- Docker runtime asset test validates the smoke script includes `/`, `/api/v1`, `/api/v1/database/schema` and no longer compares the runtime version to `0.17.6`.
- Runtime smoke script validates the discovery document during Docker lab execution.
- Manual runtime smoke confirms `/`, `/api/v1`, `/health` and `/api/v1/version` return HTTP 200 and that stdout contains the `openinfra_api_started` JSON event.

## Validation results executed in this environment

| Validation | Result |
| --- | --- |
| `python3 scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python3 -m pytest -q` | PASS — 223 passed, coverage 98.04% |
| `PYTHONPATH=src python3 scripts/quality_gate.py` | PASS — 223 passed, coverage 98.04% |
| `PYTHONPATH=src python3 -m pytest -q -o addopts='' tests/integration/test_http_api.py tests/integration/test_runtime_docker_environment.py` | PASS — 19 passed |
| `PYTHONPATH=src python3 -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli version` | PASS — `0.23.1` |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — status valid, version 4.0.0, 488 requirements, 310 tests |
| CLI render migrations `0001` → `0018` | PASS — 18 migrations rendered in order |
| Compose YAML parse validation | PASS — `compose.yaml` parsed as a YAML mapping |
| OpenAPI YAML parse validation | PASS — `docs/api/openapi.yaml` parsed as a YAML mapping |
| Native runtime smoke | PASS — systemd/runbook/version assets present |
| HTTP root/API manual smoke | PASS — `/`, `/api/v1`, `/health`, `/api/v1/version` returned HTTP 200 with expected payloads |
| API startup log smoke | PASS — stdout contains `openinfra_api_started` JSON event |
| Artifact verification | PASS — archive contains required OpenInfra source files |
| Zip integrity test | PASS — no compressed-data errors detected |
| Archive cleanup verification | PASS — no `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `build`, `dist`, `*.egg-info`, `.pyc` or `.coverage` entries |

## Requested validations not executable in this environment

| Validation | Local result |
| --- | --- |
| `python3 -m ruff format --check src tests scripts docker` | NOT EXECUTABLE — Python module `ruff` is not installed in this runtime |
| `python3 -m ruff check src tests scripts docker` | NOT EXECUTABLE — Python module `ruff` is not installed in this runtime |
| `python3 -m mypy src/openinfra` | NOT EXECUTABLE — Python module `mypy` is not installed in this runtime |
| `python3 -m bandit -q -r src/openinfra` | NOT EXECUTABLE — Python module `bandit` is not installed in this runtime |
| `python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` | NOT EXECUTABLE — Python module `pip_audit` is not installed in this runtime |
| Real Docker Compose boot | NOT EXECUTABLE — Docker CLI/daemon is not available in this runtime |
| Live PostgreSQL migration apply | NOT EXECUTABLE — PostgreSQL server/client are not available in this runtime; migration rendering and migration-order regression tests passed |

## Environment notes

- Local validation Python runtime: Python 3.13.5.
- CI matrix remains configured for Python 3.11, 3.12, 3.13 and 3.14 in `.github/workflows/ci.yml`.
- Dependency Review remains isolated in `.github/workflows/dependency-review.yml` and runs on pull requests only.
- Production runtime remains native Linux + virtualenv + systemd + PostgreSQL. Docker Compose remains a lab/smoke/test environment only.

## Cleanup status

- Archive generated without `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `build`, `dist` or `*.egg-info`.
- Python bytecode files removed before packaging.
- `.coverage` and temporary CLI smoke data are excluded from the delivered archive.
