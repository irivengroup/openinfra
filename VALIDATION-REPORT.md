# OpenInfra v0.29.49 — rapport de validation

## Objet

Correction UX ciblée du badge `OPENINFRA_WEB_EDITION` : le badge reste affiché juste après le logo OpenInfra, conserve son gabarit Bootstrap `badge`, et utilise désormais un dégradé fuchsia très foncé tirant vers prune chaud/bruné sans devenir marron.

## Changements validés

- Gradient du badge édition : `#2a0015 0%`, `#4b001f 46%`, `#6a1430 100%`.
- Suppression persistante de l’héritage Bootstrap bleu `text-bg-primary` sur le badge édition.
- Exclusion de l’ancien fuchsia clair `#ff2bd6` / `#c000a8` dans le bloc CSS du badge.
- Conservation de la classe Bootstrap `badge` sans changement de padding, taille de police, hauteur ou largeur minimale.
- Alignement runtime statique et frontend React.
- Mise à jour README, CHANGELOG, documentation UI, architecture, CDC et roadmap.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python -m openinfra version` | PASS — 0.29.49 |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profils |
| `python scripts/native_runtime_smoke.py` | PASS |
| Validation CDC v4.8.1 | PASS — 792 exigences, 519 entités |
| Validation roadmap v2 | PASS — 19 phases, 114 epics, 8 gates, 65 tests |
| `pytest --collect-only --no-cov` | PASS — 447 tests collectés |
| Tests ciblés web/runtime | PASS — 17 tests |
| Tests unitaires + architecture | PASS — 177 tests |
| Tests intégration exécutés en lots | PASS — 270 tests |
| `coverage report --fail-under=98` | PASS — 98 % |
| `python scripts/quality_gate.py` | PASS |

## Notes d’exécution

La commande d’intégration monolithique avec couverture a atteint le timeout de l’environnement. Les mêmes tests collectés ont été exécutés ensuite en lots/fichiers, sans échec, puis la couverture globale a été reconstruite et validée à 98 %.

## Validations non exécutées localement

- `ruff` : binaire absent.
- `mypy` : binaire absent.
- `bandit` : binaire absent.
- `pip-audit` : binaire absent.
- `python -m build` : module `build` absent.
- `npm run build` : `web/node_modules` / Vite absents.
- Docker Compose live : Docker absent.
