# OpenInfra v0.29.5 — validation report

## Objet

Version corrective complète issue de v0.29.4. Cette livraison poursuit le traitement des dettes prioritaires P03/P04 avant reprise Discovery : le dossier `installers/` contient désormais des programmes d'installation autonomes par scope avec prérequis, déploiement de `src/`, virtualenv, requirements de production, migrations backend, rollback transactionnel et unités systemd effectives.

## Changements validés

- `installers/setup/**/install.py` conserve les points d'entrée par scope.
- Ajout des modes autonomes `--verify-only`, `--migrate-only` et `--rollback`.
- Ajout d'un plan de prérequis dans le dry-run JSON.
- Création de `/opt/openinfra/venv` en installation native.
- Installation des requirements de production par scope depuis `installers/requirements`.
- Installation du package OpenInfra local dans le virtualenv.
- Application des migrations backend via DSN résolu depuis `OPENINFRA_DATABASE_DSN`, `postgresql_dsn_ref`, ou `postgresql_user_ref` / `postgresql_password_ref`.
- Le DSN de migration est passé par variable d'environnement au processus enfant afin de ne pas exposer le secret dans les arguments CLI.
- Rollback automatique des fichiers et dossiers créés/remplacés en cas d'échec.
- Rollback manuel des sauvegardes `.openinfra-rollback` résiduelles.
- Démarrage effectif par `systemctl restart` après validation complète.
- `web` et `agent` restent exclus de PostgreSQL et des migrations.
- `enterprise/agent` reste sans FS/LVM applicatif et sans PostgreSQL.

## Validations exécutées

```bash
PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
bandit -q -r src/openinfra
PYTHONPATH=src:. python scripts/security_gate.py --project-root .
pip-audit --dry-run
PYTHONPATH=src:. python -m pytest
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .
python installers/setup/lite/install.py --dry-run --json
python installers/setup/pro/server/install.py --verify-only --json
python installers/setup/enterprise/agent/install.py --dry-run --json
python -m build
python scripts/verify_artifact.py dist/*.whl
```

## Résultats

- Ruff format : PASS.
- Ruff lint : PASS.
- Mypy : PASS, 39 modules.
- Bandit : PASS.
- Security gate : PASS.
- pip-audit dry-run : PASS, 512 packages audités en dry-run, aucune vulnérabilité connue.
- Pytest : PASS, 344 tests.
- Couverture globale : PASS, 98.03 % pour un seuil de 98 %.
- Quality gate : PASS.
- CLI version : PASS, 0.29.5.
- CDC v4.8.1 : PASS, 735 exigences, 543 tests.
- Installateurs : PASS, 6 profils.
- Enterprise alignment : PASS.
- Native runtime smoke : PASS.
- Migrations PostgreSQL : PASS, 23 migrations chargées et validées.
- YAML compose/openapi : PASS.
- Build wheel/sdist : PASS.
- verify_artifact : PASS.

## Non exécuté

Docker Compose réel avec PostgreSQL live n'a pas été exécuté : Docker n'est pas disponible dans l'environnement courant.

## Dette restante prioritaire

P05 reste prioritaire avant reprise Discovery : orchestration réelle LVM/PGDATA native avec détection OS complète, résolution/création du compte système PostgreSQL, création/montage FS et propriété interne.
