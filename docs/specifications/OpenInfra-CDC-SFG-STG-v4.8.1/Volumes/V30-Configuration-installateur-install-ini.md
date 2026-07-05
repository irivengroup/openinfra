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
| Enterprise | agent | `api` | agent enrôlé via backend, FS applicatif `/opt/openinfra/` géré en interne, sans BDD, sans PGDATA et sans migrations |

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

Le filesystem applicatif `/opt/openinfra/` est géré en interne pour `lite/all-in-one`, `pro/server`, `pro/web`, `enterprise/server`, `enterprise/web` et `enterprise/agent`. Le scope `enterprise/agent` reste seulement exclu du FS PostgreSQL, de PGDATA, du symlink data et des migrations backend.

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
- l’agent Enterprise crée ou valide le FS/LVM applicatif CDC `/opt/openinfra/`, mais n’accède jamais directement à PostgreSQL ;
- le dry-run affiche un plan complet sans modification système.

## 9. Configuration runtime issue de `install.ini` et `.env`

`install.ini` est une entrée de bootstrap. Après installation, les paramètres utiles issus de `install.ini` et du fichier `.env` sont matérialisés dans `/opt/openinfra/config/openinfra.conf`. Le chemin `/etc/openinfra/openinfra.conf` est disponible parce que `/etc/openinfra` est un lien symbolique vers `/opt/openinfra/config`.

Les unités systemd utilisent `EnvironmentFile=/etc/openinfra/openinfra.conf`. Le fichier réel reste `/opt/openinfra/config/openinfra.conf`. Les services ne doivent pas dépendre de `installers/` après installation.

## 10. Section `[security]`

La section `[security]` est obligatoire. Lite impose :

```ini
[security]
transport = local
tls_min_version = TLSv1.3
mtls_required = false
loopback_only = true
```

Pro/Entreprise imposent :

```ini
[security]
transport = mtls
tls_min_version = TLSv1.3
mtls_required = true
server_ca_cert_ref = file:///opt/openinfra/config/trust/openinfra-ca.pem
client_cert_ref = file:///opt/openinfra/config/tls/<scope>.crt
client_key_ref = file:///opt/openinfra/config/tls/<scope>.key
loopback_only = false
```

Les valeurs `server_ca_cert_ref`, `client_cert_ref` et `client_key_ref` doivent être des références `file://`, `vault://`, `sops://` ou `kms://`. Aucun certificat, clé privée ou secret ne doit être stocké en clair dans `install.ini`.

## 11. Verrou anti-réinstallation

Le fichier `/opt/openinfra/config/.openinfra-installed.lock` doit être créé après installation réussie. Une nouvelle exécution `--execute` doit s'arrêter avant toute modification si ce verrou existe. Toute réinstallation contrôlée doit passer par une procédure de maintenance explicite avec sauvegarde et rollback.

## 12. Modèle backend API-only

Le backend ne doit pas authentifier directement chaque opérateur côté LDAP/IPA. LDAP/IPA est autorisé uniquement côté web Pro/Entreprise pour l'authentification opérateur. Le backend valide les jetons applicatifs, applique RBAC et audit, et sert les appels du frontend et des agents.
