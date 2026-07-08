# Rapport de validation — OpenInfra v0.29.58

## Objet

OpenInfra v0.29.58 prépare l’intégration future d’**OpenService** comme solution ITSM/CMDB autonome externe, raccordable à OpenInfra Pro et Enterprise. Cette livraison ne développe pas OpenService, ne fige pas son futur CDC et n’ajoute aucun ticketing natif OpenInfra.

## Changements validés

- Ajout fournisseur externe `openservice` et alias contrôlés `open-service`, `openservice-cmdb`, `openservice-itsm`.
- Ajout politique OpenService Pro/Enterprise avec `native_ticketing_enabled=false`, `openinfra_web_ui_enabled=false` et `integration_ui_owner=openservice-web`.
- Ajout commandes CLI :
  - `openinfra integrations openservice-validate`
  - `openinfra integrations openservice-cmdb-sync-plan`
- Ajout endpoints API :
  - `POST /api/v1/integrations/itsm/openservice/validate`
  - `POST /api/v1/integrations/itsm/openservice/cmdb-sync-plan`
- Publication discovery et OpenAPI.
- Documentation runbook, architecture, README, CHANGELOG, CDC et roadmap.
- Verrouillage négatif `openinfra-web` : aucune opération OpenService dans le portail web OpenInfra.
- Mise à jour cohérente des versions runtime/package/Docker vers `0.29.58`.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python -m openinfra version` | PASS — `0.29.58` |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 801 exigences, 602 tests |
| Roadmap CSV validation locale | PASS — 19 phases, 114 epics, 8 gates, 73 tests |
| `python -m pytest --collect-only --no-cov -q` | PASS — 486 tests collectés |
| Tests ciblés OpenService/ITSM/API/web | PASS |
| Tests unitaires + architecture | PASS |
| Tests intégration par lots | PASS |
| Couverture globale reconstruite par lots | PASS — 98 % |
| `python scripts/quality_gate.py --project-root .` | PASS |
| `zip -T openinfra-python-0.29.58.zip` | PASS |
| `python scripts/verify_artifact.py openinfra-python-0.29.58.zip` | PASS |

## Non exécuté localement

Non exécutés faute d’outil/runtime disponible dans l’environnement courant : `ruff`, `mypy`, `bandit`, `pip-audit`, `python -m build`, build Vite complet, Docker Compose live.

## Risques résiduels

- Les tests live OpenService ne sont pas exécutables tant que le produit OpenService et son CDC ne sont pas disponibles.
- Le contrat OpenService reste volontairement borné aux collections d’échange stables ; les champs métier détaillés seront alignés après rédaction du CDC OpenService.
