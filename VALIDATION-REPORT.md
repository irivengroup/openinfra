# OpenInfra v0.29.9 — validation report

Date: 2026-07-05
Base: OpenInfra v0.29.8
Scope: corrective runtime migration fix before resuming P07.

## Incident fixed

`openinfra database apply-migrations` failed on PostgreSQL while applying `0024_postgresql_ha_backup_registry.sql`:

```text
psycopg.errors.FeatureNotSupported: unique constraint on partitioned table must include all partitioning columns
DETAIL: PRIMARY KEY constraint on table "postgresql_backup_runs" lacks column "started_at" which is part of the partition key.
```

Root cause: `postgresql_backup_runs` is partitioned by `RANGE (started_at)` but used `PRIMARY KEY (tenant_id, id)`. PostgreSQL requires any unique constraint, including a primary key, on a partitioned table to include all partitioning columns.

## Code changes

- `installers/migrations/postgresql/0024_postgresql_ha_backup_registry.sql`
  - Changed `postgresql_backup_runs` primary key to `PRIMARY KEY (tenant_id, started_at, id)`.
- `src/openinfra/infrastructure/postgresql.py`
  - Added `PostgreSQLPartitionConstraintValidator`.
  - Migration validation now rejects partitioned table `PRIMARY KEY`, `UNIQUE` constraints and unique indexes that do not include partition columns.
- `tests/integration/test_postgresql_migration.py`
  - Added regression tests for the corrected `0024` primary key.
  - Added a negative validation test proving an invalid partitioned primary key is rejected before runtime.
- Version and runtime metadata updated to `0.29.9`.
- README, CHANGELOG and traceability updated.

## Validations executed

```bash
python -m compileall -q src tests scripts docker installers
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
bandit -q -r src/openinfra
PYTHONPATH=src:. python scripts/security_gate.py --project-root .
pip-audit --dry-run
PYTHONPATH=src:. python -m pytest
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --root installers/migrations/postgresql --name 0024_postgresql_ha_backup_registry
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py
python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py
python installers/setup/lite/install.py --dry-run --json
python installers/setup/enterprise/agent/install.py --dry-run --json
python -m build
python scripts/verify_artifact.py dist/*.whl
```

## Results

- Compileall: PASS.
- Ruff format/check: PASS.
- MyPy strict: PASS.
- Bandit: PASS.
- Security gate: PASS.
- pip-audit dry-run: PASS — 512 packages would be audited, no known vulnerabilities found.
- Pytest: PASS — 347 tests.
- Coverage: PASS — 98.01 %, threshold >= 98 %.
- Quality gate: PASS.
- CLI version: PASS — 0.29.9.
- CDC v4.8.1 validation: PASS — 735 requirements, 543 tests.
- Roadmap v2 validation: PASS — 19 phases, 114 epics, 8 gates, 20 tests.
- Installer validate/dry-run: PASS — 6 profiles.
- Autonomous installer validation: PASS.
- Enterprise alignment validation: PASS.
- Native runtime smoke: PASS.
- Migration catalog load: PASS — 24 migrations.
- Migration 0024 render check: PASS — `PRIMARY KEY (tenant_id, started_at, id)` present.
- Build wheel/sdist: PASS — `openinfra-0.29.9-py3-none-any.whl`, `openinfra-0.29.9.tar.gz`.
- Artifact verification: PASS.

## Not executed

- Docker Compose with a live PostgreSQL instance was not executed in this environment because Docker is unavailable here.

## Recommended live verification on the user's host

```powershell
docker compose build --no-cache
docker compose up -d postgres openinfra-migrate
docker logs openinfra-migrate
```

Expected outcome: migration `0024_postgresql_ha_backup_registry.sql` applies without the partitioned primary key error.
