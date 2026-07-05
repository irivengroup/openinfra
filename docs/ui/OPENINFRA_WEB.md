# OpenInfra Web v0.29.12

OpenInfra Web est le frontend `openinfra-web` de P08. Il sert l'interface React/Bootstrap 5 et expose un proxy applicatif `/api/*` vers le backend `openinfra-api`.

## Contrat runtime

- Le navigateur consomme `/api/*` sur la même origine que `openinfra-web`.
- `openinfra-web` relaie les appels vers `OPENINFRA_WEB_BACKEND_URL`.
- Le frontend ne reçoit jamais de DSN PostgreSQL, de mot de passe LDAP/IPA, de clé privée ou de jeton d'enrôlement agent.
- Hors Lite, `OPENINFRA_WEB_BACKEND_URL` doit être HTTPS, sauf environnement Docker de validation explicitement marqué `OPENINFRA_WEB_ALLOW_INSECURE_BACKEND=true`.
- Le RBAC effectif reste appliqué côté backend à chaque appel API.

## Docker Compose

Le service Compose `openinfra-web` dépend de `api:8080`, écoute par défaut sur `127.0.0.1:2006` et sert `/health`, `/ready`, `/config.json` et les assets web.

## Installation native

L'unité `openinfra-web.service` lance `openinfra-web` depuis le virtualenv géré par l'installateur et lit sa configuration via `EnvironmentFile=/etc/openinfra/openinfra.conf`, chemin compatible pointant vers `/opt/openinfra/config/openinfra.conf`.
