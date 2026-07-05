## v0.29.10 — P07 authentification LDAP/IPA et RBAC groupes

- Lite reste strictement limité à l'authentification locale `standard`.
- Pro et Enterprise acceptent LDAP/IPA uniquement côté frontend/web pour l'authentification opérateur.
- Le backend ne réalise pas de login LDAP/IPA opérateur direct ; il valide des jetons applicatifs, applique RBAC et audit.
- Les secrets de bind LDAP/IPA restent des références `env:`, `vault://`, `sops://`, `file://` ou `kms://`.
- Les groupes externes sont mappés explicitement vers des rôles OpenInfra ; l'annuaire authentifie l'identité mais n'autorise jamais les actions applicatives.
- L'émission des tokens applicatifs est basée sur les rôles OpenInfra effectifs.
- Les connexions externes réussies sont auditées sans journaliser les mots de passe, DN utilisateur en clair dans les payloads publics ou secrets de bind.

# Installateurs autonomes OpenInfra

`installers/` est le point d’entrée opérationnel des installations OpenInfra. Il ne contient pas seulement la configuration : il embarque les programmes d’installation par scope, les migrations backend et les dépendances de production nécessaires à l’installation native.

## Arborescence canonique

```text
installers/
├── migrations/postgresql/*.sql
├── requirements/*.txt
└── setup/
    ├── lite/
    │   ├── install.ini
    │   └── install.py
    ├── pro/
    │   ├── server/
    │   │   ├── install.ini
    │   │   └── install.py
    │   └── web/
    │       ├── install.ini
    │       └── install.py
    └── enterprise/
        ├── server/
        │   ├── install.ini
        │   └── install.py
        ├── web/
        │   ├── install.ini
        │   └── install.py
        └── agent/
            ├── install.ini
            └── install.py
```

Les anciens chemins racine `installers/lite`, `installers/pro` et `installers/enterprise` sont interdits. Le dossier Enterprise conserve le nom canonique anglais `enterprise`.

## Matrice des scopes

| Édition | Scope | Sections `install.ini` | Service | FS applicatif interne | PostgreSQL | Migrations |
|---|---|---|---|---:|---:|---:|
| Lite | all-in-one | storage | openinfra.service | oui | oui | oui |
| Pro | server | storage, api, identity, auth | openinfra.service | oui | oui | oui |
| Pro | web | api, auth | openinfra-web.service | oui | non | non |
| Enterprise | server | storage, api, identity, auth | openinfra.service | oui | oui | oui |
| Enterprise | web | api, auth | openinfra-web.service | oui | non | non |
| Enterprise | agent | api | openinfra-agent.service | non | non | non |

## Exécution autonome

Chaque scope s’installe depuis son propre programme :

```bash
python installers/setup/lite/install.py --dry-run --json
python installers/setup/pro/server/install.py --dry-run --json
python installers/setup/enterprise/agent/install.py --dry-run --json
```

Pour une installation effective native :

```bash
sudo python installers/setup/pro/server/install.py --execute
```

`--target-root` permet de préparer une image offline sans écrire dans `/` :

```bash
python installers/setup/enterprise/server/install.py --execute --target-root /tmp/openinfra-image --skip-service-enable
```

## Règles de déploiement

Tous les programmes `install.py` déploient :

- `src/` vers `/opt/openinfra/src` ;
- `pyproject.toml` vers `/opt/openinfra/pyproject.toml` ;
- `installers/requirements` vers `/opt/openinfra/requirements` ;
- l’unité systemd adaptée sous `/etc/systemd/system` ;
- la configuration validée sous `/etc/openinfra/install-<edition>-<scope>.ini`.

Les scopes backend/all-in-one copient aussi `installers/migrations/postgresql` vers `/opt/openinfra/share/migrations/postgresql`, puis appliquent les migrations après bootstrap PostgreSQL. Les scopes `web` et `agent` ne copient pas les migrations et n’ont aucun accès direct à PostgreSQL.

## Règles `install.ini`

`install.ini` reste volontairement succinct. Il ne porte jamais `edition`, `scope`, `service`, section `[operations]`, ports internes, `mountpoint`, `owner`, `group` ou chemin PGDATA. Le type d’installation est déduit par l’installateur depuis l’arborescence `installers/setup/...`.

Règles stockage : seuls `vgname`, `lvname` et `lvsize` sont exposés pour le stockage PostgreSQL des scopes backend. Le filesystem applicatif `/opt/openinfra` est une politique interne de l’installateur pour `all-in-one`, `server`, `web` et `enterprise/agent`; il n’est pas configurable dans `install.ini`. Le scope `enterprise/agent` crée aussi le FS/LVM applicatif `/opt/openinfra` conformément au CDC, mais ne crée aucun FS/LVM PostgreSQL, aucun PGDATA, aucun symlink data et aucune migration backend.

## PostgreSQL backend

Pour les scopes `lite/all-in-one`, `pro/server` et `enterprise/server`, l’installateur gère PostgreSQL en interne : détection de la famille Linux via `/etc/os-release`, choix de `dnf`, `apt-get` ou `zypper`, installation si `psql` est absent, activation/démarrage de `postgresql.service`, vérification `pg_isready`, initialisation PGDATA sous `/data/openinfra/`, puis application des migrations depuis `/opt/openinfra/share/migrations/postgresql`.


## Moteur transactionnel v0.29.5

Les programmes `install.py` ne sont pas de simples validateurs. En mode `--execute`, ils réalisent une installation transactionnelle :

- validation stricte de `install.ini`;
- vérification des prérequis locaux (`python3`, `systemctl` en installation native, gestionnaire de paquets PostgreSQL pour backend/all-in-one);
- copie de `src/`, `pyproject.toml`, `installers/requirements` et, pour backend/all-in-one, des migrations vers `/opt/openinfra/share/migrations/postgresql`;
- création de `/opt/openinfra/venv`;
- installation des dépendances de production du scope;
- installation du package applicatif OpenInfra dans le virtualenv;
- rendu de l'unité systemd adaptée;
- bootstrap PostgreSQL si nécessaire pour `lite/all-in-one`, `pro/server` et `enterprise/server`;
- application des migrations backend avec DSN résolu depuis `OPENINFRA_DATABASE_DSN`, `OPENINFRA_DATABASE_DSN_REF` ou les références `OPENINFRA_POSTGRES_USER_REF` / `OPENINFRA_POSTGRES_PASSWORD_REF` matérialisées dans `/opt/openinfra/config/openinfra.conf`;
- `systemctl daemon-reload`, `enable` et `restart` du service OpenInfra en installation native.

Toute erreur après écriture déclenche un rollback automatique des fichiers et dossiers remplacés ou créés par l'installateur courant. Le mode manuel `--rollback` restaure également les sauvegardes `.openinfra-rollback` résiduelles d'une installation interrompue brutalement.

Modes disponibles :

```bash
python installers/setup/pro/server/install.py --dry-run --json
python installers/setup/pro/server/install.py --verify-only --json
sudo OPENINFRA_DATABASE_DSN='postgresql://openinfra:***@127.0.0.1:5432/openinfra' \
  python installers/setup/pro/server/install.py --execute
sudo python installers/setup/pro/server/install.py --rollback
```

`--migrate-only` est réservé aux scopes backend/all-in-one et refuse les scopes `web` ou `agent`.

## Validations

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer render-systemd --edition enterprise --scope agent
```

## PostgreSQL HA/PITR v0.29.10

Les scopes `lite/all-in-one`, `pro/server` et `enterprise/server` produisent désormais un plan PostgreSQL HA/PITR interne. Le fichier `install.ini` ne doit pas contenir de paramètres PostgreSQL bas niveau. Pour les scopes `server`, la présence de `identity.peer_nodes` active le mode cluster à synchronisation quasi temps réel.

Contrôle du plan :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database ha-plan \
  --path installers/setup/enterprise/server/install.ini \
  --edition enterprise \
  --scope server
```

Artefacts rendus en exécution réelle :

- `/opt/openinfra/config/postgresql-ha.json` ;
- `/data/openinfra/conf.d/openinfra-ha.conf` ;
- `/data/openinfra/pitr` ;
- `/data/openinfra/backups`.

Le failover est volontairement manuel et auditable. L'installateur prépare les primitives nécessaires, mais ne promeut jamais un standby automatiquement.
