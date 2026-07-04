# OpenInfra Validation Report — v0.25.2

- Project: OpenInfra
- Version: `0.25.2`
- Date: 2026-07-04
- Type: corrective CI/DevSecOps release
- Base: `v0.25.1` corrective release over `v0.25.0 — P06 / EPIC-0602 Import massif scalable`

## Scope

The release fixes the CI failures reported after v0.25.1 and does not introduce a new roadmap milestone.

## Changes

- Fixed Ruff formatting drift on:
  - `tests/integration/test_import_services.py`
  - `tests/integration/test_postgresql_migration.py`
- Added strict requirements separation:
  - `requirements/runtime.txt` for production core runtime dependencies only.
  - `requirements/postgresql.txt` for optional production PostgreSQL backend dependencies.
  - `requirements/dev.txt` for development, test, CI, security and packaging tools only.
  - `requirements/security-audit.txt` as an explicit pip-audit aggregate referencing the separated files.
- Updated CI installation to install production extras separately from dev tools:
  - `python -m pip install -e '.[postgresql]'`
  - `python -m pip install --requirement requirements/dev.txt`
- Hardened `scripts/security_gate.py` to reject:
  - missing separated requirements files;
  - dev-only packages in production runtime/PostgreSQL requirements;
  - unseparated `requirements/security-audit.txt` contents;
  - accidental local package audit references.
- Added non-regression tests for requirements separation in the security gate.
- Preserved all v0.25.0/v0.25.1 behavior: bulk import, checkpoints, DDI preview, Swagger/ReDoc/OpenAPI discovery, pgAdmin `admin@openinfra.tld`, Docker lab environment and migrations `0001` to `0020`.

## Files changed

- `.github/workflows/ci.yml`
- `.env.example`
- `CHANGELOG.md`
- `README.md`
- `VALIDATION-REPORT.md`
- `VERSION`
- `compose.yaml`
- `docs/TRACEABILITY.md`
- `docs/api/openapi.yaml`
- `docs/architecture/ARCHITECTURE.md`
- `docs/runbooks/RUNTIME_DOCKER.md`
- `docs/runbooks/SECURITY_CI.md`
- `docs/runbooks/VALIDATION.md`
- `pyproject.toml`
- `requirements/runtime.txt`
- `requirements/postgresql.txt`
- `requirements/dev.txt`
- `requirements/security-audit.txt`
- `scripts/docker_environment.py`
- `scripts/quality_gate.py`
- `scripts/security_gate.py`
- `src/openinfra/__init__.py`
- `tests/integration/test_cli.py`
- `tests/integration/test_http_api.py`
- `tests/integration/test_import_services.py`
- `tests/integration/test_postgresql_migration.py`
- `tests/integration/test_runtime_docker_environment.py`
- `tests/integration/test_security_gate.py`

## Validation results

| Command | Result |
| --- | --- |
| `python3 -m ruff format --check src tests scripts docker` | PASS |
| `python3 -m ruff check src tests scripts docker` | PASS |
| `python3 -m mypy src/openinfra` | PASS |
| `python3 -m bandit -q -r src/openinfra` | PASS |
| `python3 scripts/security_gate.py --project-root .` | PASS |
| `python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` | PASS — dry-run, 47 packages |
| `PYTHONPATH=src python3 -m pytest -q` | PASS — 272 tests |
| Coverage gate | PASS — 98.07% |
| `PYTHONPATH=src python3 scripts/quality_gate.py` | PASS — 272 tests, 98.07% |
| `PYTHONPATH=src python3 -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli version` | PASS — 0.25.2 |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — 488 requirements, 310 tests |
| PostgreSQL migration rendering `0001` → `0020` | PASS |
| `compose.yaml` YAML parse | PASS |
| `docs/api/openapi.yaml` YAML parse | PASS |
| `PYTHONPATH=src python3 scripts/native_runtime_smoke.py` | PASS |
| CLI bulk import/report/checkpoint smoke | PASS |
| `python3 -m build` | PASS — wheel and sdist built during validation |
| `python3 scripts/verify_artifact.py dist/openinfra-0.25.2-py3-none-any.whl` | PASS |
| Archive cleanup | PASS — no `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `build`, `dist`, `*.egg-info` |
| Zip integrity | PASS |

## Not executed in this environment

- Docker Compose live boot with PostgreSQL container, because the Docker daemon is not available in this execution environment.
- PostgreSQL live application against a real PostgreSQL server, for the same environment reason.

## User-side Docker commands

```powershell
(Get-Content .env) -replace '^OPENINFRA_IMAGE_TAG=.*$', 'OPENINFRA_IMAGE_TAG=0.25.2' | Set-Content .env

docker compose --env-file .env down --volumes --remove-orphans
python scripts/docker_environment.py init
docker compose --env-file .env up --build -d postgres
docker compose --env-file .env up --build migrate
docker compose --env-file .env up -d auth-bootstrap api pgadmin

docker logs openinfra-api

curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/api/v1
curl http://127.0.0.1:8080/docs
curl http://127.0.0.1:8080/redoc
curl http://127.0.0.1:8080/openapi.yaml
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/ready
curl http://127.0.0.1:8080/api/v1/version
```
