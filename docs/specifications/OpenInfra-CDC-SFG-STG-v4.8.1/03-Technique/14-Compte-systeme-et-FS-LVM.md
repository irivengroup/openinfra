# Compte système OpenInfra et filesystem LVM dédié

## Compte système

L'installateur exécuté par root doit créer :

```text id="qzax6s"
user: openinfra
group: openinfra
home: /opt/openinfra/
shell: /usr/sbin/nologin
```

Le compte est non interactif. Il exécute les services applicatifs et les commandes OpenInfra autorisées par l'édition installée.

## Droits

Le compte `openinfra` doit :

- posséder `/opt/openinfra/` ;
- lire la configuration nécessaire ;
- écrire dans ses répertoires runtime ;
- exécuter les binaires OpenInfra ;
- exécuter les commandes OpenInfra administratives prévues ;
- ne jamais modifier ses propres règles sudoers ;
- ne jamais obtenir un shell root arbitraire.

## LVM

L'installateur doit préparer le stockage avant le déploiement applicatif pour les scopes applicatifs `lite/all-in-one`, `pro/server`, `pro/web`, `enterprise/server` et `enterprise/web`. Le scope `enterprise/agent` est explicitement exclu de la création de filesystem LVM applicatif et s'installe directement sous `/opt/openinfra/` :

```text id="xpovd5"
VG par défaut       : rootvg
LV par défaut       : openinfra_lv
Taille par défaut   : 2GB
Mountpoint          : /opt/openinfra/
FS recommandé       : xfs
```

## Ordre d'exécution

1. Vérification root.
2. Détection OS.
3. Installation des dépendances système.
4. Vérification ou création du VG/LV.
5. Création du filesystem si nécessaire.
6. Montage dans `/opt/openinfra/`.
7. Écriture `/etc/fstab` atomique avec sauvegarde.
8. Création utilisateur/groupe `openinfra`.
9. Application propriétaire et permissions.
10. Déploiement applicatif.
11. Application migrations pour le scope backend.
12. Démarrage services.
13. Health checks.

Pour le scope `enterprise/agent`, les étapes VG/LV/filesystem/montage applicatif sont sautées. L'installateur crée uniquement le compte/service nécessaires, déploie l'agent sous `/opt/openinfra/`, configure son enrôlement backend et active `openinfra-agent.service`.

## Refus obligatoires

L'installateur doit refuser :

- un mountpoint non monté mais contenant déjà des données non OpenInfra ;
- un LV existant avec filesystem incompatible sans validation explicite ;
- un VG absent si aucun disque ou PV n'est fourni et que la politique interdit l'installation hors LVM ;
- une taille inférieure à la taille minimale de l'édition ;
- des permissions permettant l'écriture par d'autres utilisateurs non autorisés.

## Exception agent Enterprise

`enterprise/agent` ne doit jamais créer ni modifier un LV applicatif, un LV PostgreSQL, PGDATA ou le symlink `/opt/openinfra/data`. L'agent est installé directement sous `/opt/openinfra/` et communique avec le backend via API et jeton/certificat d'enrôlement.
