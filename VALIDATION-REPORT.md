# OpenInfra v0.29.52 — rapport de validation

## Objet de livraison

OpenInfra v0.29.52 ajoute la progression opérable des imports massifs reprenables : service domaine/application, CLI, API HTTP, discovery, OpenAPI, portail web et smoke CI pour consulter l’état d’un job bulk à partir de son `job_id`.

## Changements fonctionnels

- Ajout du modèle domaine `BulkImportProgress`.
- Ajout de `GenericImportService.get_bulk_progress`.
- Ajout de la commande `openinfra import bulk-progress`.
- Ajout de l’endpoint `GET /api/v1/imports/bulk-progress`.
- Publication dans le discovery document sous `imports.bulk_progress`.
- Publication du chemin dans `docs/api/openapi.yaml`.
- Ajout du composant web **Imports / Exports** et de l’opération **Progression import massif** dans React et runtime statique.
- Ajout d’un smoke CI JSON bulk import progress.
- Alignement CDC `REQ-00795` / `TST-WEB-096`.
- Alignement roadmap `TST-P13-BULK-IMPORT-PROGRESS`.
- Mise à jour du tag Docker runtime par défaut en `0.29.52` dans `compose.yaml`, `.env.example` et `scripts/docker_environment.py`.

## Fichiers principaux modifiés

- `src/openinfra/domain/data_import.py`
- `src/openinfra/application/import_services.py`
- `src/openinfra/interfaces/cli.py`
- `src/openinfra/interfaces/http_api.py`
- `docs/api/openapi.yaml`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.js`
- `web/src/main.jsx`
- `.github/workflows/ci.yml`
- `tests/integration/test_import_services.py`
- `tests/integration/test_cli_import.py`
- `tests/integration/test_http_api.py`
- `tests/integration/test_openinfra_web.py`
- `README.md`
- `CHANGELOG.md`
- `VALIDATION-REPORT.md`
- `docs/ui/OPENINFRA_WEB.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/TRACEABILITY.md`
- `compose.yaml`
- `.env.example`
- `scripts/docker_environment.py`
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/*`
- `docs/specifications/OpenInfra-Roadmap-Developpement-v2/*`

## Validations exécutées

| Validation | Résultat |
| --- | --- |
| `PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers` | PASS |
| `PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src:. python -m openinfra.interfaces.cli version` | PASS — `0.29.52` |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `PYTHONPATH=src:. python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS — 795 exigences, 521 entités |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 68 tests |
| `PYTHONPATH=src:. pytest --collect-only --no-cov -q` | PASS — 455 tests collectés |
| Tests ciblés imports/API/web/CLI | PASS — 53 tests |
| Tests unitaires + architecture | PASS — 177 tests |
| Tests intégration en lots | PASS — 278 tests |
| Couverture reconstruite par lots + `coverage report --fail-under=98` | PASS — 98 % |
| `PYTHONPATH=src:. python scripts/quality_gate.py --project-root .` | PASS |
| `zip -T` artefacts | PASS |
| `verify_artifact.py` archive principale | PASS |

## Particularités de validation

- La commande monolithique `pytest tests/integration --no-cov` a atteint le timeout de l’environnement après progression sans échec visible. Les tests d’intégration ont donc été exécutés en quatre lots complets, pour un total de 278 tests validés.
- La couverture a été reconstruite avec `coverage run --parallel-mode` sur les lots unitaires/architecture et intégration, puis combinée avant le seuil `98 %`.

## Non exécuté localement

- `ruff`, `mypy`, `bandit`, `pip-audit` : binaires absents de l’environnement.
- `python -m build` : module Python `build` absent.
- `npm --prefix web run build` / Vite : `web/node_modules` absent.
- Docker Compose live : binaire `docker` absent.

## Risques résiduels

- Le build frontend Vite, Docker Compose live, Ruff, Mypy, Bandit, Pip-audit et `python -m build` doivent être rejoués dans l’environnement CI/outillage complet.
