# Delta v4.7.0 — Stockage PostgreSQL dédié, cluster à synchronisation quasi temps réel et multisite

## 1. Objectif

La version v4.7.0 consolide les exigences d'installation et d'exploitation en séparant proprement le stockage applicatif OpenInfra du stockage PostgreSQL backend, en formalisant la réplication automatique quasi temps réel en mode cluster et en ajoutant le support multisite pour les éditions Pro et Entreprise.

## 2. Décisions obligatoires

### 2.1 Filesystem applicatif

- Mountpoint applicatif : `/opt/openinfra/`.
- Propriétaire : compte système applicatif `openinfra`.
- Groupe : `openinfra`.
- LV applicatif par défaut : `rootvg/openinfra_lv`.
- Taille par défaut : `2GB`.
- Usage : binaires, configuration applicative, logs locaux contrôlés, fichiers d'installation, métadonnées OpenInfra non PostgreSQL.

### 2.2 Filesystem PostgreSQL backend

- Mountpoint PostgreSQL : `/data/openinfra/`.
- VG par défaut : `datavg`.
- LV par défaut : `openinfradata_lv`.
- Taille par défaut par édition : Lite `2GB`, Pro `100GB`, Entreprise `1TB`.
- Propriétaire logique : compte système gestionnaire PostgreSQL résolu par l'installateur.
- Usage : données PostgreSQL, WAL si non séparé, tablespaces gérés, état cluster local si applicable.

### 2.3 Clarification du terme `pgsql user`

Le terme `pgsql user` ne définit pas un nom Unix obligatoire. Il désigne le compte système qui exécute et administre le service PostgreSQL sur la distribution ou le packaging retenu. L'installateur doit détecter ou créer ce compte selon le mode d'installation et l'exposer comme variable logique `postgresql_service_account`.

### 2.4 Symlink

Le symlink obligatoire est :

```text
/opt/openinfra/data -> /data/openinfra/
```

L'ownership du symlink et du répertoire cible doit suivre le compte système PostgreSQL résolu. Le compte applicatif `openinfra` ne doit pas écrire directement dans les fichiers internes PostgreSQL.

### 2.5 Cluster PostgreSQL quasi temps réel

En mode cluster, l'installateur doit configurer automatiquement :

- initialisation primaire ;
- création ou rattachement des réplicas ;
- réplication streaming ;
- sélection du ou des standbys synchrones ;
- mode quasi temps réel par défaut ;
- bascule contrôlée ;
- health checks ;
- supervision du replication lag ;
- sauvegardes et WAL archiving ;
- validation post-installation.

Le mode quasi temps réel cible un accusé de réception par au moins un standby éligible avant confirmation applicative, sans imposer par défaut une synchronisation WAN pénalisante entre sites distants.

### 2.6 Multisite Pro et Entreprise

- Pro : support multisite centralisé, RBAC par site, inventory multi-sites, vues site-aware, imports/discovery directs depuis backend central.
- Entreprise : support multisite distribué, agents régionaux, clustering agents, découverte par région/site/VRF, DR multi-site, routage des jobs et gouvernance inter-sites.

## 3. Corrections d'incohérences

- `/opt/openinfra/` ne doit plus être présenté comme répertoire physique des données PostgreSQL.
- Le LV applicatif `openinfra_lv` et le LV PostgreSQL `openinfradata_lv` sont distincts.
- Le backend `openinfra.service` reste le seul scope autorisé à appliquer les migrations.
- `openinfra-web.service` et `openinfra-agent.service` ne doivent jamais appliquer les migrations.
- Les noms systemd ne varient pas selon l'édition.
- Le support multisite ne transforme pas Pro en architecture agent-cluster distribuée ; cette capacité reste Entreprise.
