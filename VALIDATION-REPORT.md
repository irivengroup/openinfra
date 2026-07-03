# OpenInfra Python POO v0.17.3 — Rapport de validation

Date : 2026-07-03

## Synthèse

- Release : `0.17.3`
- Type : correctif CI / sécurité / runtime PostgreSQL, sans nouveau jalon fonctionnel
- Baseline fonctionnelle : `0.17.0` — P04 / EPIC-0406 — Énergie et refroidissement fondation
- Bug corrigé : `pip-audit` échouait en CI car le package local editable `openinfra` n'est pas publié sur PyPI
- Bug corrigé : `PostgreSQLDriver.connect()` laissait fuiter une exception `psycopg.OperationalError` lors d'un échec DNS/connexion
- Production : déploiement serveur natif, indépendant de Docker
- Docker : environnement de test/smoke facultatif uniquement
- Seuil officiel de couverture : `>= 98 %`
- Couverture mesurée : `98.10 %`
- Résultat global local : réussi

## Impact

Cette livraison ne poursuit pas le jalon suivant. Elle corrige uniquement la chaîne CI sécurité et le contrat d'erreur PostgreSQL runtime.

Aucune commande publique, aucun endpoint HTTP, aucune migration métier et aucun comportement DCIM/IPAM/SOT existant n'ont été supprimés.

## Corrections livrées

- `.github/workflows/ci.yml` : remplacement de `python -m pip_audit --strict --progress-spinner off` par `python -m pip_audit --strict --skip-editable --progress-spinner off`.
- `scripts/security_gate.py` : le gate CI vérifie désormais que `pip_audit` et `--skip-editable` sont présents dans le workflow.
- `tests/integration/test_security_gate.py` : ajout de la couverture de non-régression sur `--skip-editable`.
- `src/openinfra/infrastructure/postgresql.py` : encapsulation des exceptions de connexion `psycopg` en `OpenInfraError`.
- Documentation mise à jour : README, changelog, validation, sécurité CI et traçabilité.
- Version mise à jour : `VERSION`, `pyproject.toml`, `src/openinfra/__init__.py`, OpenAPI et tests de version.

## Fichiers principalement concernés

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `VERSION`
- `src/openinfra/__init__.py`
- `src/openinfra/infrastructure/postgresql.py`
- `scripts/security_gate.py`
- `tests/integration/test_security_gate.py`
- `tests/integration/test_cli.py`
- `tests/integration/test_http_api.py`
- `docs/api/openapi.yaml`
- `docs/runbooks/SECURITY_CI.md`
- `docs/runbooks/VALIDATION.md`
- `docs/TRACEABILITY.md`
- `README.md`
- `CHANGELOG.md`
- `VALIDATION-REPORT.md`

## Validations exécutées localement

```bash
python3 -m ruff format --check src tests scripts docker
```

Résultat : réussi, `71 files already formatted`.

```bash
python3 -m ruff check src tests scripts docker
```

Résultat : réussi.

```bash
python3 -m mypy src/openinfra
```

Résultat : réussi, `Success: no issues found in 29 source files`.

```bash
python3 -m bandit -q -r src/openinfra
```

Résultat : réussi.

```bash
python3 scripts/security_gate.py --project-root .
```

Résultat : réussi.

```bash
python3 -m pip_audit --strict --skip-editable --progress-spinner off --dry-run
```

Résultat : réussi ; collecte validée, `would have audited 511 packages`.

Note : le mode `--dry-run` a été utilisé localement pour éviter une dépendance au réseau externe dans cet environnement. La CI GitHub exécute le même audit sans `--dry-run`.

```bash
PYTHONPATH=src python3 -m pytest -q
```

Résultat :

- `166 passed`
- couverture globale : `98.10 %`
- seuil obligatoire : `>= 98 %`

```bash
PYTHONPATH=src python3 scripts/quality_gate.py
```

Résultat : réussi, avec `166 passed` et couverture `98.10 %`.

```bash
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
```

Résultat : réussi.

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
```

Résultat : `0.17.3`.

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
```

Résultat :

- `status=valid`
- `version=4.0.0`
- `requirements=488`
- `tests=310`

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql
```

Résultat : réussi. Aucune nouvelle migration métier n'est ajoutée en v0.17.3.

```bash
python3 scripts/native_runtime_smoke.py --project-root .
```

Résultat : réussi.

```bash
python3 -m build
python3 scripts/verify_artifact.py dist/*.whl
```

Résultat : réussi. Wheel générée : `openinfra-0.17.3-py3-none-any.whl`.

## Points non exécutés localement

- Matrice Python complète GitHub Actions `3.11`, `3.12`, `3.13`, `3.14` : seul Python `3.13.5` était disponible localement.
- CodeQL GitHub : non exécutable hors GitHub Actions.
- Dependency Review GitHub : non exécutable hors contexte pull request GitHub.
- Audit `pip-audit` réseau complet : non exécuté localement ; la collecte a été validée en `--dry-run`, l'audit complet reste exécuté dans GitHub Actions.
- Docker Compose réel : non exécuté, Docker n'est pas requis pour la production.
- PostgreSQL réel : non exécuté, aucun serveur PostgreSQL local disponible.

## Condition pour rendre les checks réellement bloquants dans GitHub

Le workflow contient les jobs bloquants. Pour empêcher un merge malgré échec CI, configurer les règles de protection de branche GitHub avec les checks requis suivants :

- `Quality / Python 3.11`
- `Quality / Python 3.12`
- `Quality / Python 3.13`
- `Quality / Python 3.14`
- `Blocking security checks / Python 3.11`
- `Blocking security checks / Python 3.12`
- `Blocking security checks / Python 3.13`
- `Blocking security checks / Python 3.14`
- `CodeQL security analysis`
- `Dependency review / PR vulnerability gate` pour les pull requests

## Conclusion

La livraison `0.17.3` corrige les bugs CI signalés et tout le même type de régression locale identifiable : audit d'un package editable non publié, absence de garde-fou CI sur ce point, et fuite d'exception tierce PostgreSQL hors contrat OpenInfra. Le prochain jalon roadmap peut reprendre uniquement après validation GitHub Actions sur la branche cible.
