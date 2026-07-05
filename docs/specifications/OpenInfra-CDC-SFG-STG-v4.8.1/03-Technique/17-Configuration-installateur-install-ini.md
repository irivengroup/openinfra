# Configuration technique — `install.ini`

## Contrat technique révisé

Le fichier `install.ini` est volontairement succinct. Il ne doit pas exposer les champs permettant de piloter ou contourner une édition, un scope, un nom de service, des quotas, des ports internes, des opérations d'installation ou des chemins système canoniques. Ces décisions sont déduites par l'installateur depuis l'arborescence `installers/setup/...` et depuis la politique interne de l'édition.

Les clés inconnues sont rejetées. Les secrets ne sont jamais stockés en clair et doivent être fournis par référence `env:`, `vault://`, `sops://`, `file://` ou `kms://`.

## Règles par édition et scope

### Lite — `installers/setup/lite/install.ini`

Lite est une installation monolithique locale : base PostgreSQL, backend et frontend sur le même serveur.

Le fichier ne contient que :

```ini
[storage]
vgname = datavg
lvname = openinfradata_lv
lvsize = 2GB
```

Règles internes : session locale applicative avec base locale uniquement, aucun LDAP/IPA, aucune configuration réseau, aucune section API, aucun multisite, aucun clustering, aucune section `identity`.

### Pro / Entreprise — scope `server`

Le backend gère la base PostgreSQL locale ou clusterisée. Lorsque PostgreSQL est absent sur un backend local, l'installateur le déploie automatiquement selon la famille Linux détectée, active `postgresql.service`, vérifie la disponibilité, initialise PGDATA sous `/data/openinfra/`, puis applique les migrations backend depuis `installers/migrations/postgresql` avant activation du service.

Sections autorisées :

```ini
[storage]
vgname = datavg
lvname = openinfradata_lv
lvsize = 100GB

[api]
backend_endpoint = https://backend.example.com

[identity]
peer_nodes = backend02.example.com,backend03.example.com

[auth]
mode = standard
postgresql_user_ref = env:OPENINFRA_POSTGRES_USER
postgresql_password_ref = env:OPENINFRA_POSTGRES_PASSWORD
```

`backend_endpoint` désigne l'endpoint backend exposé. En cluster, il désigne la VIP. Les ports de communication back/front, back/agent et inter-nœuds ne sont pas exposés dans `install.ini`; les ports internes par défaut sont respectivement 2006, 2007 et 2008. `peer_nodes` est utilisé uniquement lorsque le backend est clusterisé et ne doit contenir ni protocole ni port.

### Pro / Entreprise — scope `web`

Le scope web ne déploie pas PostgreSQL et ne contient aucune section de stockage PostgreSQL. Il conserve toutefois le filesystem applicatif `/opt/openinfra/` géré en interne par l’installateur, sans exposition dans `install.ini`.

Sections autorisées :

```ini
[api]
backend_endpoint = https://backend.example.com

[auth]
mode = standard
postgresql_dsn_ref = env:OPENINFRA_POSTGRES_DSN
postgresql_user_ref = env:OPENINFRA_POSTGRES_USER
postgresql_password_ref = env:OPENINFRA_POSTGRES_PASSWORD
```

### Entreprise — scope `agent`

L'agent s'enregistre auprès du backend via le portail web et transmet ensuite ses observations au backend avec son jeton/certificat d'enrôlement. Il n'a jamais d'accès direct à PostgreSQL. Il dispose du filesystem LVM applicatif `/opt/openinfra/` géré en interne par l'installateur, mais ne crée aucun filesystem PostgreSQL, aucun PGDATA, aucun symlink `/opt/openinfra/data` et aucune migration backend.

Section autorisée unique :

```ini
[api]
backend_endpoint = https://backend.example.com
enrollment_token_ref = env:OPENINFRA_AGENT_ENROLLMENT_TOKEN
```

## Stockage applicatif et PostgreSQL

Le filesystem applicatif `/opt/openinfra/` est géré par l’installateur pour les scopes applicatifs `lite/all-in-one`, `pro/server`, `pro/web`, `enterprise/server` et `enterprise/web`. Cette disposition est interne, non configurable dans `install.ini`, et permet de conserver une séparation enterprise des binaires, configurations applicatives, permissions et quotas filesystem.

Le scope `enterprise/agent` n'est pas une exception pour le LV applicatif : `/opt/openinfra/` est géré comme pour les autres scopes. Il reste seulement exclu de PostgreSQL, PGDATA, symlink data et migrations backend.

Pour le stockage PostgreSQL des scopes backend, seuls `vgname`, `lvname` et `lvsize` sont exposés. L'installateur gère en interne le déploiement PostgreSQL si absent, le mountpoint `/data/openinfra/`, le symlink `/opt/openinfra/data -> /data/openinfra/`, les owner/group, les permissions, la résolution du compte système PostgreSQL et l'adaptation PGDATA.

Limites de taille exposées :

- Lite : `lvsize <= 2GB` ;
- Pro : `lvsize <= 100GB` ;
- Entreprise : pas de limite applicative imposée par le contrôleur, dimensionnement selon sizing/licence.

## Systemd

Le dossier `deploy/` n'est pas une source de vérité. Les unités `openinfra.service`, `openinfra-web.service` et `openinfra-agent.service` sont rendues par l'installateur selon l'édition et le scope. L'exécution des migrations relève de l'étape d'installation backend, pas d'un `ExecStartPre` systemd.

## Installateurs autonomes et source unique des migrations

`installers/` embarque les programmes autonomes par scope : `installers/setup/lite/install.py`, `installers/setup/pro/server/install.py`, `installers/setup/pro/web/install.py`, `installers/setup/enterprise/server/install.py`, `installers/setup/enterprise/web/install.py` et `installers/setup/enterprise/agent/install.py`. Chaque programme déploie le contenu `src/`, les requirements production nécessaires et l’unité systemd rendue par l’installateur. Les scopes backend/all-in-one déploient aussi les migrations PostgreSQL.

Le dossier racine `migrations/` est interdit dans les livrables. Toutes les migrations backend doivent être stockées et consommées depuis `installers/migrations/postgresql`.
