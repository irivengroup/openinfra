# OpenInfra v0.29.18 — rapport de validation

## Objet

v0.29.18 enrichit le dashboard d’accueil `openinfra-web` avec des statistiques par composant : métriques fonctionnelles, champs métier et camemberts lecture/mutation, tout en conservant le header principal unique, la navigation par accordéons et le trust `openinfra-web` ↔ backend côté serveur.

## Changements validés

- L’accueil web expose une section `Statistiques des composants OpenInfra`.
- Les composants RI, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit disposent chacun d’une carte de statistiques.
- Chaque carte affiche un camembert lecture/mutation sans afficher de méthode HTTP à l’opérateur.
- Les métriques exposées sont calculées depuis le catalogue UI : opérations, champs métier, champs obligatoires et mutations.
- Les assets runtime servis depuis `src/openinfra/interfaces/rendering/static` sont alignés avec les sources React.
- Les fragments de l’ancien second bandeau restent absents : `openinfra-search`, `openinfra-login`, `openinfra-signup`, `Search OpenInfra operations`, `Login` et `Sign-up`.
- Le frontend ne divulgue toujours aucun DSN PostgreSQL ni secret backend.
- Le CDC v4.8.1 ajoute `REQ-00749` et `TST-WEB-052`.
- La roadmap v2 ajoute `TST-P08-WEB-COMPONENT-STATS`.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers` | PASS |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.18 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 749 exigences, 554 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 25 tests |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS — 749 exigences |
| `PYTHONPATH=src:. python -m pytest --no-cov tests/integration/test_openinfra_web.py tests/integration/test_runtime_docker_environment.py -q` | PASS — 12 tests |
| `PYTHONPATH=src:. python -m pytest ... par lots avec --cov-append` | PASS — 388 tests collectés/exécutés |
| `python -m coverage report --fail-under=98` | PASS — 98 % |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |

## Exécution par lots

Le mono-run complet `PYTHONPATH=src:. python -m pytest` a été remplacé par l’exécution par lots avec `coverage append` afin d’éviter le timeout de l’environnement interactif. Les 61 fichiers de tests collectés, soit 388 tests, ont été exécutés et le rapport final de couverture global atteint le seuil `--fail-under=98`.

## Non exécuté dans cet environnement

| Validation | Cause |
|---|---|
| `ruff format --check` / `ruff check` | outil non installé localement |
| `mypy src/openinfra` | outil non installé localement |
| `bandit -q -r src/openinfra` | outil non installé localement |
| `pip-audit --dry-run` | outil non installé localement |
| `python -m build` | module `build` non installé localement |
| `npm run build` | dépendances Node non installées localement dans `web/node_modules` |
| Docker Compose PostgreSQL live | Docker indisponible dans l'environnement |

## Résultat

Livraison acceptée : le dashboard d’accueil affiche désormais les statistiques et camemberts par composant, sans régression détectée sur le portail web, la configuration runtime, les installateurs, le CDC, la roadmap et la couverture globale.
