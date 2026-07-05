# OpenInfra v0.29.9

OpenInfra est une solution Python orientée objet pour référentiel d'infrastructure, IPAM/DDI, DCIM, inventaire, import/export, sécurité, éditions Lite/Pro/Enterprise et installateurs autonomes.

**Version courante : 0.29.9 — P06 PostgreSQL HA, synchronisation quasi temps réel PostgreSQL et sauvegardes PITR avant reprise Discovery.**

## v0.29.9 — Correctif runtime migration PostgreSQL P06

Cette livraison suspend P07 et corrige d'abord l'erreur runtime constatée sur `openinfra database apply-migrations` : la table partitionnée `postgresql_backup_runs` inclut désormais `started_at` dans sa clé primaire, comme l'exige PostgreSQL pour les contraintes uniques sur tables partitionnées. Le validateur de migrations bloque aussi toute régression équivalente.

Le socle P06 reste inchangé fonctionnellement : HA/PITR géré par les installateurs backend/all-in-one, sans alourdir les `install.ini` :

- `identity.peer_nodes` active automatiquement le mode cluster à synchronisation quasi temps réel pour les scopes `server` Pro/Enterprise ;
- aucun port PostgreSQL, paramètre Patroni ou secret de réplication n'est exposé dans `install.ini` ;
- le mode interne est `near-real-time-postgresql-streaming` ;
- le port de synchronisation applicative reste interne sur `2008` ;
- PostgreSQL conserve son port standard interne `5432` ;
- WAL archiving est préparé dans `/data/openinfra/pitr` ;
- les backups physiques sont préparés dans `/data/openinfra/backups` ;
- `synchronous_commit='local'` est rendu pour éviter un commit bloquant distant ; aucun `synchronous_standby_names` n'est généré par défaut ;
- le failover reste volontairement contrôlé opérateur, pas automatique et destructif.

Nouvelle commande :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database ha-plan \
  --path installers/setup/enterprise/server/install.ini \
  --edition enterprise \
  --scope server
```

## Installateurs autonomes

Les installateurs sont les points d'entrée d'installation réels :

```text
installers/setup/lite/install.py
installers/setup/pro/server/install.py
installers/setup/pro/web/install.py
installers/setup/enterprise/server/install.py
installers/setup/enterprise/web/install.py
installers/setup/enterprise/agent/install.py
```

Chaque installateur déploie son contenu autonome : `src/`, `pyproject.toml`, requirements de production par scope, unité systemd rendue et migrations backend quand le scope gère PostgreSQL.

## Validations principales

```bash
PYTHONPATH=src:. python -m pytest
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
python -m build
python scripts/verify_artifact.py dist/*.whl
```
