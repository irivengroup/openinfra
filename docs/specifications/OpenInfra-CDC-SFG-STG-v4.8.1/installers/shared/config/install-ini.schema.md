# Schéma logique `install.ini`

`install.ini` est volontairement succinct afin d'éviter d'exposer des paramètres permettant de contourner les limitations, quotas ou règles internes de l'installateur.

## Sections autorisées

| Section | Lite all-in-one | Pro server | Pro web | Enterprise server | Enterprise web | Enterprise agent |
|---|---:|---:|---:|---:|---:|---:|
| storage | oui | oui | non | oui | non | non |
| api | non | oui | oui | oui | oui | oui |
| identity | non | oui | non | oui | non | non |
| auth | non | oui | oui | oui | oui | non |

Toute autre section est interdite.

## `[storage]`

Champs autorisés :

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

```ini
[auth]
mode = standard
postgresql_dsn_ref = env:OPENINFRA_POSTGRES_DSN
postgresql_user_ref = env:OPENINFRA_POSTGRES_USER
postgresql_password_ref = env:OPENINFRA_POSTGRES_PASSWORD
```

Le mode par défaut et validé est `standard` : application + PostgreSQL. Lite n'expose pas cette section car tout est local et connu de l'installateur.

## PGDATA PostgreSQL

Le backend initialise PostgreSQL sous `/data/openinfra/`. Si le packaging PostgreSQL impose un chemin réel versionné, l'installateur adapte l'unité systemd PostgreSQL afin que le chemin effectif des données reste situé sous `/data/openinfra/` et soit reporté dans le rapport d'installation.
