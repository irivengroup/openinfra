# Règles de validation `install.ini`

Le fichier `install.ini` est un contrat opérateur minimal. Il ne contient jamais l'édition, le scope, le nom du service systemd, les opérations normales d'installation, les ports internes, les propriétaires Unix ou les chemins de montage.

## Règles transverses

- L'édition et le scope sont déduits par l'installateur depuis `installers/setup/<edition>/<scope>/`.
- Les services `openinfra.service`, `openinfra-web.service` et `openinfra-agent.service` sont rendus par l'installateur, pas déclarés dans `install.ini`.
- La section `[operations]` est interdite : validation, prérequis, migrations, rollback, activation systemd et smoke tests sont des étapes internes.
- Les ports internes sont fixes : backend/front `2006`, backend/agent `2007`, synchronisation cluster `2008`.
- Les secrets doivent être fournis par référence : `env:`, `vault://`, `sops://`, `file://` ou `kms://`.
- Aucun champ contenant `password`, `secret` ou `token` n'est accepté sans suffixe `_ref`.
- La section `[storage]` expose uniquement `vgname`, `lvname` et `lvsize`.
- `mountpoint`, `owner`, `group`, `PGDATA`, symlink et compte système PostgreSQL sont résolus par l'installateur.
- La section `[security]` est obligatoire pour tous les scopes.
- Pro/Entreprise imposent `transport=mtls`, `tls_min_version=TLSv1.3` et `mtls_required=true`.
- Lite impose `transport=local`, `mtls_required=false` et `loopback_only=true`.
- Les certificats et clés sont déclarés par référence `file://`, `vault://`, `sops://` ou `kms://`, jamais en clair.

## Runtime post-installation

Après installation, `install.ini` n'est plus lu par les services. Les paramètres utiles issus de `install.ini` et de `.env` sont matérialisés dans `/opt/openinfra/config/openinfra.conf`. Le répertoire `/etc/openinfra` doit être un lien symbolique vers `/opt/openinfra/config`, ce qui rend `/etc/openinfra/openinfra.conf` compatible avec systemd sans créer de seconde source de vérité.

Le fichier `/opt/openinfra/config/.openinfra-installed.lock` empêche toute réinstallation accidentelle. Les migrations backend sont copiées dans `/opt/openinfra/share/migrations/postgresql` ; aucune unité systemd ne dépend de `installers/` après installation.

## Règles par scope

| Edition/scope | Sections autorisées | Règles spécifiques |
|---|---|---|
| Lite `all-in-one` | `[storage]`, `[security]` | Monolithique local app+BDD+frontend ; pas de LDAP, pas de réseau distant, pas d'API opérateur exposée, pas de cluster. |
| Pro `server` | `[storage]`, `[api]`, `[identity]`, `[auth]`, `[security]` | Backend API-only avec PostgreSQL local/cluster ; `backend_endpoint` désigne la VIP si cluster ; pas de login LDAP/IPA opérateur côté backend. |
| Pro `web` | `[api]`, `[auth]`, `[security]`, `[web_database]` | Authentification opérateur locale ou LDAP/IPA ; trust backend mTLS ; références PostgreSQL côté service web uniquement. |
| Enterprise `server` | `[storage]`, `[api]`, `[identity]`, `[auth]`, `[security]` | Backend API-only illimité ; peer nodes requis lorsque le cluster est activé. |
| Enterprise `web` | `[api]`, `[auth]`, `[security]`, `[web_database]` | Authentification opérateur locale ou LDAP/IPA ; trust backend mTLS ; références PostgreSQL côté service web uniquement. |
| Enterprise `agent` | `[api]`, `[security]` | Enrôlement via backend/portail web puis échange token/certificat avec le backend ; aucun accès PostgreSQL. |

## Tailles LVM maximales exposées

- Lite : `2GB`.
- Pro : `100GB`.
- Enterprise : `1TB` indicatif de sizing initial, sans contrôle de quota fonctionnel d'édition.
