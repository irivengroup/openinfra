# Installateur OpenInfra Entreprise — web

Ce scope installe le portail React + Bootstrap 5 de l'édition Entreprise et active `openinfra-web.service`. Il consomme l'API backend via la VIP et n'applique aucune migration backend.

## Préconditions

- VIP backend, FQDN, IP, masque, passerelle et DNS résolus ;
- certificats TLS 1.3/mTLS et CA disponibles par référence ;
- secrets de connexion éventuels injectés via `OPENINFRA_ENTERPRISE_WEB_POSTGRES_*` ;
- accès réseau limité aux flux déclarés.

## Résultat attendu

Les assets et la configuration externalisée sont installés sous `/opt/openinfra/`. `openinfra-web.service` dialogue avec `openinfra.service` par mTLS, sans accès direct non gouverné à `PGDATA` et sans exécution de migration.

## Validation et rollback

Le dry-run vérifie l'endpoint, les certificats, les assets et les permissions. Le rollback restaure le bundle et la configuration précédents sans toucher aux données backend.
