# Règles de validation `install.ini`

Le fichier `install.ini` est un contrat opérateur minimal. Il ne contient jamais l'édition, le scope, le nom du service systemd, les opérations normales d'installation, les ports internes, les propriétaires Unix ou les chemins de montage.

## Règles transverses

- L'édition et le scope sont déduits par l'installateur depuis `installers/<edition>/<scope>/`.
- Les services `openinfra.service`, `openinfra-web.service` et `openinfra-agent.service` sont rendus par l'installateur, pas déclarés dans `install.ini`.
- La section `[operations]` est interdite : validation, prérequis, migrations, rollback, activation systemd et smoke tests sont des étapes internes.
- Les ports internes sont fixes : backend/front `2006`, backend/agent `2007`, synchronisation cluster `2008`.
- Les secrets doivent être fournis par référence : `env:`, `vault://`, `sops://`, `file://` ou `kms://`.
- Aucun champ contenant `password`, `secret` ou `token` n'est accepté sans suffixe `_ref`.
- La section `[storage]` expose uniquement `vgname`, `lvname` et `lvsize`.
- `mountpoint`, `owner`, `group`, `PGDATA`, symlink et compte système PostgreSQL sont résolus par l'installateur.

## Règles par scope

| Edition/scope | Sections autorisées | Règles spécifiques |
|---|---|---|
| Lite `all-in-one` | `[storage]` | Monolithique local app+BDD+frontend ; pas de LDAP, pas de réseau, pas d'API, pas de cluster. |
| Pro `server` | `[storage]`, `[api]`, `[identity]`, `[auth]` | Backend avec PostgreSQL local/cluster ; `backend_endpoint` désigne la VIP si cluster. |
| Pro `web` | `[api]`, `[auth]` | Aucun déploiement de BDD ; DSN PostgreSQL requis pour la connexion applicative. |
| Enterprise `server` | `[storage]`, `[api]`, `[identity]`, `[auth]` | Backend illimité ; peer nodes requis lorsque le cluster est activé. |
| Enterprise `web` | `[api]`, `[auth]` | Aucun déploiement de BDD ; DSN PostgreSQL requis pour la connexion applicative. |
| Enterprise `agent` | `[api]` | Enrôlement via backend/portail web puis échange token/certificat avec le backend. |

## Tailles LVM maximales exposées

- Lite : `2GB`.
- Pro : `100GB`.
- Enterprise : `1TB` indicatif de sizing initial, sans contrôle de quota fonctionnel d'édition.
