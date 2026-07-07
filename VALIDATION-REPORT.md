# OpenInfra v0.29.28 — rapport de validation

Date: 2026-07-07

## Périmètre livré

OpenInfra v0.29.28 complète le jalon P10/DCIM côté dashboard : l’opération **Élévation rack** est exposée dans l’interface web et les opérations visuelles DCIM supportent désormais un choix explicite du format de rendu (`json`, `svg`, `html`) lorsque le contrat API le permet.

Cette évolution ne contourne pas le domaine : elle consomme les contrats HTTP DCIM déjà présents, préserve la localisation/relocalisation v0.29.26, et ajoute une parité UI/API pour l’exploitation visuelle des salles et racks.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python -m openinfra.interfaces.cli version` | PASS — 0.29.28 |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS — 764 exigences, 519 entités |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS — 764 exigences |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 37 tests |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profils |
| `python scripts/native_runtime_smoke.py` | PASS |
| `python -m openinfra.interfaces.cli installer validate --root installers` | PASS — 6 profils |
| `python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS — 6 profils |
| `python -m pytest --collect-only --no-cov tests` | PASS — 407 tests collectés |
| `pytest` par lots avec `pytest-cov` et couverture combinée | PASS — 407 tests exécutés |
| `coverage report --fail-under=98` | PASS — 98.0094 % |
| `python scripts/quality_gate.py` | PASS |
| `python scripts/verify_artifact.py /mnt/data/openinfra-python-0.29.28.zip` | PASS |
| `zip -T openinfra-python-0.29.28.zip` | PASS |
| `zip -T openinfra-cdc-sfg-stg-v4.8.1-updated-0.29.28.zip` | PASS |
| `zip -T openinfra-roadmap-developpement-v2-updated-0.29.28.zip` | PASS |

## Validations non exécutées localement

| Validation | Raison |
|---|---|
| `ruff format --check src tests scripts docker` | outil `ruff` absent |
| `ruff check src tests scripts docker` | outil `ruff` absent |
| `mypy src/openinfra` | outil `mypy` absent |
| `bandit -q -r src/openinfra` | outil `bandit` absent |
| `pip-audit --dry-run` | outil `pip-audit` absent |
| `python -m build` | module `build` absent |
| `npm run build` | `web/node_modules` absent ; dépendances Vite non installées |
| Docker Compose live | Docker indisponible dans l’environnement |

## Couverture finale

- Lignes couvertes : 12 654 / 12 911.
- Lignes manquantes : 257.
- Couverture : 98.0094 %.

## Remarques

Le mono-run `pytest` complet dépasse le timeout de l’environnement interactif ; la suite a donc été exécutée par lots, avec couverture cumulée, puis contrôlée par `coverage report --fail-under=98` et `quality_gate.py`.
