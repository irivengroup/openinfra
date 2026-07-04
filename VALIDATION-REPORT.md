# OpenInfra Validation Report — v0.24.0

## Version

- Version: `0.24.0`
- Date: `2026-07-04`
- Jalon roadmap: `P06 / EPIC-0601 — Import framework générique`
- Base conservée: `v0.23.1`

## Synthèse

La version `0.24.0` livre le framework d’import générique P06 et intègre l’exigence de découvrabilité API demandée pendant le jalon: la racine API expose les liens Swagger UI et ReDoc, les interfaces `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml` sont servies par le runtime HTTP, et les smoke tests vérifient ces routes.

## Changements validés

- Domaine `data_import`: modèles de mapping, rapports, impacts et DLQ.
- Service applicatif `GenericImportService`: dry-run, application atomique, validation globale et audit.
- Parseurs CSV, JSON et XLSX sans dépendance runtime lourde.
- Référentiels JSON et PostgreSQL pour les rapports d’import.
- Migration PostgreSQL `0019_import_framework.sql`.
- CLI `openinfra import dataset` et `openinfra import report`.
- API `POST /api/v1/imports/datasets` et `GET /api/v1/imports/report`.
- Documentation API runtime: `/docs`, `/swagger`, `/redoc`, `/openapi.yaml`, `/api/v1/openapi.yaml`.
- Document de découverte `/` et `/api/v1` enrichi avec les liens Swagger, ReDoc et OpenAPI.
- Conservation des corrections v0.22.3/v0.23.1: migrations IPAM, pgAdmin `admin@openinfra.tld`, route racine API et logs de démarrage.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python -m pytest -q` | PASS — 254 tests |
| Couverture globale | PASS — 98.03 % |
| `PYTHONPATH=src python scripts/quality_gate.py` | PASS — 254 tests, 98.03 % |
| `PYTHONPATH=src python -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.24.0 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — 488 exigences, 310 tests |
| Rendu des migrations PostgreSQL `0001` à `0019` | PASS |
| Parse YAML `compose.yaml` | PASS |
| Parse YAML `docs/api/openapi.yaml` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| Smoke CLI import dry-run + lecture rapport | PASS |
| Tests HTTP Swagger/ReDoc/OpenAPI | PASS |

## Validations non exécutables dans cet environnement

Les modules/outils suivants ne sont pas installés dans le runtime local utilisé pour produire cette livraison; les commandes ont été tentées et ont échoué par absence de module, pas par échec fonctionnel du projet:

- `python -m ruff format --check src tests scripts docker` — `No module named ruff`.
- `python -m ruff check src tests scripts docker` — `No module named ruff`.
- `python -m mypy src/openinfra` — `No module named mypy`.
- `python -m bandit -q -r src/openinfra` — `No module named bandit`.
- `python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` — `No module named pip_audit`.
- `python -m build` — `No module named build`.

Docker Compose réel et PostgreSQL live ne sont pas disponibles dans cet environnement; les validations effectuées couvrent le rendu des migrations, les tests applicatifs, les tests d’exécuteur, les contrats HTTP et les fichiers YAML.

## Contrôle d’archive

L’archive livrée est nettoyée des caches et artefacts temporaires suivants:

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
