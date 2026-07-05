# OpenInfra v0.29.15 — rapport de validation

## Objet de livraison

v0.29.15 intègre le thème Bootstrap 5 Dashboard dans `openinfra-web` en conservant le modèle API-only et la sémantique OpenInfra validée précédemment.

Changements principaux :

- `openinfra-web` adopte le thème Bootstrap 5 Dashboard et un header double niveau adapté.
- Les items du header sont alignés sur les domaines OpenInfra : Dashboard, RI, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit.
- Bootstrap 5 est servi localement depuis `src/openinfra/interfaces/rendering/static/assets/bootstrap.min.css`.
- Les adaptations produit restent dans `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`.
- Le dashboard expose recherche, sidebar, métriques runtime, centre d'opérations et exécution API.
- Aucun CDN runtime, aucun DSN PostgreSQL, aucun secret backend et aucun accès direct DB ne sont exposés au navigateur.
- Le CDC v4.8.1 ajoute `REQ-00746` et `TST-WEB-049`.
- La roadmap v2 trace le renforcement P08 Bootstrap Dashboard.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts docker installers` | PASS |
| `python -m ruff format --check src tests scripts docker installers` | PASS |
| `python -m ruff check src tests scripts docker installers` | PASS |
| `python -m mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `pip-audit --dry-run` | PASS — aucune vulnérabilité connue détectée |
| `npm run build` depuis `web/` avec dépendances locales disponibles | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `PYTHONPATH=src:. python -m pytest` par lots avec couverture combinée | PASS |
| `coverage combine && coverage report --fail-under=98` | PASS — 98 % |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.15 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 746 exigences, 551 tests |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers` | PASS — 6 installateurs |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 22 tests |
| `python -m build` | PASS |
| `python scripts/verify_artifact.py dist/*.whl` | PASS |

## Résultats

- Tests Python exécutés par lots : 388 PASS.
- Couverture globale : 98 %.
- CDC v4.8.1 : 746 exigences, 551 tests.
- Roadmap v2 : 19 phases, 114 epics, 8 gates, 22 tests.
- Installateurs autonomes : 6 profils PASS.
- Migrations PostgreSQL : 25 migrations inchangées.
- Wheel/sdist : PASS.
- Assets rendering dans wheel : `bootstrap.min.css`, `openinfra-web.css`, `openinfra-web.js`.

## Non exécuté

- Docker Compose réel avec PostgreSQL live : non exécuté, Docker n'étant pas disponible dans cet environnement.
