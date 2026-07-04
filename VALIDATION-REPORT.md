# OpenInfra v0.28.0 — Validation report

## Release

- Version: `0.28.0`
- Roadmap: `P07 / EPIC-0701 — Registry collectors et identité forte`
- Date: 2026-07-04

## Delivered scope

- Discovery collector registry with strong identity based on normalized SHA-256 certificate fingerprint.
- Collector registration, heartbeat, disablement, listing and job authorization/rejection.
- Scope-based authorization: no job is delivered to unknown, disabled, fingerprint-mismatched or out-of-scope collectors.
- Vault reference support via `vault://...`; collector secrets are not stored in OpenInfra state or PostgreSQL.
- JSON and PostgreSQL repositories for collectors.
- PostgreSQL migration `0023_discovery_collector_registry.sql`, partitioned by tenant hash.
- CLI commands: `openinfra discovery collector-register`, `collector-heartbeat`, `job-authorize`, `collector-disable`, `collector-list`.
- API endpoints: `/api/v1/discovery/collectors`, `/api/v1/discovery/collectors/heartbeat`, `/api/v1/discovery/jobs/authorize`, `/api/v1/discovery/collectors/disable`.
- OpenAPI, README, architecture, traceability and validation runbook updated.

## Impact analysis

- Additive release: no existing command, endpoint, migration or table was removed.
- Existing imports, bulk imports, signed exports, legacy migration dry-run, Swagger/ReDoc/OpenAPI and Docker lab remain available.
- Production runtime remains native Linux + virtualenv + systemd + PostgreSQL.
- Docker Compose remains a lab/smoke/test environment only.
- Requirements separation is preserved: runtime dependencies remain separated from dev/test/CI/security dependencies.

## Validation commands executed

```text
python -m ruff format --check src tests scripts docker
python -m ruff check src tests scripts docker
python -m mypy src/openinfra
python -m bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python scripts/quality_gate.py
PYTHONPATH=src python -m compileall -q src tests scripts docker
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name <0001..0023> --root migrations/postgresql
PYTHONPATH=src python scripts/native_runtime_smoke.py
python -m build
python scripts/verify_artifact.py dist/openinfra-0.28.0-py3-none-any.whl
```

## Results

| Validation | Result |
| --- | --- |
| Ruff format | PASS — 93 files already formatted |
| Ruff check | PASS |
| MyPy | PASS — no issues in 36 source files |
| Bandit | PASS |
| security_gate.py | PASS |
| pip-audit dry-run | PASS — 47 packages, no known vulnerabilities |
| Pytest | PASS — 308 tests |
| Coverage | PASS — 98.03 % |
| quality_gate.py | PASS — 308 tests, 98.03 % |
| compileall | PASS |
| CLI version | PASS — 0.28.0 |
| Specification validation | PASS — 488 requirements, 310 tests |
| PostgreSQL migrations | PASS — 0001 to 0023 rendered |
| Compose YAML | PASS |
| OpenAPI YAML | PASS |
| Native runtime smoke | PASS |
| Discovery CLI smoke | PASS |
| Build wheel/sdist | PASS |
| verify_artifact.py | PASS |
| Archive cleanup | PASS |

## PostgreSQL migrations rendered

```text
0001_bootstrap
0002_security_rbac
0003_security_token_lifecycle
0004_identity_users_groups
0005_access_policy_abac
0006_audit_trail_integrity
0007_source_of_truth_core
0008_source_governance
0009_dcim_physical_model
0010_dcim_rack_capacity
0011_dcim_field_operations
0012_dcim_visualization_indexes
0013_dcim_cabling_foundation
0014_dcim_energy_cooling_foundation
0015_ipam_enterprise_foundation
0016_ipam_transactional_allocation
0017_ipam_networking_foundation
0018_ipam_conflict_detection
0019_import_framework
0020_bulk_import_framework
0021_export_framework
0022_legacy_migration_framework
0023_discovery_collector_registry
```

## Non-executed validations

- Docker Compose live boot with PostgreSQL live was not executed because the Docker daemon is not available in this environment.

## Residual risks

- The mTLS handshake itself is expected to be enforced by the production reverse proxy/API gateway; OpenInfra v0.28.0 validates the resulting SHA-256 certificate fingerprint supplied to the application contract.
- Real Vault secret retrieval is intentionally not implemented in this registry milestone; the release stores and validates only Vault references.
