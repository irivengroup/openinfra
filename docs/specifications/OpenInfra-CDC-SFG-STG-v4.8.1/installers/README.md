# Installers OpenInfra

Ce dossier représente la structure cible obligatoire des installateurs OpenInfra. Il est volontairement placé hors de `src/`.

## Règles

- `src/` contient le code applicatif.
- `installers/` contient les profils d'installation, migrations backend, requirements de production par scope et règles de validation.
- `deploy/` n'est pas une source de vérité : les unités systemd sont rendues par l'installateur.
- `install.ini` reste minimal et n'expose pas l'édition, le scope, le service, les opérations normales, les ports internes, les propriétaires ou les mountpoints.
- `server` et `all-in-one` appliquent toutes les migrations backend depuis `installers/migrations/postgresql`.
- `web` installe le frontend et consomme le backend via `backend_endpoint`.
- `agent` installe les collecteurs Discovery uniquement en édition Enterprise et s'enrôle auprès du backend via token/certificat.

## Scopes

| Edition | Scope | Dossier |
|---|---|---|
| Lite | all-in-one | `installers/setup/lite/` |
| Pro | server | `installers/setup/pro/server/` |
| Pro | web | `installers/setup/pro/web/` |
| Enterprise | server | `installers/setup/enterprise/server/` |
| Enterprise | web | `installers/setup/enterprise/web/` |
| Enterprise | agent | `installers/setup/enterprise/agent/` |

## Nettoyage source migrations

Aucun dossier documentaire `shared/migrations` n’est conservé afin d’éviter toute seconde source de vérité. Les migrations backend existent uniquement dans le projet runtime sous `installers/migrations/postgresql`.
