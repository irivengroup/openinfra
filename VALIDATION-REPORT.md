# OpenInfra v0.29.7 — validation report

Version complète issue de v0.29.6. Cette livraison traite P06 avant reprise Discovery : PostgreSQL HA/PITR, réplication quasi synchrone dérivée de `identity.peer_nodes`, sauvegardes physiques, archive WAL, migration de registre HA et commande d'audit `database ha-plan`.

## Synthèse

- Version CLI : `0.29.7`.
- Tests automatisés : 345 tests PASS.
- Couverture globale : 98.01 %, seuil `>=98 %` PASS.
- CDC actif : `OpenInfra-CDC-SFG-STG-v4.8.1`.
- Roadmap active : `OpenInfra-Roadmap-Developpement-v2`.
- Installateurs : 6 profils autonomes PASS.
- Migrations PostgreSQL : 24 migrations, source unique `installers/migrations/postgresql`.
- Docker Compose réel avec PostgreSQL live : non exécuté, Docker indisponible dans cet environnement.

## Changements validés

- `InstallerPostgreSQLHaPlan` ajouté au validateur installateur.
- Mode interne `native-postgresql-streaming`.
- Topologie `quasi-synchronous-cluster` activée lorsque `identity.peer_nodes` est renseigné.
- Topologie `standalone-managed` conservée pour Lite et serveurs sans peers.
- Rendu interne :
  - `/etc/openinfra/postgresql-ha.json` ;
  - `/data/openinfra/conf.d/openinfra-ha.conf` ;
  - `/data/openinfra/pitr` ;
  - `/data/openinfra/backups`.
- Paramètres PostgreSQL rendus : WAL archiving, `hot_standby`, slots, `synchronous_commit=remote_apply`, `synchronous_standby_names='ANY 1 (...)'` si cluster.
- Failover automatique destructif interdit : promotion opérateur contrôlée et auditable.
- Migration `0024_postgresql_ha_backup_registry.sql` ajoutée.
- CLI `openinfra database ha-plan` ajoutée.

## Validations exécutées

```bash
python -m compileall -q src tests scripts docker installers
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
bandit -q -r src/openinfra
PYTHONPATH=src:. python scripts/security_gate.py --project-root .
pip-audit --dry-run
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .
PYTHONPATH=src python -m openinfra.interfaces.cli database ha-plan --path installers/setup/enterprise/server/install.ini --edition enterprise --scope server
python installers/setup/lite/install.py --dry-run --json
python installers/setup/enterprise/agent/install.py --dry-run --json
python -m build
python scripts/verify_artifact.py dist/*.whl
```

## Résultats

```text
ruff format --check : PASS
ruff check : PASS
mypy : PASS
bandit : PASS
security_gate.py : PASS
pip-audit --dry-run : PASS — 512 packages audités en dry-run
pytest : PASS — 345 tests
coverage : PASS — 98.01 %
quality_gate.py : PASS
CLI version : PASS — 0.29.7
spec validate CDC v4.8.1 : PASS — 735 exigences, 543 tests
installer validate : PASS — 6 profils
installer dry-run : PASS — 6 profils
validate_autonomous_installer.py : PASS
validate_enterprise_alignment.py : PASS
native_runtime_smoke.py : PASS
compose.yaml : YAML valide
OpenAPI YAML : YAML valide
build wheel/sdist : PASS
verify_artifact.py : PASS
```

## Contrôles d'archive

```text
deploy/ absent : PASS
migrations/ racine absent : PASS
anciens dossiers installers/lite, installers/pro, installers/enterprise absents : PASS
installers/setup canonical : PASS
installers/migrations/postgresql : PASS — 24 migrations
caches/artefacts temporaires absents : PASS
```

## Limite d'exécution

Docker Compose réel avec PostgreSQL live n'a pas été exécuté dans cet environnement, car Docker n'est pas disponible. Les tests applicatifs, installateurs, migrations rendues, OpenAPI, Compose YAML, build et quality gates ont été exécutés localement.
