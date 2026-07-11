# Installateur OpenInfra Lite — all-in-one

Ce scope installe le backend, le portail web et PostgreSQL sur un même hôte. Il utilise `openinfra.service`, une exposition locale contrôlée et le fichier `install.ini` du répertoire courant.

## Préconditions

- système Linux supporté avec privilèges administrateur ;
- volume group `datavg` disponible pour le LV `openinfradata_lv` de 2GB ;
- variables `OPENINFRA_LITE_WEB_POSTGRES_DSN`, `OPENINFRA_LITE_WEB_POSTGRES_USER` et `OPENINFRA_LITE_WEB_POSTGRES_PASSWORD` injectées par l'environnement sécurisé ;
- résolution FQDN, IP, masque, passerelle et DNS validée avant installation.

## Résultat attendu

L'installateur crée `/opt/openinfra/`, prépare `/data/openinfra/`, configure `/opt/openinfra/data -> /data/openinfra/`, initialise `PGDATA`, applique toutes les migrations backend et active `openinfra.service`. Le mode Lite reste limité au loopback et n'exige pas mTLS.

## Validation et rollback

Exécuter le dry-run avant l'application. Une erreur de dépendance, stockage ou migration interrompt l'installation avant activation du service. Le rollback restaure la configuration sauvegardée et ne supprime jamais les données PostgreSQL sans ordre explicite.
