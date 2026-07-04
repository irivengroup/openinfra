# OpenInfra Validation Report — v0.27.0

Date: 2026-07-04
Release: `0.27.0`
Roadmap: P06 / EPIC-0604 — Migration depuis référentiels existants

## Résumé

La version `0.27.0` ajoute un framework de migration depuis référentiels existants. Les sources initiales supportées sont Device42, NetBox, Nautobot, GLPI et CSV générique. La migration est simulée avant application : templates contrôlés, dry-run, mapping effectif, rapport d’écarts, lignes invalides, stratégie de reprise et persistance du rapport sont disponibles sans écriture dans la Source of Truth.

## Changements livrés

- Domaine `data_import` étendu : `LegacyMigrationSource`, `MigrationTemplate`, `MigrationGap` et `MigrationPlanReport`.
- Templates Device42, NetBox, Nautobot, GLPI et CSV générique vers les objets Source of Truth.
- Support des mappings littéraux `literal:<valeur>` pour normaliser `kind` et `source` sans colonnes legacy artificielles.
- Service applicatif de planification de migration : sélection de template, dry-run, rapport d’impact, gaps bloquants/non bloquants, audit et persistance.
- Ports/adaptateurs JSON/PostgreSQL étendus pour les rapports de migration.
- Migration PostgreSQL `0022_legacy_migration_framework.sql` avec table `migration_plan_reports` partitionnée par hash du tenant et index de consultation.
- CLI : `openinfra import migration-template`, `openinfra import migration-plan`, `openinfra import migration-report`.
- API : `GET /api/v1/imports/migration-template`, `POST /api/v1/imports/migration-plans`, `GET /api/v1/imports/migration-report`.
- OpenAPI, README, architecture, validation et traçabilité mis à jour.
- Séparation requirements runtime/dev conservée.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m ruff format --check src tests scripts docker` | PASS |
| `python -m ruff check src tests scripts docker` | PASS |
| `python -m mypy src/openinfra` | PASS |
| `python -m bandit -q -r src/openinfra` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` | PASS — 47 packages |
| `PYTHONPATH=src python -m pytest -q` | PASS — 294 tests |
| Couverture globale | PASS — 98.02 % |
| `PYTHONPATH=src python scripts/quality_gate.py` | PASS — 294 tests, 98.02 % |
| `PYTHONPATH=src python -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.27.0 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — 488 exigences, 310 tests |
| Rendu migrations PostgreSQL `0001` → `0022` | PASS |
| `compose.yaml` | YAML valide |
| `docs/api/openapi.yaml` | YAML valide |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| Smoke CLI migration template/plan/report | PASS |
| `python -m build` | PASS — wheel + sdist |
| `PYTHONPATH=src python scripts/verify_artifact.py dist/openinfra-0.27.0-py3-none-any.whl` | PASS |

## Tests de non-régression ajoutés ou renforcés

- Templates Device42, NetBox, Nautobot, GLPI et CSV générique sérialisables et validés.
- Plan de migration dry-run sans écriture dans la Source of Truth.
- Détection de colonne requise absente avec gap bloquant.
- Gaps non bloquants pour colonnes recommandées absentes.
- Persistance/relecture JSON et PostgreSQL des rapports de migration.
- Rejet des rapports corrompus ou incohérents.
- CLI migration template/plan/report.
- API migration template/plan/report avec erreurs contrôlées.
- Migration PostgreSQL `0022` partitionnée et cohérente avec les migrations `0001` à `0022`.
- Conservation de Swagger UI, ReDoc et OpenAPI YAML.

## Points non exécutés dans cet environnement

- Docker Compose réel avec PostgreSQL live : non exécuté car le démon Docker n’est pas disponible dans l’environnement courant.
- Application live des migrations sur un serveur PostgreSQL réel : non exécutée ici pour la même raison. Les migrations ont été validées par rendu CLI, tests structurels et exécution simulée de l’exécuteur.

## Commandes Docker à relancer côté poste

```powershell
(Get-Content .env) -replace '^OPENINFRA_IMAGE_TAG=.*$', 'OPENINFRA_IMAGE_TAG=0.27.0' | Set-Content .env

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
