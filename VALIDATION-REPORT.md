# OpenInfra Python POO v0.9.0 — Rapport de validation

## Synthèse

Version livrée : `0.9.0`.

Cet incrément ajoute un audit trail consultable, exportable et vérifiable avec intégrité chaînée SHA-256. La fonctionnalité est intégrée au domaine, à l'application, aux adaptateurs JSON/PostgreSQL, à la CLI, à l'API HTTP, aux migrations PostgreSQL, au runtime Docker, à la documentation et à la CI.

## Changements fonctionnels

- Ajout du domaine `audit` : filtres, pagination, export, rapports d'intégrité et calcul de hash chaîné.
- Ajout du service applicatif `AuditTrailService`.
- Extension du port `AuditRepository` avec listing paginé et vérification d'intégrité.
- Extension des adaptateurs `JsonAuditRepository` et `PostgreSQLAuditRepository`.
- Ajout de la permission `audit.read` et du rôle `audit:reader`.
- Ajout migration PostgreSQL `0006_audit_trail_integrity.sql`.
- Ajout CLI :
  - `openinfra audit list`
  - `openinfra audit export`
  - `openinfra audit verify-integrity`
- Ajout API :
  - `GET /api/v1/audit/events`
  - `POST /api/v1/audit/export`
  - `GET /api/v1/audit/integrity`
- Extension du runtime Docker smoke pour vérifier l'audit trail authentifié.
- Mise à jour README, OpenAPI, runbooks, architecture, CI et changelog.

## Fichiers principaux concernés

- `src/openinfra/domain/audit.py`
- `src/openinfra/application/audit_services.py`
- `src/openinfra/application/ports.py`
- `src/openinfra/application/container.py`
- `src/openinfra/domain/security.py`
- `src/openinfra/application/security_services.py`
- `src/openinfra/infrastructure/json_store.py`
- `src/openinfra/infrastructure/postgresql.py`
- `src/openinfra/interfaces/cli.py`
- `src/openinfra/interfaces/http_api.py`
- `migrations/postgresql/0006_audit_trail_integrity.sql`
- `docker/openinfra-runtime-smoke.py`
- `.github/workflows/ci.yml`
- `docs/api/openapi.yaml`
- `docs/runbooks/VALIDATION.md`
- `docs/runbooks/RUNTIME_DOCKER.md`
- `docs/runbooks/POSTGRESQL_CLUSTER.md`
- `docs/architecture/ARCHITECTURE.md`
- `README.md`
- `CHANGELOG.md`
- `VERSION`
- `pyproject.toml`

## Validations exécutées localement

```text
compileall : PASS
pytest : PASS, 86 tests
couverture : PASS, 90.07 %, seuil 90 %
quality_gate.py : PASS
CLI version : PASS, 0.9.0
CLI spec validate : PASS, 488 exigences, 310 tests
Render migrations 0001/0002/0003/0004/0005/0006 : PASS
CLI security bootstrap-token : PASS
CLI IPAM allocation : PASS
CLI audit list : PASS
CLI audit export JSONL : PASS
CLI audit verify-integrity : PASS
YAML compose.yaml : PASS
YAML GitHub Actions : PASS
YAML OpenAPI : PASS
docker_environment.py init : PASS, .env généré en mode 0600 puis supprimé
Recherche marqueurs interdits dans src/tests/scripts/docker/migrations : PASS
Longueur de lignes Python <= 100 dans src/tests/scripts/docker : PASS
```

## Commandes exécutées

```bash
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 scripts/quality_gate.py
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0001_bootstrap --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0002_security_rbac --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0003_security_token_lifecycle --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0004_identity_users_groups --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0005_access_policy_abac --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0006_audit_trail_integrity --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli security bootstrap-token --data "$TMPDIR/state.json" --tenant default --subject audit-admin --role admin --token "$TOKEN"
PYTHONPATH=src python3 -m openinfra.interfaces.cli ipam allocate --data "$TMPDIR/state.json" --tenant default --vrf default --prefix 10.190.0.0/30 --hostname audit-smoke --idempotency-key smoke-v09-1
PYTHONPATH=src python3 -m openinfra.interfaces.cli audit list --data "$TMPDIR/state.json" --tenant default --admin-token "$TOKEN"
PYTHONPATH=src python3 -m openinfra.interfaces.cli audit export --data "$TMPDIR/state.json" --tenant default --admin-token "$TOKEN" --format jsonl
PYTHONPATH=src python3 -m openinfra.interfaces.cli audit verify-integrity --data "$TMPDIR/state.json" --tenant default --admin-token "$TOKEN"
python3 scripts/docker_environment.py init
```

## Validations non exécutées localement

Ces validations sont configurées dans la CI GitHub Actions mais les binaires ou services ne sont pas disponibles dans l'environnement courant :

```text
ruff : indisponible localement
mypy : indisponible localement
bandit : indisponible localement
python -m build : module build indisponible localement
Docker Compose runtime réel : Docker indisponible localement
PostgreSQL réel hors Docker : aucun serveur PostgreSQL externe disponible
```

## Risques résiduels

- L'audit trail est opérationnel en backend JSON et testé avec adaptateur PostgreSQL simulé.
- La validation PostgreSQL réelle doit être exécutée via le runtime Docker ou un cluster PostgreSQL disponible.
- Les intégrations entreprise avancées restent hors périmètre de cette version : OIDC, LDAP, SAML, SCIM, UI d'administration, Discovery distribué, imports massifs, graphe avancé, jobs distribués, archivage WORM externe et signature cryptographique externe des journaux.
