# Volume V29 — Stockage PostgreSQL dédié, réplication quasi synchrone et multisite

## 1. Positionnement

Ce volume complète les volumes V26, V27 et V28. Il définit les règles obligatoires de stockage PostgreSQL backend, de symlink applicatif, de réplication automatique en cluster et de support multisite.

## 2. Stockage applicatif vs stockage PostgreSQL

OpenInfra doit séparer strictement :

| Zone | Mountpoint | Propriétaire | Usage |
|---|---|---|---|
| Application | `/opt/openinfra/` | `openinfra:openinfra` | application, configuration, scripts, artefacts contrôlés |
| PostgreSQL backend | `/data/openinfra/` | compte système PostgreSQL résolu | données PostgreSQL, WAL, tablespaces, état local DB |

Cette séparation est obligatoire pour éviter :

- une confusion entre droits applicatifs et droits base ;
- un écrasement accidentel des données PostgreSQL par l'application ;
- une saturation du filesystem applicatif par la base ;
- une sauvegarde incohérente ;
- une restauration impossible à granularité base.

## 3. Paramètres LVM obligatoires

### 3.1 LV applicatif

```yaml
openinfra_application_fs:
  vgname: rootvg
  lvname: openinfra_lv
  mountpoint: /opt/openinfra/
  lv_size: 2GB
  owner: openinfra
  group: openinfra
```

### 3.2 LV PostgreSQL backend

```yaml
openinfra_postgresql_data_fs:
  vgname: datavg
  lvname: openinfradata_lv
  mountpoint: /data/openinfra/
  pgdata: /data/openinfra/
  lv_size_by_edition:
    lite: 2GB
    pro: 100GB
    enterprise: 1TB
  owner: postgresql_service_account
  group: postgresql_service_group
```

`postgresql_service_account` est une variable logique. L'installateur doit détecter le compte réel ou le créer selon le packaging PostgreSQL retenu.

## 4. Symlink standard

```text
/opt/openinfra/data -> /data/openinfra/
```

Le symlink est fourni pour offrir un point de référence OpenInfra stable. Il ne change pas la règle de sécurité : le compte applicatif `openinfra` ne doit pas écrire directement dans les fichiers PostgreSQL internes.

## 5. Réplication quasi synchrone

En mode cluster backend, l'installation doit configurer automatiquement une réplication PostgreSQL quasi synchrone.

Mode par défaut :

- réplication streaming activée ;
- au moins un standby local ou proche réseau en quorum synchrone ;
- confirmation transactionnelle après réception WAL par le standby éligible ;
- supervision du lag ;
- bascule automatique contrôlée ;
- rétrogradation propre de l'ancien primaire ;
- réintégration automatisée d'un nœud restauré.

Le mode strict `remote_apply` peut être activé lorsque la latence et les objectifs RPO/RTO le justifient. Le mode WAN strict n'est pas activé par défaut pour éviter une dégradation globale.

## 6. Multisite

### 6.1 Pro

L'édition Pro doit supporter :

- plusieurs sites dans le référentiel ;
- RBAC par site ;
- vues par site ;
- affectation d'équipements, racks, subnets, VLAN, contrats et propriétaires par site ;
- discovery directe depuis le backend central ;
- exports et rapports filtrés par site ;
- connecteurs ITSM externes contextualisés par site.

### 6.2 Entreprise

L'édition Entreprise doit supporter en plus :

- agents régionaux ;
- clustering d'agents ;
- découverte région/site/VRF ;
- files de jobs par site/région ;
- routage intelligent des jobs ;
- stratégie DR multisite ;
- réplication inter-sites contrôlée ;
- politiques de latence et de souveraineté par site ;
- supervision de santé des sites.

## 7. Critères d'acceptation

L'exigence est acceptée uniquement si :

- `/opt/openinfra/` est monté et possédé par `openinfra` ;
- `/data/openinfra/` est monté et possédé par le compte PostgreSQL résolu ;
- `/opt/openinfra/data` pointe vers `/data/openinfra/` ;
- l'installateur refuse une configuration où le compte applicatif peut écrire arbitrairement dans les fichiers internes PostgreSQL ;
- le cluster configure automatiquement la réplication quasi synchrone ;
- le replication lag est supervisé ;
- une bascule primaire est testée ;
- Pro et Entreprise exposent des fonctions multisites conformes à leurs capacités respectives ;
- aucune contradiction ne subsiste avec les volumes V26, V27 et V28.


## PGDATA PostgreSQL

Le backend doit initialiser PostgreSQL avec `PGDATA=/data/openinfra/`. Si le packaging PostgreSQL impose un chemin réel versionné, l'installateur doit adapter l'unité systemd PostgreSQL afin que le chemin effectif des données reste situé sous `/data/openinfra/` et soit reporté dans le rapport d'installation.
