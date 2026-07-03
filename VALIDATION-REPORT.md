# OpenInfra Python POO v0.17.5 — Rapport de validation

## Synthèse

- Release : `0.17.5`
- Type : correctif CI / sécurité, sans nouveau jalon métier
- Baseline : `0.17.4`
- Roadmap : inchangée, dernier jalon fonctionnel conservé `P04 / EPIC-0406 — Énergie et refroidissement fondation`
- Objectif : corriger le statut GitHub Actions `Dependency review / PR vulnerability gate (push) Skipped` en séparant le workflow PR-only du workflow CI push.

## Analyse d'impact

Le workflow `.github/workflows/ci.yml` était déclenché sur `push` et contenait un job `dependency-review` protégé par `if: github.event_name == 'pull_request'`. Sur un push, GitHub Actions affichait donc ce job comme `Skipped`. Le contrôle était correct fonctionnellement pour les pull requests, mais polluait le résultat de push et pouvait perturber les règles de checks requis.

La correction sépare les responsabilités :

- `.github/workflows/ci.yml` : qualité, tests, sécurité bloquante sur push, CodeQL, smoke runtime ;
- `.github/workflows/dependency-review.yml` : Dependency Review déclenchée uniquement par `pull_request`.

Aucun comportement métier OpenInfra n'est modifié.

## Fichiers modifiés

- `.github/workflows/ci.yml`
- `.github/workflows/dependency-review.yml`
- `scripts/security_gate.py`
- `tests/integration/test_security_gate.py`
- `VERSION`
- `pyproject.toml`
- `src/openinfra/__init__.py`
- `docs/api/openapi.yaml`
- `README.md`
- `CHANGELOG.md`
- `docs/runbooks/SECURITY_CI.md`
- `docs/runbooks/VALIDATION.md`
- `docs/TRACEABILITY.md`
- `VALIDATION-REPORT.md`

## Corrections CI

- Suppression de `actions/dependency-review-action` du workflow de push `.github/workflows/ci.yml`.
- Suppression de tout job conditionné par `if: github.event_name == 'pull_request'` dans le workflow de push.
- Ajout du workflow `.github/workflows/dependency-review.yml`, déclenché uniquement par `pull_request`.
- Renommage explicite du job sécurité en `Blocking push vulnerability gate / Python ${{ matrix.python-version }}`.
- Conservation de la matrice Python `3.11`, `3.12`, `3.13`, `3.14`.
- Conservation des contrôles bloquants push : `bandit`, `pip-audit`, `security_gate.py`, CodeQL.

## Garde-fous ajoutés

`scripts/security_gate.py` vérifie désormais :

- présence du workflow PR dédié `.github/workflows/dependency-review.yml` ;
- présence de `actions/dependency-review-action` dans le workflow PR ;
- absence de `actions/dependency-review-action` dans `.github/workflows/ci.yml` ;
- absence de `if: github.event_name == 'pull_request'` dans `.github/workflows/ci.yml` ;
- absence de `push:` et `workflow_dispatch:` dans le workflow Dependency Review ;
- conservation de `pip-audit` via `requirements/security-audit.txt` ;
- conservation de Python `3.13` et `3.14` dans la matrice.

## Tests ajoutés

- `test_security_gate_rejects_dependency_review_in_push_workflow`
- `test_security_gate_rejects_push_trigger_on_dependency_review_workflow`

Ces tests empêchent la réintroduction d'un job PR-only dans le workflow de push.

## Validations exécutées

### Formatage

```bash
python3 -m ruff format --check src tests scripts docker
```

Résultat : réussi, `71 files already formatted`.

### Lint

```bash
python3 -m ruff check src tests scripts docker
```

Résultat : réussi, `All checks passed!`.

### Typage statique

```bash
python3 -m mypy src/openinfra
```

Résultat : réussi, `Success: no issues found in 29 source files`.

### Sécurité SAST

```bash
python3 -m bandit -q -r src/openinfra
```

Résultat : réussi.

### Gate sécurité interne

```bash
python3 scripts/security_gate.py --project-root .
```

Résultat : réussi.

### Audit dépendances — dry-run local

```bash
python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run
```

Résultat : réussi.

```text
INFO:pip_audit._audit:Dry run: would have audited 47 packages
No known vulnerabilities found
```

### Tests complets

```bash
PYTHONPATH=src python3 -m pytest
```

Résultat :

- `170 passed`
- couverture globale : `98.10 %`
- seuil obligatoire : `>= 98 %`

### Quality gate

```bash
PYTHONPATH=src python3 scripts/quality_gate.py
```

Résultat : réussi.

### Compilation

```bash
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
```

Résultat : réussi.

### CLI version

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
```

Résultat : `0.17.5`.

### Validation CDC/SFG/STG

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
```

Résultat :

```text
status=valid
version=4.0.0
requirements=488
tests=310
```

### Migrations PostgreSQL

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql
```

Résultat : réussi.

Toutes les migrations PostgreSQL `0001` à `0014` ont également été rendues avec succès.

### Smoke runtime natif

```bash
python3 scripts/native_runtime_smoke.py --project-root .
```

Résultat : réussi.

### Build et vérification artefact

```bash
python3 -m build
python3 scripts/verify_artifact.py dist/*.whl
```

Résultat : réussi.

```text
Successfully built openinfra-0.17.5.tar.gz and openinfra-0.17.5-py3-none-any.whl
```

## Non exécuté localement

- Exécution réelle GitHub Actions : non exécutable dans l'environnement local.
- Matrice GitHub complète Python `3.11`, `3.12`, `3.13`, `3.14` : seul Python `3.13.5` était disponible localement.
- CodeQL : exécutable uniquement dans GitHub Actions.
- Dependency Review Action : exécutable uniquement dans GitHub Actions sur événement `pull_request`.
- Audit réseau complet `pip-audit` : non exécuté localement ; le dry-run a validé l'entrée d'audit dédiée, l'audit réseau complet reste dans la CI.
- Docker Compose réel : non exécuté ; Docker n'est pas requis pour la production.
- PostgreSQL réel : non exécuté ; aucun serveur PostgreSQL local disponible.

## Résultat

La livraison `0.17.5` corrige le statut `Dependency review / PR vulnerability gate (push) Skipped`. Après push, le workflow CI ne contient plus de job PR-only susceptible d'être marqué `Skipped`. Le contrôle Dependency Review reste disponible et bloquant pour les pull requests via un workflow dédié.
