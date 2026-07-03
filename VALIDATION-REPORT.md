# OpenInfra Python POO v0.17.6 — Rapport de validation

## Synthèse

- Release : `0.17.6`
- Baseline : `0.17.5`
- Type : correctif CI / sécurité / Python 3.13
- Roadmap : inchangée
- Dernier jalon fonctionnel conservé : P04 / EPIC-0406 — Énergie et refroidissement fondation
- Production : runtime serveur natif ; Docker reste facultatif pour lab/smoke uniquement

## Bug corrigé

Le smoke GitHub Actions échouait aléatoirement sur Python 3.13 pendant `openinfra security bootstrap-token` :

```text
openinfra security bootstrap-token: error: argument --token: expected one argument
```

Cause : `secrets.token_urlsafe(48)` peut générer une chaîne commençant par `-`. Dans une commande shell du type `--token "$token"`, `argparse` peut interpréter cette valeur comme une option au lieu de l'argument de `--token`.

## Corrections intégrées

- `.github/workflows/ci.yml` : tous les jetons générés dans les smoke tests CI sont préfixés par `ci_`.
- `TokenGenerator` : les nouveaux jetons API générés automatiquement par OpenInfra sont préfixés par `oi_`.
- `docker/openinfra-runtime-smoke.py` et `scripts/docker_environment.py` : jetons de lab/smoke préfixés par `oi_`.
- `scripts/security_gate.py` : rejet de la génération CI non préfixée `print(secrets.token_urlsafe(48))`.
- Tests ajoutés/modifiés : non-régression du gate CI et garantie que les jetons générés par OpenInfra ne commencent pas par `-`.

## Validations exécutées localement

```bash
python3 -m ruff format --check src tests scripts docker
```

Résultat : réussi.

```bash
python3 -m ruff check src tests scripts docker
```

Résultat : réussi.

```bash
python3 -m mypy src/openinfra
```

Résultat : réussi.

```bash
python3 -m bandit -q -r src/openinfra
```

Résultat : réussi.

```bash
PYTHONPATH=src python3 scripts/security_gate.py --project-root .
```

Résultat : réussi.

```bash
PYTHONPATH=src python3 -m pytest -q
```

Résultat :

- 171 tests réussis
- Couverture globale : 98.10 %
- Seuil obligatoire : >= 98 %

```bash
PYTHONPATH=src python3 scripts/quality_gate.py
```

Résultat : réussi.

```bash
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
```

Résultat : réussi.

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
```

Résultat : `0.17.6`.

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
```

Résultat : valide.

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql
```

Résultat : réussi.

Toutes les migrations PostgreSQL `0001` à `0014` ont également été rendues avec succès.

```bash
python3 scripts/native_runtime_smoke.py --project-root .
```

Résultat : réussi.

```bash
python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run --timeout 5
```

Résultat : réussi ; 47 paquets collectés, aucun package local `openinfra` audité comme dépendance PyPI.

```bash
python3 -m build
python3 scripts/verify_artifact.py dist/*.whl
```

Résultat : réussi ; wheel `openinfra-0.17.6-py3-none-any.whl` construit et vérifié.

## Contrôle de non-régression ciblé

Smoke reproduisant le bloc CI corrigé avec jetons préfixés `ci_` :

- `security bootstrap-token` admin : réussi
- `security bootstrap-token` worker : réussi
- `access create-rule` : réussi
- `access evaluate` : réussi
- aucun appel `--token` sans valeur détecté

## Non exécuté localement

- GitHub Actions réel sur matrice `3.11`, `3.12`, `3.13`, `3.14` : seul Python `3.13.5` est disponible localement.
- CodeQL et Dependency Review : exécutables uniquement côté GitHub Actions.
- Audit `pip-audit` réseau complet : impossible localement à cause d'une résolution DNS externe vers `pypi.org`; le dry-run et la configuration CI sont validés.
- Docker Compose réel : non exécuté ; Docker n'est pas requis en production.
- PostgreSQL réel : non exécuté ; aucun serveur PostgreSQL local disponible.

## Conclusion

La version `0.17.6` corrige le bug CI Python 3.13 lié aux jetons aléatoires commençant par `-`, ajoute des garde-fous de non-régression, conserve la couverture globale au-dessus de 98 %, et ne modifie aucun jalon fonctionnel métier.
