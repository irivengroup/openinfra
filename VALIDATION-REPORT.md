# Rapport de validation — OpenInfra v0.29.57

## Incrément livré

OpenInfra v0.29.57 complète l'incrément EPIC-1304/P13 des intégrations ITSM externes en ajoutant les connecteurs **GLPI Inventory** et **Freshservice Assets**, sans ticketing natif OpenInfra.

## Changements fonctionnels validés

- Ajout fournisseur domaine `glpi` avec alias contrôlés `glpi-assets`, `glpi-inventory`.
- Ajout fournisseur domaine `freshservice` avec alias contrôlés `fresh-service`, `freshservice-assets`, `freshworks`.
- Ajout politiques de connecteurs externes, validation HTTPS, refus credentials URL, secrets uniquement par `auth_secret_ref`.
- Ajout plans déterministes de synchronisation CI depuis RSOT vers GLPI/Freshservice.
- Ajout commandes CLI `glpi-validate`, `glpi-asset-sync-plan`, `freshservice-validate`, `freshservice-asset-sync-plan`.
- Ajout routes API REST `POST /api/v1/integrations/itsm/glpi/*` et `POST /api/v1/integrations/itsm/freshservice/*`.
- Ajout publication OpenAPI, discovery document, UI, README, CHANGELOG, architecture, runbook, CDC et roadmap.
- Mise à jour cohérente des versions runtime/package/Docker vers `0.29.57`.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python -m openinfra version` | PASS — `0.29.57` |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS — 800 exigences, 525 entités |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 72 tests |
| `python -m pytest --collect-only --no-cov` | PASS — 481 tests collectés |
| Tests ciblés domaine/service/API/web ITSM externes | PASS — 60 tests |
| Tests unitaires + architecture | PASS — 191 tests |
| Tests intégration par lots | PASS — 290 tests |
| Couverture globale reconstruite par lots | PASS — 98 % |
| `python scripts/quality_gate.py` | PASS |

## Validation CLI connecteurs externes

- `openinfra integrations itsm-providers` : PASS — `servicenow`, `jira_service_management`, `glpi`, `freshservice`.
- `openinfra integrations glpi-validate` : PASS.
- `openinfra integrations glpi-asset-sync-plan` : PASS.
- `openinfra integrations freshservice-validate` : PASS.
- `openinfra integrations freshservice-asset-sync-plan` : PASS.

## Validation non monolithique

La commande `python -m pytest -q` en exécution monolithique a démarré mais a dépassé la limite d'exécution locale avant la fin. La validation complète a donc été rejouée par lots déterministes avec couverture agrégée, sans échec, pour couvrir les 481 tests collectés.

## Non exécuté localement

Les outils suivants ne sont pas disponibles dans l'environnement courant : `ruff`, `mypy`, `bandit`, `pip-audit`, `build`. Le build Vite complet et Docker Compose live ne sont pas exécutés faute de runtime Node/Vite/Docker live validé ici. Les hooks CI correspondants restent déclarés dans la GitHub Actions du projet.

## Risques résiduels

- Les connecteurs GLPI/Freshservice sont validés contractuellement, sans appel live vers des instances externes.
- Les credentials restent volontairement abstraits par références de secrets ; leur résolution dépend de l'environnement cible.
- Les tests live GLPI/Freshservice devront être exécutés dans un environnement d'intégration disposant d'instances dédiées.
