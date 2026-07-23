# ADR-0015 — Séparer le stockage applicatif et le stockage PostgreSQL

## Statut

Accepté.

## Contexte

Les versions précédentes définissaient un filesystem applicatif `/opt/openinfra/`. Les données PostgreSQL backend doivent être isolées pour garantir sécurité, performance, exploitation, sauvegarde et restauration cohérentes.

## Décision

OpenInfra utilise deux zones distinctes :

- `/opt/openinfra/` pour l'application, propriétaire `openinfra` ;
- `/data/openinfra/` pour PostgreSQL, propriétaire logique `postgresql_service_account`.

Un symlink `/opt/openinfra/data` pointe vers `/data/openinfra/` mais n'autorise pas l'application à écrire directement dans les fichiers PostgreSQL.

## Conséquences

- Meilleure séparation des responsabilités.
- Sauvegarde PostgreSQL et extension disque plus sûres.
- Réduction du risque d'altération des données par le compte applicatif.
- Installation légèrement plus structurée car deux LV sont requis ou validés.


## PGDATA PostgreSQL

Le backend doit initialiser PostgreSQL avec `PGDATA=/data/openinfra/`. Si le packaging PostgreSQL impose un chemin réel versionné, l'installateur doit adapter l'unité systemd PostgreSQL afin que le chemin effectif des données reste situé sous `/data/openinfra/` et soit reporté dans le rapport d'installation.
