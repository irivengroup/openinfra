# OpenInfra v0.29.46 — Rapport de validation

## Périmètre

La version v0.29.46 ajoute l’accessibilité critique du portail web OpenInfra sans modifier les contrats backend existants. L’incrément couvre la navigation, les landmarks, la recherche globale et la restitution de focus après sélection d’un résultat.

## Changements validés

- Ajout d’un lien d’évitement clavier vers le contenu principal.
- Ajout d’un landmark principal stable `openinfra-main-content` avec focus programmatique sécurisé.
- Ajout de `aria-current` sur les entrées actives du header, du Dashboard, des composants et des opérations du panneau latéral.
- Renforcement des accordéons du panneau latéral avec `aria-controls`, `aria-labelledby` et `role="region"`.
- Déclaration de la recherche globale en `role="search"` et du champ en combobox accessible.
- Déclaration des résultats de recherche en `role="listbox"`, groupes et options accessibles, avec annonce `aria-live`.
- Focus transféré vers le contenu principal après sélection depuis la recherche globale locale ou backend.
- États `focus-visible` homogènes sur header, sidebar, recherche, opérations et boutons Swagger/ReDoc.
- Alignement des sources React, des assets runtime statiques, du validateur frontend, des tests, de la documentation, du CDC et de la roadmap.

## Fichiers principaux modifiés

- `web/src/main.jsx`
- `web/src/openinfra-theme.css`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.js`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`
- `scripts/validate_frontend.py`
- `tests/integration/test_openinfra_web.py`
- `README.md`
- `CHANGELOG.md`
- `docs/ui/OPENINFRA_WEB.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/**`
- `docs/specifications/OpenInfra-Roadmap-Developpement-v2/**`
- `VERSION`
- `pyproject.toml`
- `web/package.json`
- `src/openinfra/__init__.py`

## Validations exécutées

| Validation | Résultat |
| --- | --- |
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.46` |
| `PYTHONPATH=src:. python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `PYTHONPATH=src:. python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 789 exigences, 594 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py --root docs/specifications/OpenInfra-Roadmap-Developpement-v2` | PASS — 19 phases, 114 epics, 8 gates, 62 tests |
| `PYTHONPATH=src:. pytest --collect-only --no-cov` | PASS — 447 tests collectés |
| `PYTHONPATH=src:. pytest -q --no-cov tests/integration/test_openinfra_web.py tests/integration/test_runtime_docker_environment.py` | PASS — 17 tests |
| `PYTHONPATH=src:. pytest -q --no-cov tests/unit tests/architecture` | PASS — 177 tests |
| Tests d’intégration par lots avec `--no-cov` | PASS — 270 tests |
| Agrégation de couverture par lots avec `coverage run -a -m pytest -q --no-cov ...` | PASS |
| `coverage report --fail-under=98` | PASS — 98 % |
| `PYTHONPATH=src:. python scripts/quality_gate.py --project-root .` | PASS |

## Précision sur `pytest` global

La commande monolithique `PYTHONPATH=src:. pytest -q --no-cov` a progressé sans échec visible mais a atteint la limite de temps de l’environnement. Pour éviter un faux statut bloquant, la validation complète a été reconstruite en lots : unitaires, architecture, intégration et couverture agrégée. Les 447 tests collectés sont couverts par ces lots et la couverture globale vérifiée reste à 98 %.

## Validations non exécutables dans cet environnement

- `ruff` : binaire absent.
- `mypy` : binaire absent.
- `bandit` : binaire absent.
- `pip-audit` : binaire absent.
- `python -m build` : module `build` absent.
- `npm run build` : `vite` indisponible car `web/node_modules` absent.
- Docker Compose live : Docker absent.

## Contrôles packaging

- Caches Python, pytest, couverture et répertoires temporaires supprimés avant packaging.
- Archive principale contrôlée par `zip -T`.
- Archive principale contrôlée par `scripts/verify_artifact.py`.
- CDC et roadmap packagés séparément après validation de leurs matrices.
