# OpenInfra v0.29.50 — rapport de validation

## Objet de livraison

OpenInfra v0.29.50 expose l'administration en lecture des éditions et quotas runtime dans l'API HTTP et dans le portail `openinfra-web`, sans déplacer ni dupliquer les règles métier hors de `EditionQueryService`.

## Changements fonctionnels

- Ajout de `GET /api/v1/editions/policies` pour publier le catalogue Lite/Pro/Enterprise.
- Ajout de `GET /api/v1/editions/feature-check` pour obtenir une décision de capacité d'édition.
- Ajout de `GET /api/v1/editions/quota-check` pour obtenir une décision de quota runtime tenant.
- Publication des endpoints dans le discovery document et dans `docs/api/openapi.yaml`.
- Protection des routes par `Permission.SECURITY_ADMIN` lorsque `auth_required=True`.
- Ajout des opérations web dans Sécurité/RBAC/Audit :
  - `Politiques éditions et quotas` ;
  - `Vérifier une capacité édition` ;
  - `Vérifier un quota édition`.
- Ajout d'un smoke CI CLI pour `openinfra edition list`, `feature-check` et `quota-check`.
- Alignement CDC `REQ-00793` / `TST-WEB-094`.
- Alignement roadmap `TST-P08-WEB-EDITION-ADMIN-QUOTAS`.
- Conservation des corrections UI v0.29.49 : badge édition dans le header principal, fuchsia très foncé, sans badge auth visible.

## Fichiers principaux modifiés

- `src/openinfra/interfaces/http_api.py`
- `docs/api/openapi.yaml`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.js`
- `web/src/main.jsx`
- `scripts/validate_frontend.py`
- `.github/workflows/ci.yml`
- `tests/integration/test_http_api.py`
- `tests/integration/test_openinfra_web.py`
- `README.md`
- `CHANGELOG.md`
- `docs/ui/OPENINFRA_WEB.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/runbooks/EDITIONS_FEATURE_GATES.md`
- `docs/TRACEABILITY.md`
- `compose.yaml`
- `.env.example`
- `web/package.json`
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/*`
- `docs/specifications/OpenInfra-Roadmap-Developpement-v2/*`

## Validations exécutées

| Validation | Résultat |
| --- | --- |
| `PYTHONPATH=src python -m compileall -q src tests scripts docker installers` | PASS |
| `PYTHONPATH=src python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — `0.29.50` |
| `PYTHONPATH=src python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS — 793 exigences, 519 entités |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 66 tests |
| `PYTHONPATH=src:. pytest --collect-only --no-cov -q` | PASS — 448 tests collectés |
| Tests unitaires + architecture en lot | PASS — 177 tests |
| Tests intégration en lots | PASS — 271 tests |
| Tests ciblés édition/API/web | PASS — 12 tests |
| Couverture reconstruite par lots + `coverage report --fail-under=98` | PASS — 98 % |
| `PYTHONPATH=src:. python scripts/quality_gate.py --project-root .` | PASS |
| `zip -T` CDC/Roadmap | PASS |

## Particularités de validation

- Le `pytest` monolithique sans découpage a été interrompu par le timeout de l'environnement après progression sans échec visible ; les mêmes 448 tests collectés ont donc été exécutés en lots.
- Un lancement ciblé sans `--no-cov` échoue normalement sur le seuil global de couverture, car il ne couvre qu'un sous-ensemble de tests. Les tests ciblés ont été relancés avec `--no-cov` et ont passé ; la couverture globale a été reconstruite par lots complets.

## Non exécuté localement

- `ruff`, `mypy`, `bandit`, `pip-audit` : binaires absents de l'environnement.
- `python -m build` : module Python `build` absent.
- `npm --prefix web run build` : échec attendu, `vite` absent car `web/node_modules` n'est pas installé.
- Docker Compose live : binaire `docker` absent.

## Risques résiduels

- Le build frontend Vite et le smoke Docker Compose doivent être rejoués dans l'environnement CI/outillage complet.
- Les validations statiques Ruff/Mypy/Bandit/Pip-audit doivent être rejouées dès disponibilité des binaires.
