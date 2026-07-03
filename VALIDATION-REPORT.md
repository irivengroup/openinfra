# OpenInfra Python POO v0.17.4 — Rapport de validation

## Synthèse

- Release : `0.17.4`
- Type : correctif CI sécurité / audit vulnérabilités
- Baseline fonctionnelle : `0.17.0` — P04 / EPIC-0406 — Énergie et refroidissement fondation
- Nouveau jalon métier : aucun
- Exigence production : runtime serveur natif, sans dépendance Docker
- Seuil couverture obligatoire : `>= 98 %`
- Couverture mesurée : `98.10 %`

## Bug corrigé

Le job GitHub Actions échouait avec :

```bash
python -m pip_audit --strict --skip-editable --progress-spinner off
ERROR:pip_audit._cli:openinfra: distribution marked as editable
```

Cause : le job installait le projet avec `pip install -e '.[postgresql,dev]'`, puis lançait `pip-audit` sur l'environnement Python complet. Avec `--strict`, la distribution projet installée en editable restait un cas bloquant.

Correction : le job sécurité n'audite plus l'environnement complet. Il audite un fichier explicite de dépendances tierces :

```bash
python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off
```

## Fichiers modifiés ou ajoutés

- `.github/workflows/ci.yml`
  - Remplacement de l'audit d'environnement par l'audit `requirements/security-audit.txt`.
- `requirements/security-audit.txt`
  - Nouvelle entrée d'audit dédiée aux dépendances tierces.
- `scripts/security_gate.py`
  - Vérification de la présence du fichier d'audit.
  - Rejet d'un workflow qui revient à l'audit d'environnement editable.
  - Rejet d'un fichier d'audit qui référence le package projet local.
- `tests/integration/test_security_gate.py`
  - Tests de non-régression sur l'audit par fichier de dépendances.
  - Test de rejet du retour à `pip-audit` sur environnement editable.
  - Test de rejet d'une référence au package local dans l'entrée d'audit.
- `VERSION`, `pyproject.toml`, `src/openinfra/__init__.py`, `docs/api/openapi.yaml`
  - Version mise à jour en `0.17.4`.
- `README.md`, `CHANGELOG.md`, `docs/TRACEABILITY.md`, `docs/runbooks/SECURITY_CI.md`, `docs/runbooks/VALIDATION.md`
  - Documentation corrective mise à jour.

## Validations exécutées

### Format Ruff

```bash
python3 -m ruff format --check src tests scripts docker
```

Résultat : réussi, `71 files already formatted`.

### Lint Ruff

```bash
python3 -m ruff check src tests scripts docker
```

Résultat : réussi.

### Typage statique

```bash
python3 -m mypy src/openinfra
```

Résultat : réussi, `Success: no issues found in 29 source files`.

### Scan sécurité Bandit

```bash
python3 -m bandit -q -r src/openinfra
```

Résultat : réussi.

### Gate sécurité interne

```bash
PYTHONPATH=. python3 scripts/security_gate.py --project-root .
```

Résultat : réussi.

### Pip audit — collecte locale sans réseau

```bash
python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run
```

Résultat : réussi, `Dry run: would have audited 47 packages`.

### Tests automatisés et couverture

```bash
PYTHONPATH=src python3 -m pytest -q
```

Résultat :

- `168 passed`
- couverture globale : `98.10 %`
- seuil obligatoire : `>= 98 %`

### Quality gate

```bash
PYTHONPATH=src python3 scripts/quality_gate.py
```

Résultat : réussi, `168 passed`, couverture `98.10 %`.

### Compilation Python

```bash
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
```

Résultat : réussi.

### CLI version

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
```

Résultat : `0.17.4`.

### Validation CDC/SFG/STG

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
```

Résultat :

- `status=valid`
- `version=4.0.0`
- `requirements=488`
- `tests=310`

### Migrations PostgreSQL

```bash
for f in migrations/postgresql/*.sql; do
  n="$(basename "$f" .sql)"
  PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name "$n" --root migrations/postgresql >/tmp/openinfra-${n}.sql
done
```

Résultat : migrations `0001` à `0014` rendues avec succès.

Validation ciblée demandée :

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql
```

Résultat : réussi.

### Smoke runtime natif

```bash
python3 scripts/native_runtime_smoke.py
```

Résultat : réussi.

### Build packaging

```bash
python3 -m build --no-isolation
python3 scripts/verify_artifact.py dist/*.whl
```

Résultat : réussi, wheel générée `openinfra-0.17.4-py3-none-any.whl`.

## Validations non exécutées localement

- Audit complet `pip-audit` réseau : non exécutable localement à cause d'une résolution DNS impossible vers `pypi.org`. Le `--dry-run` prouve que la collecte utilise bien `requirements/security-audit.txt` et n'inclut plus le package editable local.
- Matrice GitHub complète Python `3.11`, `3.12`, `3.13`, `3.14` : seul Python `3.13.5` était disponible localement.
- CodeQL et Dependency Review : exécutables uniquement dans GitHub Actions.
- Docker Compose réel : non exécuté ; Docker n'est pas requis pour la production.
- PostgreSQL réel : non exécuté ; aucun serveur PostgreSQL local disponible.

## Contrôle archive

L'archive source livrée exclut :

- `__pycache__`
- `.pytest_cache`
- `.mypy_cache`
- `.ruff_cache`
- `build`
- `dist`
- `*.egg-info`

## Conclusion

La livraison `0.17.4` corrige l'échec CI `distribution marked as editable` et ajoute des garde-fous contre les régressions similaires. Le prochain jalon roadmap peut reprendre après validation GitHub Actions sur la branche cible.
