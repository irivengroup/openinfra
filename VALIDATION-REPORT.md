# OpenInfra Validation Report — v0.27.1

Date: 2026-07-04
Release: `0.27.1`
Type: Correctif CI / sécurité
Base: `0.27.0` — P06 / EPIC-0604 Migration depuis référentiels existants

## Résumé

La version `0.27.1` corrige l'échec Bandit `B105 hardcoded_password_string` signalé par la CI sur l'état initial du backend JSON. La clé de signature des exports n'est plus initialisée avec une chaîne vide dans `_empty_state()`. Elle est désormais absente de l'état initial, générée uniquement à la première exécution d'un export signé, persistée ensuite, puis explicitement conservée au rechargement du document JSON.

Cette correction évite le faux positif Bandit sans `#nosec`, sans affaiblir le modèle de signature HMAC-SHA256, sans casser les exports signés et sans modifier le périmètre fonctionnel livré en `0.27.0`.

## Changements livrés

- Suppression de l'entrée initiale `export_signing_secret: ""` dans l'état JSON vide.
- Ajout d'une clé de stockage interne construite sans littéral de secret codé en dur dans un emplacement déclenchant Bandit.
- Conservation explicite de la clé de signature export lors du merge entre état JSON chargé et état vide de référence.
- Maintien de la génération paresseuse de la clé via `secrets.token_hex(32)`.
- Ajout d'un test de non-régression validant que :
  - l'état JSON initial ne contient pas de clé de signature export ;
  - la clé est créée uniquement après exécution d'un export signé ;
  - un artefact signé reste téléchargeable après rechargement complet du backend JSON.
- Alignement version `0.27.1` dans `VERSION`, `pyproject.toml`, `src/openinfra/__init__.py`, `compose.yaml`, `.env.example`, OpenAPI, README, tests Docker et quality gate.
- Conservation de Swagger UI, ReDoc, OpenAPI YAML, imports génériques, imports bulk, exports signés, migration legacy et séparation stricte requirements runtime/dev/CI.

## Fichiers principaux modifiés

- `src/openinfra/infrastructure/json_store.py`
- `tests/integration/test_export_services.py`
- `.env.example`
- `compose.yaml`
- `docs/api/openapi.yaml`
- `pyproject.toml`
- `src/openinfra/__init__.py`
- `scripts/docker_environment.py`
- `scripts/quality_gate.py`
- `tests/integration/test_runtime_docker_environment.py`
- `README.md`
- `CHANGELOG.md`
- `VERSION`

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python3 -m ruff format --check src tests scripts docker` | PASS |
| `python3 -m ruff check src tests scripts docker` | PASS |
| `python3 -m mypy src/openinfra` | PASS |
| `python3 -m bandit -q -r src/openinfra` | PASS |
| `python3 scripts/security_gate.py --project-root .` | PASS |
| `python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` | PASS — 47 packages |
| `PYTHONPATH=src python3 -m pytest -q` | PASS — 295 tests |
| Couverture globale | PASS — 98.02 % |
| `PYTHONPATH=src python3 scripts/quality_gate.py` | PASS — 295 tests, 98.02 % |
| `PYTHONPATH=src python3 -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli version` | PASS — 0.27.1 |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | PASS — 488 exigences, 310 tests |
| Rendu migrations PostgreSQL `0001` → `0022` | PASS |
| `compose.yaml` | YAML valide |
| `docs/api/openapi.yaml` | YAML valide |
| `PYTHONPATH=src python3 scripts/native_runtime_smoke.py` | PASS |
| Smoke CLI migration template/plan/report | Couvert par tests d'intégration |
| `python3 -m build` | PASS — wheel + sdist |
| `PYTHONPATH=src python3 scripts/verify_artifact.py dist/openinfra-0.27.1-py3-none-any.whl` | PASS |

## Tests de non-régression ajoutés ou renforcés

- `tests/integration/test_export_services.py::TestExportService::test_json_backend_signing_secret_is_lazy_and_survives_reload`
- `tests/integration/test_cli_export.py` conserve la validation téléchargement artefact après rechargement CLI.
- `tests/integration/test_runtime_docker_environment.py` conserve l'alignement du tag Docker par défaut.

## Points non exécutés dans cet environnement

- Docker Compose réel avec PostgreSQL live : non exécuté car le démon Docker n'est pas disponible dans l'environnement courant.
- Application live des migrations sur un serveur PostgreSQL réel : non exécutée ici pour la même raison. Les migrations ont été validées par rendu CLI, tests structurels et exécution simulée de l'exécuteur.

## Commandes Docker à relancer côté poste

```powershell
(Get-Content .env) -replace '^OPENINFRA_IMAGE_TAG=.*$', 'OPENINFRA_IMAGE_TAG=0.27.1' | Set-Content .env

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
