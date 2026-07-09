# OpenInfra v0.29.74 — Validation Report

Release: `0.29.74`

## Objet

La version v0.29.74 corrige l'incohérence UX introduite autour des organisations ITAM : une organisation est une entité racine et ne doit donc pas afficher de sélecteur Organisation parent, Tenant parent ou tenant de sécurité dans ses formulaires de création, modification ou retrait. Les formulaires Tenant sélectionnent l'organisation parente et, pour les opérations sur un tenant existant, le tenant cible filtré par organisation.

La livraison applique aussi la politique de minimisation des migrations : aucun script PostgreSQL nouveau n'est créé pour ce correctif purement UI. La dernière migration reste `0031_itam_organization_identity.sql`, conservée pour compatibilité ascendante.

## Changements validés

- Suppression des champs web `scope_tenant_id` et du libellé `Tenant de sécurité` dans les formulaires Organisation/Tenant.
- Suppression des sélecteurs globaux Organisation/Tenant pour les opérations Organisation et Tenant.
- Ajout d'un rendu de scope conditionnel : Organisation/Tenant global uniquement pour les opérations qui représentent réellement une ressource, un support, une licence ou un contexte tenant-scoped.
- Ajout des sélecteurs explicites Organisation et Tenant cible sur `itam-tenant`, `itam-tenant-update` et `itam-tenant-delete`.
- Conservation du couple Organisation → Tenant filtré pour les ressources/supports/licences.
- Ajout du test `tests/integration/test_postgresql_migration_policy.py` pour verrouiller l'absence de migration `0032_*`.
- CDC et roadmap mis à jour avec `REQ-00815`, `TST-WEB-114` et `TST-P14-ITAM-FORM-HIERARCHY-MIGRATION-MINIMAL`.

## Validations exécutées

| Commande | Statut |
|---|---|
| `python -m compileall -q src tests scripts docker` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — 0.29.74 |
| `PYTHONPATH=src python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 815 exigences, 614 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 84 tests |
| `PYTHONPATH=src python -m pytest tests/integration/test_openinfra_web.py tests/integration/test_postgresql_migration_policy.py -q --no-cov` | PASS — 14 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/integration` | Interrompu par timeout runtime, remplacé par exécution en lots |
| `PYTHONPATH=src python -m pytest --no-cov -q <lots integration>` | PASS — 321 tests |
| `PYTHONPATH=src python -m pytest --cov=openinfra --cov-append <lots unit/architecture/integration>` | PASS |
| `python scripts/quality_gate.py` | PASS — couverture globale 98 % |

## Non exécuté localement

- `ruff format --check src tests scripts docker` : exécutable `ruff` absent du runtime.
- `ruff check src tests scripts docker` : exécutable `ruff` absent du runtime.
- `bandit -q -r src/openinfra` : exécutable `bandit` absent du runtime.
- `mypy src/openinfra` : exécutable `mypy` absent du runtime.
- `python -m build` : module `build` absent du runtime.
- `pip-audit -r requirements/security-audit.txt` : non exécuté dans ce runtime.
- Build Vite complet : dépendances frontend non installées localement.
- Docker Compose live : non exécuté dans ce runtime.

## Artefacts attendus

- Archive source : `openinfra-python-0.29.74.zip`
- CDC mis à jour : `openinfra-cdc-sfg-stg-v4.8.1-updated-0.29.74.zip`
- Roadmap mise à jour : `openinfra-roadmap-developpement-v2-updated-0.29.74.zip`
