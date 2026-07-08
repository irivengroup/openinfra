# Rapport de validation — OpenInfra v0.29.60

## Objet

OpenInfra v0.29.60 finalise P13 / EPIC-1306 avec des guides opérables de migration données pour Device42, NetBox, Nautobot, GLPI et CSV générique. L’incrément expose un guide structuré par source avec template, étapes, contrôles requis, contrôles rollback et critères de succès via CLI, API, discovery, OpenAPI et portail web, sans mutation RSOT.

## Changements validés

- Ajout domaine `MigrationGuideStep` et `MigrationGuide`.
- Ajout commande applicative `MigrationGuideCommand`.
- Ajout service `GenericImportService.get_migration_guide`.
- Ajout CLI `openinfra import migration-guide --source ...`.
- Ajout API `GET /api/v1/imports/migration-guide?source=...`.
- Publication discovery sous `imports.migration_guide`.
- Publication OpenAPI.
- Ajout opération web **Imports / Exports > Guide migration données**.
- Ajout runbook `docs/runbooks/IMPORTS_MIGRATION_GUIDES.md`.
- Alignement README, CHANGELOG, architecture, UI, traçabilité, CDC et roadmap.
- Durcissement de plusieurs handlers HTTP ITSM/ITAM pour retourner une erreur JSON `400` au lieu de fermer la connexion sur payload incomplet ou JSON invalide.

## Garde-fous

- Aucune mutation RSOT pendant la génération du guide.
- `native_ticketing_enabled=false` dans les guides retournés.
- RSOT reste canonique.
- Les guides ne développent pas Device42, NetBox, Nautobot, GLPI ni OpenService.
- Les guides ne déclenchent pas d’import, d’export ou de rollback.
- Les sources prises en charge sont contrôlées : `device42`, `netbox`, `nautobot`, `glpi`, `csv`.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — `0.29.60` |
| `PYTHONPATH=src python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root . --json` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers --json` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 803 exigences, 605 tests |
| `PYTHONPATH=src python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py --root docs/specifications/OpenInfra-Roadmap-Developpement-v2` | PASS — 19 phases, 114 epics, 8 gates, 75 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q -o addopts=""` | PASS — 493 tests collectés |
| Tests ciblés guides migration/API/CLI/web | PASS — 50 tests |
| Tests unitaires + architecture | PASS — 196 tests |
| Tests intégration lot 1 | PASS — 63 tests |
| Tests intégration lot 2 | PASS — 56 tests |
| Tests intégration lot 3 | PASS — 75 tests |
| Tests intégration lot 4 | PASS — 63 tests |
| Tests intégration lot 5 | PASS — 40 tests |
| Couverture globale reconstruite par lots | PASS — 98.35 % |
| `PYTHONPATH=src python scripts/quality_gate.py --project-root .` | PASS |
| `zip -T openinfra-python-0.29.60.zip` | PASS |
| `python scripts/verify_artifact.py openinfra-python-0.29.60.zip` | PASS |

## Non exécuté localement

Non exécutés faute d’outil/runtime disponible dans l’environnement courant : `ruff`, `mypy`, `bandit`, `pip-audit`, `python -m build`, build Vite complet, Docker Compose live.

## Risques résiduels

- Les guides structurent le chemin de migration, mais l’exécution réelle dépend des exports source, des mappings et des validations opérateur.
- Le `pytest` monolithique complet reste non utilisé dans cet environnement ; la validation complète a été rejouée par lots déterministes avec couverture agrégée à 98.35 %.
