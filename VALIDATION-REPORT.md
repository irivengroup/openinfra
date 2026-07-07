# OpenInfra v0.29.42 — rapport de validation

## Objet

Correction UX ciblée du header fixe openinfra-web : ombre du header plus prononcée que les éléments de contenu et scroll démarrant exactement sous le double bandeau sur toute la largeur.

## Changements validés

- Ajout de `--openinfra-header-shadow` dans les deux feuilles CSS runtime/source.
- Application de `box-shadow: var(--openinfra-header-shadow)` sur `openinfra-header-stack`.
- Conservation de `position: fixed`, `left: 0`, `right: 0`, `top: 0`, `width: 100%` pour le header pleine largeur.
- Ajout de `scroll-padding-top: var(--openinfra-fixed-header-height)` au document.
- Conservation de `padding-top: var(--openinfra-fixed-header-height)` sur le body et du calcul runtime de hauteur.
- Neutralisation de l’ombre basse concurrente du second bandeau afin que la séparation soit portée par le header complet.
- Mise à jour de `REQ-00783`, `TST-WEB-086` et `TST-P08-WEB-FIXED-HEADER`.

## Validations exécutées

- `python -m compileall -q src tests scripts docker` : PASS
- `python scripts/validate_frontend.py` : PASS
- `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` : PASS
- `python -m openinfra.interfaces.cli version` : PASS — 0.29.42
- `python scripts/security_gate.py` : PASS
- `python scripts/validate_enterprise_alignment.py` : PASS
- `python scripts/validate_autonomous_installer.py` : PASS — 6 profils
- `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` : PASS — 783 exigences, 519 entités
- `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py docs/specifications/OpenInfra-Roadmap-Developpement-v2` : PASS — 19 phases, 114 epics, 8 gates, 56 tests
- `pytest tests/integration/test_openinfra_web.py --no-cov -q` : PASS — 12 tests
- `pytest tests/architecture tests/unit --no-cov -q` : PASS
- `pytest` intégration en 4 lots `--no-cov -q` : PASS
- `zip -T` : PASS
- `scripts/verify_artifact.py` : PASS

## Validations non exécutées dans l’environnement local

- `ruff`, `mypy`, `bandit`, `pip-audit` : binaires absents.
- `python -m build` : module `build` absent.
- `npm run build` : `web/node_modules` / `vite` absents.
- Docker Compose live : commande `docker` absente.
- `native_runtime_smoke.py` : non exécuté car `OPENINFRA_DATABASE_DSN` n’est pas fourni et aucun backend runtime n’est démarré.
- Couverture globale `--fail-under=98` : non finalisée localement ; la collecte par lots avec couverture a dépassé la limite d’exécution de l’environnement. La suite complète a été validée en lots sans couverture.
