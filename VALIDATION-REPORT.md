# OpenInfra v0.29.77 — Validation Report

Release: `0.29.77`

## Objet

La version v0.29.77 est un correctif qualité/sécurité sur la base fonctionnelle v0.29.76. Elle corrige les deux échecs CI remontés : Bandit B608 sur la requête PostgreSQL DCIM de liste des racks et Ruff format sur l’arbre `src tests scripts docker`.

Aucune migration PostgreSQL nouvelle n’est créée : le schéma v0.29.76 et la migration additive `0033_dcim_site_dependencies_rack_lifecycle.sql` restent inchangés. Les corrections portent uniquement sur l’implémentation SQL, le formatage/lint et la traçabilité CDC/Roadmap.

## Changements validés

- Remplacement du filtre SQL interpolé `status_filter` par deux variantes de requêtes statiques paramétrées dans `PostgreSQLDcimRepository.list_racks_in_room`.
- Conservation du comportement métier : par défaut seuls les racks actifs sont retournés ; `include_retired=True` retourne aussi les racks retirés.
- Formatage Ruff appliqué sur `src`, `tests`, `scripts` et `docker`.
- Ruff lint stabilisé : import ordering, lignes SQL longues, apostrophe Unicode ambiguë et exceptions N802 pour handlers HTTP imposés par `BaseHTTPRequestHandler`.
- Ajout d’un test de régression source empêchant la réintroduction de `{status_filter}` ou d’un fragment SQL interpolé dans la requête racks.
- CDC et roadmap mis à jour avec `REQ-00818`, `TST-WEB-117` et `TST-P14-QUALITY-RUFF-BANDIT-POSTGRESQL`.

## Validations exécutées

| Commande | Statut |
|---|---|
| `python -m ruff format --check src tests scripts docker` | PASS — 137 fichiers déjà formatés |
| `python -m ruff check src tests scripts docker` | PASS |
| `python -m bandit -q -r src/openinfra` | PASS |
| `python -m compileall -q src tests scripts docker` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — 0.29.77 |
| `PYTHONPATH=src python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 818 exigences, 617 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 86 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 533 tests collectés |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/integration/...` par lots | PASS — 330 tests |
| `PYTHONPATH=src python -m pytest -q -o addopts='' --cov=src/openinfra --cov-report= --cov-fail-under=0 ...` par lots | PASS — 533 tests |
| `python scripts/quality_gate.py` | PASS — couverture globale 98 % |

## Note d’exécution

La commande monolithique `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture tests/integration` a été remplacée par des lots de tests, car le runner local a interrompu l’exécution globale après 300 secondes. Les mêmes 533 tests collectés ont été exécutés avec succès par lots, puis rejoués avec couverture pour alimenter le quality gate.

## Non exécuté localement

- `mypy src/openinfra` : module `mypy` absent du runtime initial.
- `python -m build` : module `build` absent du runtime initial.
- `pip-audit -r requirements/security-audit.txt` : module `pip-audit` absent du runtime initial.
- Build Vite complet : dépendances frontend non installées localement.
- Docker Compose live : non exécuté dans ce runtime.

## Artefacts attendus

- Archive source : `openinfra-python-0.29.77.zip`
- CDC mis à jour : `openinfra-cdc-sfg-stg-v4.8.1-updated-0.29.77.zip`
- Roadmap mise à jour : `openinfra-roadmap-developpement-v2-updated-0.29.77.zip`
