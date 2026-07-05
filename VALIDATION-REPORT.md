# OpenInfra v0.29.17 — rapport de validation

## Objet

v0.29.17 applique la correction demandée sur `openinfra-web` : suppression du second bandeau Bootstrap de recherche/actions dans le header web, incluant le champ `Search OpenInfra operations...` et les boutons `Login` / `Sign-up`.

## Changements validés

- Le header web ne contient plus le bloc `px-3 py-2 border-bottom mb-3`.
- Les fragments runtime `openinfra-search`, `openinfra-login`, `openinfra-signup`, `Search OpenInfra operations` et `Sign-up` sont absents des sources React et des assets servis.
- Le header sombre principal Bootstrap 5 est conservé.
- La navigation opérationnelle reste portée par la sidebar accordéon.
- Les formulaires métier typés et le trust `openinfra-web` ↔ backend server-side sont conservés.
- Le CDC v4.8.1 ajoute `REQ-00748` et `TST-WEB-051`.
- La roadmap v2 ajoute le test P08 de non-régression du header principal unique.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers` | PASS |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.17 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 748 exigences, 553 tests |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 24 tests |
| `PYTHONPATH=src:. python -m pytest ... par lots avec coverage append` | PASS — 388 tests collectés/exécutés par lots |
| `python -m coverage report --fail-under=98` | PASS — 98 % |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |

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

Correction acceptée : le second bandeau de header demandé est retiré sans régression détectée sur le portail web, la configuration runtime, les installateurs, le CDC, la roadmap et la couverture globale.
