# OpenInfra v0.29.70 — Validation Report

Release: `0.29.70`

## Scope

Hotfix CI DevSecOps : correction des alertes Bandit B608 sur la persistance PostgreSQL, remise au format Ruff du test d’intégration web et réalignement mypy des retours DCIM/HTTP API. Aucun changement de contrat public API, CLI, migration ou UI n’est introduit.

## Changes validated

- Les listes DCIM PostgreSQL utilisent des requêtes SQL statiques pour les variantes `include_retired=True/False`.
- La liste des entités propriétaires ITAM utilise des requêtes SQL statiques pour les variantes avec ou sans retrait logique.
- Toutes les valeurs issues du domaine ou de l’utilisateur restent transmises via paramètres SQL nommés.
- Aucun `# nosec` supplémentaire n’a été ajouté.
- `tests/integration/test_openinfra_web.py` est conforme à `ruff format --check`.
- Les méthodes de mise à jour DCIM exposent des types de retour explicites.
- Les variables de réponse HTTP API susceptibles d’être confondues par `mypy` sont nommées par cas d’usage.

## Executed validations

| Validation | Result |
| --- | --- |
| `ruff format --check src tests scripts docker` | PASS — 135 fichiers conformes |
| `ruff check src tests scripts docker` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `mypy src/openinfra` | PASS — 54 fichiers source |
| `python -m compileall -q src tests scripts` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.70` |
| `PYTHONPATH=src python -m pytest tests/integration/test_openinfra_web.py -q --no-cov` | PASS — 13 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| Integration tests by file groups with `--no-cov` | PASS — 312 tests |
| Targeted regression tests after mypy/http_api fixes | PASS — 64 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 515 tests collected |
| Coverage par lots avec `--cov-append --cov-fail-under=0` | PASS — 515 tests exécutés |
| `python scripts/quality_gate.py` | PASS — couverture globale 98 % |
| `python -m build` | PASS — sdist + wheel générés localement |
| `zip -T /mnt/data/openinfra-python-0.29.70.zip` | PASS |
| `PYTHONPATH=src python scripts/verify_artifact.py /mnt/data/openinfra-python-0.29.70.zip` | PASS |

## Not completed in this runtime

- `pip-audit -r requirements/security-audit.txt` : non finalisé dans ce runtime, résolution DNS de `pypi.org` indisponible.
- Build Vite complet : dépendances frontend non installées localement.
- Docker Compose live : non exécuté dans ce runtime.
