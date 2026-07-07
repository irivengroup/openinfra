# Rapport de validation — OpenInfra v0.29.40

## Synthèse

Livraison validée pour l'incrément v0.29.40 : restauration de la palette initiale des camemberts, branchement réel des boutons Swagger/ReDoc sur la documentation backend API, remplacement du pictogramme ITRM par une icône de référentiel/référence et fixation du double header en haut de viewport.

## Changements couverts

- Camemberts Dashboard revenus à la palette initiale `--openinfra-action` / `--openinfra-green`, avec interdiction du fuchsia dans le gradient et les légendes.
- Boutons `Swagger` et `ReDoc` branchés sur les URLs `apiDocumentation` publiées par `/config.json`.
- Proxy BFF `openinfra-web` pour `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml` vers `openinfra-api`.
- Variable `OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL` pour les déploiements web/API séparés.
- Icône ITRM remplacée par une icône `reference`, représentant un référentiel/référence, dans les sources React et les assets runtime.
- Double header fixé en haut de viewport via `openinfra-header-stack`, offset dynamique `--openinfra-fixed-header-height`, body offset et sidebar sticky sous header.
- CDC/Roadmap alignés avec `REQ-00780`, `REQ-00781`, `REQ-00782`, `REQ-00783`, `TST-WEB-083`, `TST-WEB-084`, `TST-WEB-085`, `TST-WEB-086`.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS — 783 exigences, 519 entités |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 56 tests |
| `PYTHONPATH=src python -m openinfra version` | PASS — 0.29.40 |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_enterprise_alignment.py --cdc-root ... --roadmap-root ... --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m pytest -q --collect-only --no-cov` | PASS — 440 tests collectés |
| `PYTHONPATH=src python -m pytest -q --no-cov` par lots | PASS — 440 tests exécutés |
| `PYTHONPATH=src python -m pytest -q --cov=src/openinfra --cov-report= --cov-append --cov-fail-under=0` par lots | PASS — 440 tests exécutés avec couverture agrégée |
| `coverage report --fail-under=98` | PASS — total 98 % |
| `python scripts/quality_gate.py` | PASS |
| `zip -T openinfra-python-0.29.40.zip` | PASS |
| `zip -T` CDC/Roadmap | PASS |
| `python scripts/verify_artifact.py /mnt/data/openinfra-python-0.29.40.zip` | PASS |

## Validations non exécutées localement

- `ruff format --check src tests scripts docker` : binaire `ruff` absent.
- `ruff check src tests scripts docker` : binaire `ruff` absent.
- `mypy src/openinfra` : binaire `mypy` absent.
- `bandit -q -r src/openinfra` : binaire `bandit` absent.
- `pip-audit --dry-run` : binaire `pip-audit` absent.
- `python -m build` : module `build` absent.
- `npm run build` : `web/node_modules` / `vite` absents.
- Docker Compose live : Docker absent.

## Notes d'exécution

La suite fonctionnelle complète a été exécutée en lots déterministes pour éviter les timeouts de l’environnement. La couverture a été agrégée avec `coverage --append`, puis contrôlée par `coverage report --fail-under=98` et `quality_gate.py`.
