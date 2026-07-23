# Stockage PostgreSQL dédié

## Exigence générale

Le stockage applicatif et le stockage PostgreSQL doivent être séparés dès l'installation.

## Filesystem applicatif

- Mountpoint : `/opt/openinfra/`.
- Owner : `openinfra`.
- Groupe : `openinfra`.
- LV par défaut : `rootvg/openinfra_lv`.
- Taille par défaut : `2GB`.

## Filesystem PostgreSQL backend

- Mountpoint : `/data/openinfra/`.
- VG par défaut : `datavg`.
- LV par défaut : `openinfradata_lv`.
- Taille par défaut par édition : Lite `2GB`, Pro `100GB`, Entreprise `1TB`.
- Owner logique : `postgresql_service_account`.
- Groupe logique : `postgresql_service_group`.

## Résolution du compte PostgreSQL

Le terme `pgsql user` désigne le compte système gestionnaire PostgreSQL. Il ne doit pas être interprété comme un nom figé.

L'installateur doit :

1. détecter le compte système du service PostgreSQL si PostgreSQL est installé ;
2. créer ou valider le compte si PostgreSQL est installé par OpenInfra ;
3. enregistrer le compte effectif dans l'inventaire local d'installation ;
4. appliquer les permissions au mountpoint PostgreSQL ;
5. refuser le démarrage si le mountpoint n'appartient pas au compte attendu.

## Symlink

Le symlink `/opt/openinfra/data` doit pointer vers `/data/openinfra/`. Il est une convention d'accès et de repérage, pas une autorisation d'écriture pour l'application.

## Sécurité

Le compte `openinfra` ne doit pas obtenir de droit d'écriture direct sur les fichiers internes PostgreSQL. Les accès aux données doivent passer par PostgreSQL et les API applicatives.


## PGDATA PostgreSQL

Le backend doit initialiser PostgreSQL avec `PGDATA=/data/openinfra/`. Si le packaging PostgreSQL impose un chemin réel versionné, l'installateur doit adapter l'unité systemd PostgreSQL afin que le chemin effectif des données reste situé sous `/data/openinfra/` et soit reporté dans le rapport d'installation.
