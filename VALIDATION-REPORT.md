# OpenInfra Validation Report — v0.25.1

## Version

- Version: `0.25.1`
- Date: `2026-07-04`
- Type: correctif CI/DevSecOps, sans nouveau jalon roadmap
- Base: `v0.25.0 — P06 / EPIC-0602 Import massif scalable`

## Synthèse

La version `0.25.1` corrige les échecs CI signalés sur la branche `v0.25.0` sans retirer ni modifier le périmètre fonctionnel de l'import massif scalable.

Corrections principales :

- Formatage Ruff appliqué sur les fichiers impactés par le jalon P06.
- Remplacement du parsing XLSX basé sur `xml.etree.ElementTree` par `defusedxml.ElementTree`.
- Ajout de `defusedxml>=0.7.1` aux dépendances runtime et à l'audit de sécurité.
- Correction des alertes Bandit `B405` et `B314` sans `# nosec`.
- Ajout d'un test de non-régression qui rejette un XLSX contenant une entité XML externe.
- Correction des alertes Ruff similaires détectées après formatage : imports, arguments de protocole, `isinstance` moderne, méthodes HTTP héritées `do_GET`/`do_POST`, et subprocess de smoke test contrôlé.
- Correction des erreurs MyPy sur les rapports bulk JSON/PostgreSQL, le typage API HTTP bulk et `DdiChange.compensating`.

Les fonctionnalités `v0.25.0` sont conservées : import bulk, checkpoints, reprise, API/CLI import, Swagger/ReDoc/OpenAPI, pgAdmin `admin@openinfra.tld`, migrations PostgreSQL `0001` à `0020` et environnement Docker lab.

## Fichiers modifiés

- `src/openinfra/infrastructure/import_parsers.py`
- `src/openinfra/application/import_services.py`
- `src/openinfra/domain/ipam.py`
- `src/openinfra/infrastructure/json_store.py`
- `src/openinfra/infrastructure/postgresql.py`
- `src/openinfra/interfaces/http_api.py`
- `tests/unit/test_import_parsers.py`
- `pyproject.toml`
- `requirements/security-audit.txt`
- `CHANGELOG.md`
- `README.md`
- `docs/TRACEABILITY.md`
- `VALIDATION-REPORT.md`
- version/tag files updated to `0.25.1`

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python3 -m ruff format --check src tests scripts docker` | PASS — 85 fichiers formatés |
| `python3 -m ruff check src tests scripts docker` | PASS |
| `python3 -m mypy src/openinfra` | PASS |
| `python3 -m bandit -q -r src/openinfra` | PASS |
| `python3 scripts/security_gate.py --project-root .` | PASS |
| `python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` | PASS — dry-run, 47 packages |
| `PYTHONPATH=src python3 -m pytest -q` | PASS — 270 tests |
| Couverture globale | PASS — 98.07 % |
| `PYTHONPATH=src python3 scripts/quality_gate.py` | PASS — 270 tests, 98.07 % |
| `PYTHONPATH=src python3 -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli version` | PASS — 0.25.1 |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — 488 exigences, 310 tests |
| Rendu des migrations PostgreSQL `0001` à `0020` | PASS |
| Parse YAML `compose.yaml` | PASS |
| Parse YAML `docs/api/openapi.yaml` | PASS |
| `PYTHONPATH=src python3 scripts/native_runtime_smoke.py --project-root .` | PASS |
| Smoke CLI bulk import dry-run + rapport + checkpoint | PASS |
| `python3 -m build --wheel --sdist` | PASS |
| `python3 scripts/verify_artifact.py dist/openinfra-0.25.1-py3-none-any.whl` | PASS |

## Validations non exécutables dans cet environnement

- Docker Compose réel avec PostgreSQL live : non exécuté, car le démon Docker n'est pas disponible dans cet environnement.

## Commandes Docker recommandées côté poste

```powershell
(Get-Content .env) -replace '^OPENINFRA_IMAGE_TAG=.*$', 'OPENINFRA_IMAGE_TAG=0.25.1' | Set-Content .env

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

## Risques résiduels

- Le parsing XLSX reste volontairement minimaliste et orienté imports tabulaires simples ; les fichiers XLSX chiffrés, macros, formules complexes et styles ne sont pas interprétés.
- L'import massif PostgreSQL conserve le traitement batch applicatif ; l'optimisation `COPY` pourra être ajoutée dans un jalon ultérieur sans modifier le contrat CLI/API.
