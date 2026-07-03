# CI sécurité bloquante OpenInfra

## Objectif

La CI OpenInfra doit bloquer un `push` ou une pull request lorsqu'une faiblesse sécurité détectable automatiquement est introduite dans le dépôt. Ces contrôles ne remplacent pas une revue sécurité humaine, mais ils constituent une barrière minimale obligatoire avant livraison.

## Contrôles actifs

- `bandit -q -r src/openinfra` : analyse statique sécurité du code Python applicatif.
- `python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off` : audit des dépendances installées contre les bases de vulnérabilités Python ; `requirements/security-audit.txt` évite d'auditer l'environnement editable et limite le contrôle aux dépendances tierces.
- `python scripts/security_gate.py --project-root .` : scan déterministe des secrets committés et vérification du durcissement GitHub Actions.
- CodeQL : analyse de sécurité et de qualité avec les suites `security-extended` et `security-and-quality`.
- Dependency Review : workflow séparé, déclenché uniquement sur pull request, pour bloquer les dépendances vulnérables introduites dans une PR sans créer de job `Skipped` sur les pushs.
- Dependabot : ouverture automatique de pull requests de mise à jour pour `pip` et `github-actions`.

## Matrice Python

La CI exécute la qualité et la sécurité sur Python `3.11`, `3.12`, `3.13` et `3.14`.

## Condition de blocage GitHub

Pour que ces contrôles soient bloquants au niveau GitHub, les règles de protection de branche du dépôt doivent déclarer les jobs suivants comme checks requis :

- `Quality / Python 3.11`
- `Quality / Python 3.12`
- `Quality / Python 3.13`
- `Quality / Python 3.14`
- `Blocking push vulnerability gate / Python 3.11`
- `Blocking push vulnerability gate / Python 3.12`
- `Blocking push vulnerability gate / Python 3.13`
- `Blocking push vulnerability gate / Python 3.14`
- `CodeQL security analysis`
- `Dependency review / PR vulnerability gate` pour les pull requests

## Correction RBAC du smoke sécurité

Les commandes `security list-tokens` et `security revoke-token` requièrent une permission d'administration sécurité. Le smoke CI utilise donc un jeton `security:admin` séparé du jeton `ipam:operator`.

```bash
openinfra security bootstrap-token --subject ci-security-admin --role security:admin --token "$security_admin_token"
openinfra security list-tokens --admin-token "$security_admin_token"
openinfra security revoke-token --target-token "$worker_token" --admin-token "$security_admin_token"
```

## Garde-fou pip-audit

La CI installe le projet avec `pip install -e .[postgresql,dev]`. Le package local `openinfra` ne doit pas être résolu sur PyPI pendant l’audit. Le job de sécurité utilise donc :

```bash
python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off
```

Le `security_gate.py` vérifie la présence de `pip_audit` et `requirements/security-audit.txt` dans le workflow pour éviter toute régression similaire.

## Séparation push / pull request

Le contrôle `Dependency review / PR vulnerability gate` ne doit pas être placé dans `.github/workflows/ci.yml`, car ce workflow se déclenche aussi sur `push`. Un job conditionné par `if: github.event_name == 'pull_request'` apparaîtrait alors comme `Skipped` dans les exécutions de push.

La séparation retenue est la suivante :

- `.github/workflows/ci.yml` : qualité, tests, `bandit`, `pip-audit`, `security_gate.py`, CodeQL et smoke runtime ; exécution sur `push`, pull request, tag `v*` et lancement manuel ;
- `.github/workflows/dependency-review.yml` : `actions/dependency-review-action`, exécution uniquement sur `pull_request`.

Le `security_gate.py` vérifie cette séparation et refuse toute réintroduction de `actions/dependency-review-action` ou de condition `if: github.event_name == 'pull_request'` dans le workflow de push.
