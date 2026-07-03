# OpenInfra Python POO v0.17.2 — Rapport de validation

Date : 2026-07-03

## Synthèse

- Release : `0.17.2`
- Type : correctif CI / sécurité, sans nouveau jalon fonctionnel
- Baseline fonctionnelle : `0.17.0` — P04 / EPIC-0406 — Énergie et refroidissement fondation
- Bug corrigé : le smoke CI `security list-tokens` / `security revoke-token` utilisait un jeton `ipam:operator` non autorisé pour une opération d'administration sécurité
- Exigence ajoutée : contrôles sécurité bloquants sur `push` et pull request
- Compatibilité CI ajoutée : Python `3.13` et `3.14`, en plus de `3.11` et `3.12`
- Production : déploiement serveur natif, indépendant de Docker
- Docker : environnement de test/smoke facultatif uniquement
- Seuil officiel de couverture : `>= 98 %`
- Couverture mesurée : `98.10 %`
- Résultat global local : réussi, hors audit de vulnérabilités en ligne `pip-audit` bloqué par la résolution DNS locale

## Impact

Cette livraison ne poursuit pas le jalon suivant. Elle corrige uniquement la chaîne CI et les contrôles sécurité.

Aucune commande publique, aucun endpoint HTTP, aucune migration métier et aucun comportement DCIM/IPAM/SOT existant n'ont été supprimés.

## Corrections livrées

- Correction du smoke sécurité GitHub Actions :
  - le jeton `ipam:operator` reste utilisé pour `whoami` et les opérations IPAM autorisées ;
  - un jeton séparé `security:admin` est créé pour `security list-tokens` et `security revoke-token`.
- Ajout du job `blocking-security` dans `.github/workflows/ci.yml`.
- Extension de la matrice CI à Python `3.11`, `3.12`, `3.13` et `3.14`.
- Ajout d'un audit de vulnérabilités de dépendances via `pip-audit`.
- Ajout d'une analyse statique sécurité bloquante via `bandit`.
- Ajout de CodeQL avec les suites `security-extended` et `security-and-quality`.
- Ajout de `dependency-review-action` pour les pull requests.
- Ajout de `.github/dependabot.yml` pour `pip` et `github-actions`.
- Ajout de `scripts/security_gate.py` pour détecter les secrets committés et verrouiller les exigences de durcissement CI.
- Intégration de `scripts/security_gate.py` dans `scripts/quality_gate.py`.
- Ajout du runbook `docs/runbooks/SECURITY_CI.md`.
- Ajout des tests `tests/integration/test_security_gate.py`.
- Mise à jour version : `VERSION`, `pyproject.toml`, `src/openinfra/__init__.py`, `docs/api/openapi.yaml`, tests de version.
- Mise à jour documentation : `README.md`, `CHANGELOG.md`, `docs/runbooks/VALIDATION.md`, `docs/TRACEABILITY.md`.

## Fichiers principalement concernés

- `.github/workflows/ci.yml`
- `.github/dependabot.yml`
- `pyproject.toml`
- `VERSION`
- `src/openinfra/__init__.py`
- `scripts/security_gate.py`
- `scripts/quality_gate.py`
- `tests/integration/test_security_gate.py`
- `tests/integration/test_cli.py`
- `tests/integration/test_http_api.py`
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

Résultat : `0.17.2`.

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

Résultat : réussi. Aucune nouvelle migration métier n'est ajoutée en v0.17.2.

```bash
python3 scripts/native_runtime_smoke.py --project-root .
```

Résultat : réussi.

```bash
python3 -m build
python3 scripts/verify_artifact.py dist/*.whl
```

Résultat : réussi. Wheel générée : `openinfra-0.17.2-py3-none-any.whl`.

## Smoke RBAC sécurité exécuté

Scénario validé localement :

1. création d'un jeton `ipam:operator` pour `ci-client` ;
2. validation `whoami` sur ce jeton ;
3. création d'un jeton `security:admin` pour `ci-security-admin` ;
4. création d'un jeton `viewer` pour `ci-viewer` ;
5. exécution de `security list-tokens` avec le jeton `security:admin` ;
6. exécution de `security revoke-token` avec le jeton `security:admin`.

Résultat final : révocation réussie du jeton `viewer`.

## Audit vulnérabilités `pip-audit`

La commande suivante est intégrée dans GitHub Actions :

```bash
python -m pip_audit --strict --progress-spinner off
```

Exécution locale : non finalisée, car l'environnement local ne pouvait pas résoudre `pypi.org` pendant la requête d'audit. La dépendance `pip-audit` a bien été installée localement, mais la vérification en ligne a échoué sur la résolution DNS externe.

## Points non exécutés localement

- Matrice Python complète GitHub Actions `3.11`, `3.12`, `3.13`, `3.14` : seul Python `3.13.5` était disponible localement.
- CodeQL GitHub : non exécutable hors GitHub Actions.
- Dependency Review GitHub : non exécutable hors contexte pull request GitHub.
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

La livraison `0.17.2` corrige le bug CI RBAC signalé et ajoute une CI sécurité bloquante complète. Le prochain jalon roadmap peut reprendre uniquement après validation GitHub Actions sur la branche cible.
