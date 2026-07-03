# CI sécurité bloquante OpenInfra

## Objectif

La CI OpenInfra doit bloquer un `push` ou une pull request lorsqu'une faiblesse sécurité détectable automatiquement est introduite dans le dépôt. Ces contrôles ne remplacent pas une revue sécurité humaine, mais ils constituent une barrière minimale obligatoire avant livraison.

## Contrôles actifs

- `bandit -q -r src/openinfra` : analyse statique sécurité du code Python applicatif.
- `python -m pip_audit --strict --progress-spinner off` : audit des dépendances installées contre les bases de vulnérabilités Python.
- `python scripts/security_gate.py --project-root .` : scan déterministe des secrets committés et vérification du durcissement GitHub Actions.
- CodeQL : analyse de sécurité et de qualité avec les suites `security-extended` et `security-and-quality`.
- Dependency Review : blocage des pull requests introduisant des dépendances vulnérables à sévérité au moins modérée.
- Dependabot : ouverture automatique de pull requests de mise à jour pour `pip` et `github-actions`.

## Matrice Python

La CI exécute la qualité et la sécurité sur Python `3.11`, `3.12`, `3.13` et `3.14`.

## Condition de blocage GitHub

Pour que ces contrôles soient bloquants au niveau GitHub, les règles de protection de branche du dépôt doivent déclarer les jobs suivants comme checks requis :

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

## Correction RBAC du smoke sécurité

Les commandes `security list-tokens` et `security revoke-token` requièrent une permission d'administration sécurité. Le smoke CI utilise donc un jeton `security:admin` séparé du jeton `ipam:operator`.

```bash
openinfra security bootstrap-token --subject ci-security-admin --role security:admin --token "$security_admin_token"
openinfra security list-tokens --admin-token "$security_admin_token"
openinfra security revoke-token --target-token "$worker_token" --admin-token "$security_admin_token"
```
