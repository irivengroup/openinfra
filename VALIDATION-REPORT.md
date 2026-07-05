# OpenInfra v0.29.10 — validation report

Date: 2026-07-05
Base: OpenInfra v0.29.9
Scope: P07 authentication, LDAP/IPA, RBAC group mapping and permission audit before resuming Discovery.

## Scope delivered

- Local `standard` authentication remains the only accepted mode for Lite.
- LDAP/IPA authentication is accepted only for Pro/Enterprise backend `server` scopes.
- `web` and `agent` scopes do not connect directly to LDAP/IPA; they rely on backend-mediated authentication.
- LDAP/IPA configuration requires `ldaps://`, TLS validation and secret references only.
- External directory groups are mapped to OpenInfra internal groups and roles; OpenInfra remains the RBAC authority.
- External authentication produces OpenInfra application tokens and records audit events.
- PostgreSQL migration `0025_authentication_ldap_ipa_rbac.sql` adds authentication provider config, external group mappings and partitioned permission audit tables.
- LDAP/IPA runtime dependency `ldap3` is separated by scope and loaded only when external directory authentication is used.

## Files changed

- `src/openinfra/domain/authentication.py`
- `src/openinfra/application/authentication_services.py`
- `src/openinfra/application/container.py`
- `src/openinfra/infrastructure/external_identity.py`
- `src/openinfra/infrastructure/installer_config.py`
- `src/openinfra/interfaces/cli.py`
- `installers/migrations/postgresql/0025_authentication_ldap_ipa_rbac.sql`
- `installers/requirements/auth-ldap.txt`
- `installers/requirements/pro-server.txt`
- `installers/requirements/enterprise-server.txt`
- `requirements/auth-ldap.txt`
- `requirements/security-audit.txt`
- `pyproject.toml`
- `tests/unit/test_authentication_domain.py`
- `tests/unit/test_external_identity_infrastructure.py`
- `tests/integration/test_external_authentication_services.py`
- `tests/integration/test_installer_alignment.py`
- CDC, architecture, runbook, traceability, README and CHANGELOG.

## Validations executed

```bash
PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
bandit -q -r src/openinfra
PYTHONPATH=src:. python scripts/security_gate.py --project-root .
pip-audit --dry-run
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py
python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py
PYTHONPATH=src python -m openinfra.interfaces.cli auth policy --edition enterprise --mode ipa --url ldaps://ipa.example.net --base-dn dc=example,dc=net --bind-dn-ref env:OPENINFRA_IPA_BIND_DN --bind-password-ref env:OPENINFRA_IPA_BIND_PASSWORD
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
- Pytest: PASS — 366 tests.
- Coverage: PASS — 98.04 %, threshold >= 98 %.
- Quality gate: PASS.
- CLI version: PASS — 0.29.10.
- CDC v4.8.1 validation: PASS — 735 requirements, 543 tests.
- Roadmap v2 validation: PASS — 19 phases, 114 epics, 8 gates, 20 tests.
- Installer validate/dry-run: PASS — 6 profiles.
- Autonomous installer validation: PASS.
- Enterprise alignment validation: PASS.
- Native runtime smoke: PASS.
- Migration catalog load: PASS — 25 migrations.
- CLI auth policy smoke: PASS — Enterprise IPA accepted with secret references and RBAC authority OpenInfra.
- Build wheel/sdist: PASS — `openinfra-0.29.10-py3-none-any.whl`, `openinfra-0.29.10.tar.gz`.
- Artifact verification: PASS.
- Archive cleanup: PASS — no `deploy/`, no root `migrations/`, no legacy installer roots, no caches.

## Not executed

- Docker Compose with a live PostgreSQL instance was not executed in this environment because Docker is unavailable here.
