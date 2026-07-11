# Installateur OpenInfra Pro — serveur

Ce scope installe le backend canonique `openinfra.service`, PostgreSQL et toutes les migrations backend de l'édition Pro. Le portail web est installé par le scope `pro/web`.

## Préconditions

- FQDN, IP, masque, passerelle et DNS validés ;
- volume group `datavg` disponible pour `openinfradata_lv` de 100GB ;
- certificats CA, client et clé privée référencés par `file://` ;
- secrets PostgreSQL injectés via `OPENINFRA_POSTGRES_USER` et `OPENINFRA_POSTGRES_PASSWORD` ;
- endpoint backend HTTPS conforme au `install.ini`.

## Résultat attendu

L'installateur prépare `/opt/openinfra/`, `/data/openinfra/`, le lien `/opt/openinfra/data -> /data/openinfra/`, initialise `PGDATA`, applique toutes les migrations backend et active `openinfra.service`. TLS 1.3 et mTLS sont obligatoires.

## Validation et rollback

Le dry-run contrôle dépendances, capacité LVM, références de secrets, certificats et connectivité. En cas d'échec, aucune activation partielle n'est conservée ; la configuration précédente est restaurée et les données restent préservées.
