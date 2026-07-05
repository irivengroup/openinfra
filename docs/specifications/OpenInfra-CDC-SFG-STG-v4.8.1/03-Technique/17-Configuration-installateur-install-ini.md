# Configuration technique — `install.ini`, configuration runtime et verrou d'installation

## Contrat technique révisé

Le fichier `install.ini` est le contrat opérateur minimal utilisé uniquement pendant l'installation. Il ne doit pas exposer les champs permettant de piloter ou contourner une édition, un scope, un nom de service, des quotas, des ports internes, des opérations d'installation ou des chemins système canoniques. Ces décisions sont déduites par l'installateur depuis l'arborescence `installers/setup/...` et depuis la politique interne de l'édition.

Après installation, le dossier `installers/` n'est plus requis par les services runtime. Les paramètres utiles issus de `install.ini` et du fichier `.env` d'installation sont matérialisés dans la configuration runtime canonique `/opt/openinfra/config/openinfra.conf`. Le chemin `/etc/openinfra/openinfra.conf` est uniquement un chemin de compatibilité : `/etc/openinfra` doit être un lien symbolique vers `/opt/openinfra/config`.

Les clés inconnues sont rejetées. Les secrets ne sont jamais stockés en clair et doivent être fournis par référence `env:`, `vault://`, `sops://`, `file://` ou `kms://`.

## Configuration runtime canonique

L'installateur doit créer ou valider l'arborescence suivante :

```text
/opt/openinfra/
├── config/
│   ├── openinfra.conf
│   ├── install-<edition>-<scope>.ini
│   └── .openinfra-installed.lock
└── share/
    └── migrations/postgresql/
```

Règles obligatoires :

- `/opt/openinfra/config/openinfra.conf` est la source runtime canonique.
- `/etc/openinfra` est un symlink vers `/opt/openinfra/config`.
- les unités systemd utilisent `EnvironmentFile=/etc/openinfra/openinfra.conf` pour compatibilité Unix, mais le fichier réel est `/opt/openinfra/config/openinfra.conf`.
- le fichier `.openinfra-installed.lock` bloque toute installation multiple non contrôlée.
- les migrations backend sont copiées après installation vers `/opt/openinfra/share/migrations/postgresql`.
- aucune unité systemd ne dépend du dossier `installers/` après installation.

Le format de `openinfra.conf` est compatible systemd `EnvironmentFile`. Les valeurs sensibles sont stockées uniquement comme références :

```ini
OPENINFRA_EDITION="enterprise"
OPENINFRA_SCOPE="server"
OPENINFRA_RUNTIME_CONFIG="/opt/openinfra/config/openinfra.conf"
OPENINFRA_MIGRATIONS_ROOT="/opt/openinfra/share/migrations/postgresql"
OPENINFRA_INSTALL_AUTH_POSTGRESQL_USER_REF="env:OPENINFRA_POSTGRES_USER"
OPENINFRA_INSTALL_AUTH_POSTGRESQL_PASSWORD_REF="env:OPENINFRA_POSTGRES_PASSWORD"
OPENINFRA_INSTALL_SECURITY_TRANSPORT="mtls"
OPENINFRA_INSTALL_SECURITY_TLS_MIN_VERSION="TLSv1.3"
OPENINFRA_INSTALL_SECURITY_MTLS_REQUIRED="true"
```

## Règles par édition et scope

### Lite — `installers/setup/lite/install.ini`

Lite est une installation monolithique locale : base PostgreSQL, backend et frontend sur le même serveur. Lite reste strictement local, sans LDAP/IPA, sans API distante opérateur et sans mTLS exposé.

```ini
[storage]
vgname = datavg
lvname = openinfradata_lv
lvsize = 2GB

[security]
transport = local
tls_min_version = TLSv1.3
mtls_required = false
loopback_only = true
```

Règles internes : session locale applicative avec base locale uniquement, aucun LDAP/IPA, aucune configuration réseau externe, aucune section API, aucun multisite, aucun clustering, aucune section `identity`.

### Pro / Entreprise — scope `server`

Le backend est un service API-only. Il n'authentifie pas directement chaque opérateur humain et ne se connecte pas à LDAP/IPA pour un login opérateur. Il valide les jetons applicatifs présentés par le frontend ou les agents, applique le RBAC OpenInfra effectif et journalise les décisions d'autorisation.

Lorsque PostgreSQL est absent sur un backend local, l'installateur le déploie automatiquement selon la famille Linux détectée, active `postgresql.service`, vérifie la disponibilité, initialise PGDATA sous `/data/openinfra/`, puis applique les migrations backend depuis `/opt/openinfra/share/migrations/postgresql` avant activation du service.

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

[security]
transport = mtls
tls_min_version = TLSv1.3
mtls_required = true
server_ca_cert_ref = file:///opt/openinfra/config/trust/openinfra-ca.pem
client_cert_ref = file:///opt/openinfra/config/tls/backend.crt
client_key_ref = file:///opt/openinfra/config/tls/backend.key
trusted_proxy_cidrs = 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
loopback_only = false
```

`backend_endpoint` désigne l'endpoint backend exposé. En cluster, il désigne la VIP. Les ports de communication back/front, back/agent et inter-nœuds ne sont pas exposés dans `install.ini`; les ports internes par défaut sont respectivement 2006, 2007 et 2008. `peer_nodes` est utilisé uniquement lorsque le backend est clusterisé et ne doit contenir ni protocole ni port.

### Pro / Entreprise — scope `web`

Le scope web authentifie les opérateurs. En Pro/Entreprise, il peut utiliser l'authentification standard locale ou LDAP/IPA. Le résultat d'authentification est converti en jeton applicatif OpenInfra ; le backend reste l'autorité effective des permissions via RBAC, groupes et audits.

Le scope web ne déploie pas PostgreSQL et ne contient aucune section de stockage PostgreSQL. Il conserve le filesystem applicatif `/opt/openinfra/` géré en interne par l'installateur, sans exposition dans `install.ini`.

```ini
[api]
backend_endpoint = https://backend.example.com

[auth]
mode = standard

[security]
transport = mtls
tls_min_version = TLSv1.3
mtls_required = true
server_ca_cert_ref = file:///opt/openinfra/config/trust/openinfra-ca.pem
client_cert_ref = file:///opt/openinfra/config/tls/web.crt
client_key_ref = file:///opt/openinfra/config/tls/web.key
trusted_proxy_cidrs = 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
loopback_only = false
```

Exemple LDAP/IPA autorisé uniquement côté web Pro/Entreprise :

```ini
[auth]
mode = ldap
directory_url = ldaps://ipa.example.net:636
base_dn = dc=example,dc=net
user_filter = (uid={username})
group_filter = (member={user_dn})
bind_dn_ref = env:OPENINFRA_LDAP_BIND_DN
bind_password_ref = env:OPENINFRA_LDAP_BIND_PASSWORD
ca_cert_ref = file:///opt/openinfra/config/trust/ipa-ca.pem
cache_ttl_seconds = 300
```

### Entreprise — scope `agent`

L'agent s'enregistre auprès du backend via le portail web et transmet ensuite ses observations au backend avec son mécanisme technique d'enrôlement. Il n'a jamais d'accès direct à PostgreSQL. Il dispose du filesystem LVM applicatif `/opt/openinfra/` géré en interne par l'installateur, mais ne crée aucun filesystem PostgreSQL, aucun PGDATA, aucun symlink `/opt/openinfra/data` et aucune migration backend.

```ini
[api]
backend_endpoint = https://backend.example.com
enrollment_token_ref = env:OPENINFRA_AGENT_ENROLLMENT_TOKEN

[security]
transport = mtls
tls_min_version = TLSv1.3
mtls_required = true
server_ca_cert_ref = file:///opt/openinfra/config/trust/openinfra-ca.pem
client_cert_ref = file:///opt/openinfra/config/tls/agent.crt
client_key_ref = file:///opt/openinfra/config/tls/agent.key
trusted_proxy_cidrs =
loopback_only = false
```

## Sécurisation des échanges front/back/agent

Hors Lite, tout échange réseau entre frontend, backend, agents et nœuds backend doit utiliser TLS 1.3 avec authentification mutuelle mTLS. Les certificats, clés privées et autorités de certification sont déclarés par référence uniquement. Les chemins référencés sous `/opt/openinfra/config` doivent être protégés par permissions minimales et ne doivent jamais être journalisés en clair.

Flux imposés :

- frontend → backend : HTTPS TLS 1.3 + certificat client web + jeton applicatif opérateur ;
- agent → backend : HTTPS TLS 1.3 + certificat client agent + jeton/enrôlement technique ;
- backend ↔ backend : TLS 1.3 + mTLS + ports internes non exposés dans `install.ini` ;
- Lite : boucle locale seulement, sans exposition réseau opérateur.

## Stockage applicatif et PostgreSQL

Le filesystem applicatif `/opt/openinfra/` est géré par l'installateur pour les scopes applicatifs `lite/all-in-one`, `pro/server`, `pro/web`, `enterprise/server`, `enterprise/web` et `enterprise/agent`. Cette disposition est interne, non configurable dans `install.ini`, et permet de conserver une séparation enterprise des binaires, configurations applicatives, permissions et quotas filesystem.

Pour le stockage PostgreSQL des scopes backend, seuls `vgname`, `lvname` et `lvsize` sont exposés. L'installateur gère en interne le déploiement PostgreSQL si absent, le mountpoint `/data/openinfra/`, le symlink `/opt/openinfra/data -> /data/openinfra/`, les owner/group, les permissions, la résolution du compte système PostgreSQL et l'adaptation PGDATA.

Limites de taille exposées :

- Lite : `lvsize <= 2GB` ;
- Pro : `lvsize <= 100GB` ;
- Entreprise : pas de limite applicative imposée par le contrôleur, dimensionnement selon sizing/licence.

## Systemd

Le dossier `deploy/` n'est pas une source de vérité. Les unités `openinfra.service`, `openinfra-web.service` et `openinfra-agent.service` sont rendues par l'installateur selon l'édition et le scope. L'exécution des migrations relève de l'étape d'installation backend, pas d'un `ExecStartPre` systemd. Les unités chargent `EnvironmentFile=/etc/openinfra/openinfra.conf`, qui résout réellement vers `/opt/openinfra/config/openinfra.conf`.

## Installateurs autonomes et source unique des migrations

`installers/` embarque les programmes autonomes par scope : `installers/setup/lite/install.py`, `installers/setup/pro/server/install.py`, `installers/setup/pro/web/install.py`, `installers/setup/enterprise/server/install.py`, `installers/setup/enterprise/web/install.py` et `installers/setup/enterprise/agent/install.py`. Chaque programme déploie le contenu `src/`, les requirements production nécessaires et l'unité systemd rendue par l'installateur. Les scopes backend/all-in-one déploient aussi les migrations PostgreSQL sous `/opt/openinfra/share/migrations/postgresql`.

Le dossier racine `migrations/` est interdit dans les livrables. Pendant le build source, toutes les migrations backend doivent être stockées dans `installers/migrations/postgresql`; après installation, les services consomment la copie runtime `/opt/openinfra/share/migrations/postgresql`.
