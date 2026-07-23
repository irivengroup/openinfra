# Installateur OpenInfra Pro — web

Ce scope installe uniquement le portail React + Bootstrap 5 et active `openinfra-web.service`. Il ne crée pas PostgreSQL et n'applique aucune migration backend.

## Préconditions

- endpoint HTTPS du backend Pro accessible ;
- FQDN, IP, masque, passerelle et DNS validés ;
- certificats mTLS et CA présents aux chemins référencés ;
- secrets de connexion web éventuels injectés via les variables `OPENINFRA_PRO_WEB_POSTGRES_*` sans valeur en clair dans `install.ini`.

## Résultat attendu

Les assets web sont installés sous `/opt/openinfra/`, la configuration API est externalisée et `openinfra-web.service` communique avec `openinfra.service` en TLS 1.3 avec mTLS.

## Validation et rollback

Le dry-run valide les dépendances, les assets, l'endpoint API et les références de certificats. Le rollback restaure la version précédente du portail sans exécuter de migration ni modifier `PGDATA`.
