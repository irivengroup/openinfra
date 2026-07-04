# OpenInfra Validation Report — v0.25.0

## Version

- Version: `0.25.0`
- Date: `2026-07-04`
- Jalon roadmap: `P06 / EPIC-0602 — Import massif scalable`
- Base conservée: `v0.24.0`

## Synthèse

La version `0.25.0` livre le mode d’import massif scalable sans retirer ni affaiblir l’import générique atomique livré en `0.24.0`. Le nouveau mode bulk ajoute le streaming CSV, les batches bornés, les checkpoints persistés, la reprise par `job_id`, les métriques d’exécution, la DLQ échantillonnée, les rapports consultables et les contrats CLI/API dédiés.

Les corrections précédentes sont conservées : migrations PostgreSQL IPAM, pgAdmin4 avec `admin@openinfra.tld`, route racine API, logs de démarrage, Swagger UI, ReDoc et OpenAPI YAML.

## Changements validés

- Domaine `data_import` enrichi avec `BulkImportReport`, `BulkImportCheckpoint` et `BulkImportMetrics`.
- Service applicatif `GenericImportService.bulk_import_dataset`: streaming, batches, checkpoint, reprise, dry-run/apply et rapport persisté.
- Parseur CSV streaming via `ImportDatasetParser.iter_rows`; compatibilité conservée pour CSV/JSON/XLSX de l’import générique.
- Référentiels JSON et PostgreSQL pour rapports et checkpoints bulk.
- Migration PostgreSQL `0020_bulk_import_framework.sql` avec tables `bulk_import_jobs` et `bulk_import_checkpoints` partitionnées par tenant.
- CLI `openinfra import bulk-dataset`, `openinfra import bulk-report` et `openinfra import bulk-checkpoint`.
- API `POST /api/v1/imports/bulk-datasets`, `GET /api/v1/imports/bulk-report` et `GET /api/v1/imports/bulk-checkpoint`.
- Documentation API runtime maintenue: `/docs`, `/swagger`, `/redoc`, `/openapi.yaml`, `/api/v1/openapi.yaml`.
- Document de découverte `/` et `/api/v1` conservé avec les liens Swagger, ReDoc et OpenAPI.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python -m pytest -q` | PASS — 269 tests |
| Couverture globale | PASS — 98.07 % |
| `PYTHONPATH=src python scripts/quality_gate.py` | PASS — 269 tests, 98.07 % |
| `PYTHONPATH=src python -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.25.0 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — 488 exigences, 310 tests |
| Rendu des migrations PostgreSQL `0001` à `0020` | PASS |
| Parse YAML `compose.yaml` | PASS |
| Parse YAML `docs/api/openapi.yaml` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| Smoke CLI bulk import dry-run + lecture rapport + checkpoint | PASS |
| Tests HTTP Swagger/ReDoc/OpenAPI | PASS |

## Validations non exécutables dans cet environnement

Les modules/outils suivants ne sont pas installés dans le runtime local utilisé pour produire cette livraison; les commandes ont été vérifiées comme indisponibles localement, pas échouées fonctionnellement sur le projet :

- `python -m ruff format --check src tests scripts docker` — module `ruff` absent.
- `python -m ruff check src tests scripts docker` — module `ruff` absent.
- `python -m mypy src/openinfra` — module `mypy` absent.
- `python -m bandit -q -r src/openinfra` — module `bandit` absent.
- `python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` — module `pip_audit` absent.
- `python -m build` — module `build` absent.

Docker Compose réel et PostgreSQL live ne sont pas disponibles dans cet environnement. Les validations effectuées couvrent le rendu des migrations, les tests applicatifs, les tests d’exécuteur, les contrats HTTP, les fichiers YAML et le smoke runtime natif.

## Contrôle d’archive

L’archive livrée est nettoyée des caches et artefacts temporaires suivants :

- `__pycache__`
- `.pytest_cache`
- `.mypy_cache`
- `.ruff_cache`
- `build`
- `dist`
- `*.egg-info`
- `.coverage`

## Commandes recommandées côté utilisateur

```powershell
(Get-Content .env) -replace '^OPENINFRA_IMAGE_TAG=.*$', 'OPENINFRA_IMAGE_TAG=0.25.0' | Set-Content .env

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
