# OpenInfra v0.29.13 — rapport de validation

## Objet de livraison

P08 livré côté code et runtime après v0.29.11 :

- ajout du service `openinfra-web` servant l'interface frontend et proxyfiant `/api/*` vers le backend ;
- intégration réelle de `openinfra-web` dans `compose.yaml`, `.env.example`, `scripts/docker_environment.py` et le smoke Docker ;
- frontend React/Bootstrap 5 sous `web/` et assets runtime embarqués sous `src/openinfra/interfaces/rendering/static` ;
- backend conservé strictement API-only : pas de login opérateur LDAP/IPA direct côté backend ;
- navigateur limité à un modèle same-origin `/api`, sans DSN PostgreSQL, secret LDAP/IPA, clé privée ou jeton agent ;
- runtime natif aligné : `openinfra-web.service` lancé par `/opt/openinfra/venv/bin/openinfra-web` et configuration issue de `/opt/openinfra/config/openinfra.conf` accessible via `/etc/openinfra/openinfra.conf` ;
- tests de proxy, configuration frontend, non-exposition des secrets, Docker Compose et installateur ajoutés.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers` | PASS |
| `PYTHONPATH=src:. python -m ruff format --check src tests scripts docker installers` | PASS |
| `PYTHONPATH=src:. python -m ruff check src tests scripts docker installers` | PASS |
| `PYTHONPATH=src:. python -m mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `pip-audit --dry-run` | PASS — aucune vulnérabilité connue détectée |
| `PYTHONPATH=src:. python -m pytest -q --no-cov` | PASS |
| `python -m coverage report --fail-under=98` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.13 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS |
| `python -m build` | PASS |
| `python scripts/verify_artifact.py dist/*.whl` | PASS |

## Résultats chiffrés

- Version : `0.29.13`.
- Suite Python : 383 tests collectés et passés.
- Couverture globale : 98.00 %.
- CDC v4.8.1 : PASS — 742 exigences, 547 tests.
- Roadmap v2 : PASS — 19 phases, 114 epics, 8 gates, 20 tests.
- Installateurs autonomes : PASS — 6 profils.
- Migrations PostgreSQL : PASS — 25 migrations.
- Frontend contract : PASS — React, ReactDOM, Bootstrap 5, assets runtime et service Compose validés.
- Build wheel/sdist : PASS.

## Contrôles archive attendus

- `deploy/` absent.
- `migrations/` racine absent.
- anciens dossiers `installers/lite`, `installers/pro`, `installers/enterprise` absents.
- `installers/setup/**/install.py` présents pour les 6 installateurs autonomes.
- `installers/migrations/postgresql` présent comme source projet.
- runtime natif cible `/opt/openinfra/share/migrations/postgresql` après installation.
- `openinfra-web` déclaré dans Docker Compose et dans le packaging Python.
- caches et artefacts temporaires absents.
- `dist/` et `build/` exclus de l'archive source.

## Point non exécuté

Docker Compose réel avec PostgreSQL live n'a pas été exécuté dans cet environnement. Les tests contractuels Compose, le smoke natif, les validations CLI/installateurs/migrations et le smoke web par tests automatisés ont été exécutés.
