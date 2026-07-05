# Schéma logique `install.ini`

`install.ini` est volontairement succinct afin d'éviter d'exposer des paramètres permettant de contourner les limitations, quotas ou règles internes de l'installateur.

## Sections autorisées

| Section | Lite all-in-one | Pro server | Pro web | Enterprise server | Enterprise web | Enterprise agent |
|---|---:|---:|---:|---:|---:|---:|
| storage | oui | oui | non | oui | non | non |
| api | non | oui | oui | oui | oui | oui |
| identity | non | oui | non | oui | non | non |
| auth | non | oui | oui | oui | oui | non |
| security | oui | oui | oui | oui | oui | oui |

Toute autre section est interdite.

## `[storage]`

```ini
[storage]
vgname = datavg
lvname = openinfradata_lv
lvsize = 100GB
```

`mountpoint`, `owner`, `group`, `PGDATA`, filesystem, symlink et compte système PostgreSQL sont des décisions internes de l'installateur. Le stockage PostgreSQL effectif reste `/data/openinfra/` avec symlink interne `/opt/openinfra/data -> /data/openinfra/`.

## `[api]`

```ini
[api]
backend_endpoint = https://openinfra-vip.example.com
enrollment_token_ref = env:OPENINFRA_AGENT_ENROLLMENT_TOKEN
```

`backend_endpoint` désigne le backend, ou la VIP backend en cluster. Les ports par défaut ne sont pas configurables dans `install.ini` : `2006` pour back/front, `2007` pour back/agent, `2008` pour synchronisation cluster.

## `[identity]`

```ini
[identity]
peer_nodes = backend02.example.com,backend03.example.com
```

`peer_nodes` est utilisé uniquement pour la synchronisation cluster server. Le protocole de synchronisation est choisi par l'installateur selon robustesse, performance et résilience.

## `[auth]`

Scope server :

```ini
[auth]
mode = standard
postgresql_user_ref = env:OPENINFRA_POSTGRES_USER
postgresql_password_ref = env:OPENINFRA_POSTGRES_PASSWORD
```

Scope web :

```ini
[auth]
mode = standard
```

LDAP/IPA est autorisé uniquement pour les scopes web Pro/Enterprise. Le backend ne réalise pas de login opérateur LDAP/IPA ; il valide des jetons applicatifs et applique les permissions OpenInfra.

## `[security]`

Lite :

```ini
[security]
transport = local
tls_min_version = TLSv1.3
mtls_required = false
loopback_only = true
```

Pro/Enterprise :

```ini
[security]
transport = mtls
tls_min_version = TLSv1.3
mtls_required = true
server_ca_cert_ref = file:///opt/openinfra/config/trust/openinfra-ca.pem
client_cert_ref = file:///opt/openinfra/config/tls/<scope>.crt
client_key_ref = file:///opt/openinfra/config/tls/<scope>.key
trusted_proxy_cidrs = 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
loopback_only = false
```

## Configuration runtime

Après installation, le fichier runtime canonique est `/opt/openinfra/config/openinfra.conf`. `/etc/openinfra` est un symlink vers `/opt/openinfra/config`. Les unités systemd utilisent `EnvironmentFile=/etc/openinfra/openinfra.conf`, ce qui résout le fichier canonique sans conserver `installers/` au runtime.

## PGDATA PostgreSQL

Le backend initialise PostgreSQL sous `/data/openinfra/`. Si le packaging PostgreSQL impose un chemin réel versionné, l'installateur adapte l'unité systemd PostgreSQL afin que le chemin effectif des données reste situé sous `/data/openinfra/` et soit reporté dans le rapport d'installation.
