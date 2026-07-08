# OpenInfra v0.29.67 — Validation Report

Release: `0.29.67`

## Scope

Hotfix de régression web après v0.29.66 : restauration de la navigation sidebar hors Dashboard et suppression du warning navigateur `this.refreshDcimCatalog is not a function`.

## Changes validated

- `OpenInfraDashboard.refreshDcimCatalog()` est maintenant implémentée dans le runtime statique.
- `dcimReferenceLevel()`, `isDcimReferenceField()` et `dcimOptions()` sont intégrées au renderer de formulaires.
- Le catalogue DCIM `/api/v1/dcim/topology-catalog` est chargé de manière non bloquante.
- Les en-têtes d’accordéon sidebar sélectionnent l’opération par défaut du composant et gardent l’accordéon cohérent.
- Les mutations DCIM rafraîchissent le catalogue afin de maintenir les sélecteurs à jour.
- Le bouton menu SVG extra-small de v0.29.66 est conservé.

## Executed validations

| Validation | Result |
| --- | --- |
| `python -m compileall -q src tests scripts` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| OpenAPI YAML parse | PASS — `0.29.67` |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.67` |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m pytest tests/integration/test_openinfra_web.py -q --no-cov` | PASS — 13 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| Integration tests by file with `--no-cov` | PASS — 312 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 515 tests collected |

## Not completed in this runtime

- `ruff`, `mypy`, `bandit`, `pip-audit`, `python -m build` : executables non disponibles localement.
- Full `python -m pytest` avec couverture globale : interrompu par timeout sandbox avant génération d’un rapport complet exploitable.
- `quality_gate.py` : non exécuté car il dépend d’un fichier `.coverage` complet.
- Build Vite complet : dépendances frontend non installées dans ce runtime.
- Docker Compose live : non exécuté dans ce runtime.
