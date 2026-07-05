# Volume V30 — Configuration installateur `install.ini`

## 1. Objectif

Ce volume définit le contrat minimal des fichiers `install.ini` OpenInfra. Les fichiers de configuration doivent rester succincts afin de ne pas exposer de paramètres permettant de contourner les éditions, quotas, services, chemins système, ports internes ou opérations de l’installateur.

Le type d’installation est porté par l’arborescence et le programme d’installation autonome, pas par le fichier `install.ini`.

## 2. Localisation canonique

Chaque scope dispose de son fichier local et de son programme autonome :

```text
installers/setup/lite/install.ini
installers/setup/lite/install.py
installers/setup/pro/server/install.ini
installers/setup/pro/server/install.py
installers/setup/pro/web/install.ini
installers/setup/pro/web/install.py
installers/setup/enterprise/server/install.ini
installers/setup/enterprise/server/install.py
installers/setup/enterprise/web/install.ini
installers/setup/enterprise/web/install.py
installers/setup/enterprise/agent/install.ini
installers/setup/enterprise/agent/install.py
```

Les anciens dossiers racine `installers/lite`, `installers/pro` et `installers/enterprise` sont interdits. Le dossier Enterprise conserve le nom canonique `enterprise`.

## 3. Sections autorisées

| Édition | Scope | Sections autorisées | Remarques |
|---|---|---|---|
| Lite | all-in-one | `storage` | installation monolithique locale : BDD, backend et frontend sur le même serveur |
| Pro | server | `storage`, `api`, `identity`, `auth` | backend avec PostgreSQL managé, migrations et service `openinfra.service` |
| Pro | web | `api`, `auth` | frontend sans PostgreSQL local ni migrations |
| Enterprise | server | `storage`, `api`, `identity`, `auth` | backend clusterisable, PostgreSQL managé ou cluster local, migrations |
| Enterprise | web | `api`, `auth` | frontend clusterisable sans PostgreSQL local ni migrations |
| Enterprise | agent | `api` | agent enrôlé via backend, sans BDD, sans migrations et sans FS/LVM applicatif |

## 4. Clés interdites

`install.ini` ne doit jamais exposer :

- `edition`, `scope`, `service` ;
- section `[operations]` ;
- ports internes back/front, back/agent ou peer-to-peer ;
- `central_endpoint` ;
- `mountpoint`, `owner`, `group`, `pgdata`, symlink ;
- chemins système canoniques ou paramètres de contournement des quotas.

## 5. Stockage

Pour les scopes qui gèrent PostgreSQL, la section `[storage]` expose uniquement :

```ini
[storage]
vgname = datavg
lvname = openinfradata_lv
lvsize = 100GB
```

`lvsize` est la taille maximale acceptée par édition :

- Lite : `2GB` ;
- Pro : `100GB` ;
- Enterprise : illimité côté contrôleur, dimensionnement selon sizing/licence.

L’installateur gère en interne le mountpoint `/data/openinfra/`, le symlink `/opt/openinfra/data -> /data/openinfra/`, le compte système PostgreSQL effectif, les owner/group, les permissions et PGDATA.

Le filesystem applicatif `/opt/openinfra/` est géré en interne pour `lite/all-in-one`, `pro/server`, `pro/web`, `enterprise/server` et `enterprise/web`. Le scope `enterprise/agent` est installé directement sous `/opt/openinfra/` sans création de FS/LVM applicatif.

## 6. API, identity et auth

`backend_endpoint` désigne l’endpoint backend ou la VIP en cas de cluster. Les ports par défaut sont internes à l’installateur : 2006 pour back/front, 2007 pour back/agent et 2008 pour la synchronisation inter-backends.

`peer_nodes` est autorisé uniquement pour les scopes backend clusterisables et ne contient ni protocole ni port.

Le mode d’authentification par défaut est `standard` pour l’application et la base. Les credentials PostgreSQL sont fournis par références sécurisées.

## 7. Installateurs autonomes

Chaque `install.py` est exécutable depuis son répertoire et doit supporter au minimum :

```bash
python install.py --dry-run --json
sudo python install.py --execute
python install.py --execute --target-root /tmp/openinfra-image --skip-service-enable
```

Tous les installateurs déploient `src/`, `pyproject.toml`, les requirements de production et l’unité systemd. Les scopes backend/all-in-one déploient aussi `installers/migrations/postgresql` et appliquent les migrations.

## 8. Critères d’acceptation

L’installation est acceptée si :

- chaque scope possède `install.ini` et `install.py` sous `installers/setup/...` ;
- aucun ancien dossier racine `installers/lite`, `installers/pro` ou `installers/enterprise` n’est livré ;
- le fichier `install.ini` est validé avant toute modification système ;
- les secrets sont uniquement référencés par `env:`, `vault://`, `sops://`, `file://` ou `kms://` ;
- les migrations backend proviennent uniquement de `installers/migrations/postgresql` ;
- les scopes `web` et `agent` ne déploient jamais PostgreSQL ni migrations ;
- l’agent Enterprise ne crée jamais de FS/LVM applicatif et n’accède jamais directement à PostgreSQL ;
- le dry-run affiche un plan complet sans modification système.
