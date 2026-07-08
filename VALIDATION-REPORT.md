# OpenInfra v0.29.55 — rapport de validation

## Périmètre livré

- Intégration externe ITSM ServiceNow sans fonctionnalité ITSM native OpenInfra.
- API/CLI/UI pour lister les politiques ITSM externes, valider un connecteur ServiceNow et produire un plan de synchronisation CI.
- Correction UI demandée : les boutons de soumission restent en Bootstrap 5 `btn-primary`, avec surcharge thème turquoise `#24d8ab`.
- Correction UI demandée : le bloc statut runtime web utilise uniquement la couleur de texte `#003D8F`, sans fond, bordure ni padding ajouté.
- Non-régression RSOT canonique issue de v0.29.54 conservée ; alias historiques ITRM/SOT/RI restent dépréciés.

## Validations exécutées

| Validation | Statut |
|---|---:|
| `ruff format --check src tests scripts docker` | PASS |
| `ruff check src tests scripts docker` | PASS |
| `python -m compileall -q src tests scripts docker installers` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python -m openinfra version` | PASS — 0.29.55 |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profils |
| `python scripts/native_runtime_smoke.py` | PASS |
| `python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 798 exigences, 600 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py docs/specifications/OpenInfra-Roadmap-Developpement-v2` | PASS — 19 phases, 114 epics, 8 gates, 70 tests |
| `pytest --collect-only --no-cov` | PASS — 471 tests collectés |
| `pytest tests/unit tests/architecture --no-cov` | PASS — 185 tests collectés dans ce périmètre |
| `pytest tests/integration --no-cov` exécuté en lots | PASS — 286 tests collectés dans ce périmètre |
| Couverture reconstruite par lots + `coverage report --fail-under=98` | PASS — 98.00 % |
| `python scripts/quality_gate.py --project-root .` | PASS |

## Validations non exécutées / non disponibles localement

| Validation | Résultat |
|---|---|
| `mypy src/openinfra` | Non exécuté — binaire `mypy` absent |
| `bandit -q -r src/openinfra` | Non exécuté — binaire `bandit` absent |
| `pip-audit` | Non exécuté — binaire `pip-audit` absent |
| `python -m build` | Non exécuté — module Python `build` absent |
| `npm run build --prefix web` | Non exécuté jusqu’au bout — `vite` absent car `web/node_modules` absent |
| Docker Compose live | Non exécuté — binaire `docker` absent |

## Résultat

La livraison v0.29.55 est validée par les contrôles disponibles dans l’environnement. Les contrôles dépendant d’outils absents sont explicitement listés ci-dessus.
