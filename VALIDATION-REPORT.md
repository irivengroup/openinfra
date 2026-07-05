# OpenInfra v0.29.11 — rapport de validation

## Objet de livraison

Correctif d'alignement P07/P08 après v0.29.10 :

- configuration runtime canonique matérialisée dans `/opt/openinfra/config/openinfra.conf` ;
- compatibilité opérateur via `/etc/openinfra/openinfra.conf`, avec `/etc/openinfra` comme lien symbolique vers `/opt/openinfra/config` ;
- verrou anti-réinstallation `/opt/openinfra/config/.openinfra-installed.lock` ;
- suppression de la dépendance runtime au dossier `installers/` après installation ;
- copie des migrations backend vers `/opt/openinfra/share/migrations/postgresql` ;
- backend strictement API-only pour les opérateurs humains ;
- authentification opérateur locale/LDAP/IPA portée par le frontend web Pro/Enterprise ;
- agents consommant l'API backend avec mécanisme technique d'enrôlement ;
- sécurisation maximale des flux frontend-backend, agent-backend et backend-backend par TLS 1.3 + mTLS hors Lite ;
- CDC v4.8.1, ADR, matrices et runbooks alignés.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers` | PASS |
| `python -m ruff format --check src tests scripts docker installers` | PASS |
| `python -m ruff check src tests scripts docker installers` | PASS |
| `python -m mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `pip-audit --dry-run` | PASS — aucune vulnérabilité connue détectée |
| `PYTHONPATH=src:. python -m pytest -q` | PASS |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.11 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_install_ini.py` | PASS |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS |
| `python -m build` | PASS |
| `python scripts/verify_artifact.py dist/*.whl` | PASS |

## Résultats chiffrés

- Version : `0.29.11`.
- Suite Python : 376 tests collectés et passés.
- Couverture globale : 98.00 %.
- CDC v4.8.1 : PASS — 742 exigences, 547 tests.
- Roadmap v2 : PASS — 19 phases, 114 epics, 8 gates, 20 tests.
- Installateurs autonomes : PASS — 6 profils.
- Migrations PostgreSQL : PASS — 25 migrations.
- Build wheel/sdist : PASS.

## Contrôles archive attendus

- `deploy/` absent.
- `migrations/` racine absent.
- anciens dossiers `installers/lite`, `installers/pro`, `installers/enterprise` absents.
- `installers/setup/**/install.py` présents pour les 6 installateurs autonomes.
- `installers/migrations/postgresql` présent comme source projet.
- runtime natif cible `/opt/openinfra/share/migrations/postgresql` après installation.
- caches et artefacts temporaires absents.
- `dist/` et `build/` exclus de l'archive source.

## Point non exécuté

Docker Compose réel avec PostgreSQL live n'a pas été exécuté dans cet environnement. Le smoke natif et les validations CLI/installateurs/migrations ont été exécutés.
