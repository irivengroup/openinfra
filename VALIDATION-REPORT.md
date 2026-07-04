# OpenInfra Validation Report — v0.23.0

Date: 2026-07-04  
Version: 0.23.0  
Scope: P05 / EPIC-0506 — DDI integration baseline after v0.22.3 Docker/PostgreSQL corrective release.

## Delivered change

OpenInfra v0.23.0 introduces a deterministic DDI preview baseline connected to existing IPAM reservations. The release does not apply changes to external DNS or DHCP systems; it computes auditable dry-run plans, detects known divergences from observed data and emits rollback-compensating operations for later orchestration.

### Functional scope

- Added DDI domain objects for providers, record kinds, DNS/DHCP changes, divergences and reservation preview reports.
- Added baseline DDI connectors for BIND, PowerDNS and Kea.
- Added `IpamDdiService.preview_reservation()` to build a DNS/DHCP preview from an existing IPAM reservation identified by tenant, VRF and idempotency key.
- Added DNS forward and reverse PTR change generation for BIND and PowerDNS.
- Added Kea DHCP reservation preview when a MAC address is provided.
- Added divergence detection against observed DNS records and DHCP leases already stored in OpenInfra.
- Added rollback-compensating change generation for all previewed operations.
- Added CLI command `openinfra ipam ddi-preview`.
- Added HTTP endpoint `POST /api/v1/ipam/ddi-preview`.
- Preserved pgAdmin4 lab integration from v0.22.3 with `OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld`.
- Preserved v0.22.3 PostgreSQL migration execution safeguards.

## Files changed

- `VERSION`
- `pyproject.toml`
- `src/openinfra/__init__.py`
- `src/openinfra/domain/ipam.py`
- `src/openinfra/application/ports.py`
- `src/openinfra/application/ipam_services.py`
- `src/openinfra/application/container.py`
- `src/openinfra/infrastructure/ddi_connectors.py`
- `src/openinfra/interfaces/cli.py`
- `src/openinfra/interfaces/http_api.py`
- `tests/unit/test_domain_ipam_ddi.py`
- `tests/integration/test_ipam_ddi_services.py`
- `tests/integration/test_cli.py`
- `tests/integration/test_http_api.py`
- `tests/integration/test_runtime_docker_environment.py`
- `README.md`
- `CHANGELOG.md`
- `docs/api/openapi.yaml`
- `docs/architecture/ARCHITECTURE.md`
- `docs/TRACEABILITY.md`
- `docs/runbooks/VALIDATION.md`
- `compose.yaml`
- `.env.example`
- `scripts/docker_environment.py`
- `scripts/quality_gate.py`
- `VALIDATION-REPORT.md`
- `SHA256SUMS.txt`

## Regression coverage added

- Domain tests validate provider/action/kind serialization, rollback compensation, divergence serialization and `safe_to_apply` semantics.
- Integration tests validate DDI preview generation for BIND, PowerDNS and Kea from an existing reservation.
- Integration tests validate dry-run default behavior, rollback change generation and audit event emission.
- Integration tests validate DNS/PTR divergence detection and unsafe preview classification.
- Integration tests validate the CLI `ipam ddi-preview` workflow.
- Integration tests validate the HTTP `/api/v1/ipam/ddi-preview` endpoint.
- Existing PostgreSQL migration regression tests for `0001` to `0018` remain in place.
- Existing Docker pgAdmin regression tests keep `admin@openinfra.tld` and block `.local` regression.

## Validation results executed in this environment

| Validation | Result |
| --- | --- |
| `python3 scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python3 -m pytest -q` | PASS — 223 passed, coverage 98.03% |
| `PYTHONPATH=src python3 scripts/quality_gate.py` | PASS — 223 passed, coverage 98.03% |
| `PYTHONPATH=src python3 -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli version` | PASS — `0.23.0` |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — status valid, version 4.0.0, 488 requirements, 310 tests |
| CLI render migrations `0001` → `0018` | PASS — 18 migrations rendered in order |
| Compose YAML parse validation | PASS — `compose.yaml` parsed as a YAML mapping |
| OpenAPI YAML parse validation | PASS — `docs/api/openapi.yaml` parsed as a YAML mapping |
| Native runtime smoke | PASS — systemd/runbook/version assets present |
| DDI CLI smoke | PASS — reservation preview generated 5 changes, 5 rollback changes, no divergences, `safe_to_apply=true` |
| Artifact verification | PASS — archive contains required OpenInfra source files |
| Zip integrity test | PASS — no compressed-data errors detected |
| Archive cleanup verification | PASS — no `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `build`, `dist`, `*.egg-info`, `.pyc` or `.coverage` entries |
| Forbidden marker scan | PASS — no project TODO/FIXME/stub/placeholder outside the specification validator forbidden-word list |

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
