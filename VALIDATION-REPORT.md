# OpenInfra v0.29.73 — Validation Report

Release: `0.29.73`

## Résumé

La version v0.29.73 réaligne ITAM autour d’un référentiel **Organisation** placé au-dessus des tenants. Une organisation représente l’entreprise, le groupe ou l’entité juridique cliente ; un tenant représente une subdivision interne rattachée à une organisation active, par exemple `organisation=Orange` et `tenant=DSI`.

Les formulaires web sélectionnent désormais l’organisation avant le tenant, filtrent la liste des tenants par organisation et proposent un tenant implicite lorsqu’une organisation active n’a encore aucun tenant. Les supports, licences et opérations ITAM métier ne peuvent plus être opérés contre un tenant orphelin.

## Résultats de validation

| Commande | Statut |
| --- | --- |
| `ruff format --check src tests scripts docker` | PASS — 135 fichiers conformes |
| `ruff check src tests scripts docker` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `mypy src/openinfra` | PASS — 54 fichiers source |
| `python -m compileall -q src tests scripts docker` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — 0.29.73 |
| `PYTHONPATH=src python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 814 exigences, 613 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 83 tests |
| `PYTHONPATH=src python -m pytest tests/integration/test_itam_tenant_services.py tests/integration/test_itam_support_http_api.py -q --no-cov` | PASS — 7 tests |
| `PYTHONPATH=src python -m pytest tests/integration/test_itam_tenant_services.py tests/integration/test_itam_support_services.py tests/integration/test_itam_support_http_api.py tests/integration/test_itam_software_license_services.py tests/integration/test_openinfra_web.py -q --no-cov` | PASS — 29 tests |
| `PYTHONPATH=src python -m pytest tests/integration/test_http_api.py tests/integration/test_cli.py -q --no-cov` | PASS — 49 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 523 tests collectés |
| `python scripts/quality_gate.py` | PASS — couverture globale 98 % |
| `python -m build` | PASS — sdist + wheel générés localement |

## Validations par lots

Le lot complet `python -m pytest` en une seule commande dépasse les limites de timeout du runtime local. Les mêmes familles de tests ont été exécutées par lots avec couverture consolidée, puis vérifiées par `quality_gate.py`.

- Unitaires + architecture : PASS — 203 tests.
- Intégration lot 1 : PASS — 96 tests.
- Intégration lot 2 : PASS — 125 tests.
- Intégration lot 3 : PASS — 99 tests.
- Intégration totale par lots : PASS — 320 tests.
- Couverture consolidée : PASS — 98 %.

## Non exécuté localement

- `pip-audit -r requirements/security-audit.txt` : outil disponible, mais échec DNS vers `pypi.org` dans le runtime local.
- Build Vite complet : dépendances frontend non installées dans ce runtime.
- Docker Compose live : runtime Docker non exécuté ici.

## Artefacts

- Archive source : `openinfra-python-0.29.73.zip`
- CDC mis à jour : `openinfra-cdc-sfg-stg-v4.8.1-updated-0.29.73.zip`
- Roadmap mise à jour : `openinfra-roadmap-developpement-v2-updated-0.29.73.zip`
