# OpenInfra Validation Report — v0.26.0

Date: 2026-07-04
Release: `0.26.0`
Roadmap: P06 / EPIC-0603 — Exports asynchrones et signés

## Résumé

La version `0.26.0` ajoute un framework d’exports asynchrones et signés, sans régression sur les jalons précédents. La demande d’export crée un job non bloquant, l’exécution worker produit un artefact CSV/JSON/XLSX, le contenu est haché en SHA-256, signé en HMAC-SHA256 puis vérifié avant téléchargement.

## Changements livrés

- Domaine `data_export` : formats, ressource exportable, filtres, jobs, statuts et métadonnées d’artefact.
- Service applicatif `ExportService` : queue, worker, pagination bornée, sérialisation, signature, audit et vérification d’intégrité.
- Ports/adaptateurs : `ExportRepository`, `JsonExportRepository`, `PostgreSQLExportRepository`.
- Migration PostgreSQL `0021_export_framework.sql` avec tables `export_jobs` et `export_artifacts` partitionnées par hash du tenant, `export_signing_keys` et index d’audit exports.
- CLI : `openinfra export request`, `openinfra export run`, `openinfra export report`, `openinfra export artifact`.
- API : `POST /api/v1/exports/jobs`, `GET /api/v1/exports/jobs`, `POST /api/v1/exports/run`, `GET /api/v1/exports/artifact`.
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
| `PYTHONPATH=src python -m pytest -q` | PASS — 283 tests |
| Couverture globale | PASS — 98.00 % |
| `PYTHONPATH=src python scripts/quality_gate.py` | PASS — 283 tests, 98.00 % |
| `PYTHONPATH=src python -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.26.0 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — 488 exigences, 310 tests |
| Rendu migrations PostgreSQL `0001` → `0021` | PASS |
| `compose.yaml` | YAML valide |
| `docs/api/openapi.yaml` | YAML valide |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| Smoke CLI export request/run/report/artifact | PASS |
| `python -m build` | PASS — wheel + sdist |
| `PYTHONPATH=src python scripts/verify_artifact.py dist/openinfra-0.26.0-py3-none-any.whl` | PASS |

## Tests de non-régression ajoutés ou renforcés

- File d’export non bloquante et exécution worker séparée.
- Export JSON, CSV et XLSX.
- Vérification SHA-256 et HMAC-SHA256 avant téléchargement.
- Rejet d’un artefact altéré ou d’une signature invalide.
- Échec worker audité et job marqué `failed`.
- Validation stricte des filtres, formats, noms d’artefact et métadonnées.
- Migration PostgreSQL `0021` partitionnée et cohérente avec les migrations `0001` à `0021`.
- OpenAPI YAML incluant les endpoints d’export.
- Conservation de Swagger UI, ReDoc et OpenAPI YAML.

## Points non exécutés dans cet environnement

- Docker Compose réel avec PostgreSQL live : non exécuté car le démon Docker n’est pas disponible dans l’environnement courant.
- Application live des migrations sur un serveur PostgreSQL réel : non exécutée ici pour la même raison. Les migrations ont été validées par rendu CLI, tests structurels et exécution simulée de l’exécuteur.

## Commandes Docker à relancer côté poste

```powershell
(Get-Content .env) -replace '^OPENINFRA_IMAGE_TAG=.*$', 'OPENINFRA_IMAGE_TAG=0.26.0' | Set-Content .env

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
