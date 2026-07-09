# Installateurs hors `src` et déploiement des migrations backend

## Règle de séparation

Les installateurs doivent être dans `installers/`, en dehors de `src/`. Le dossier `src/` contient uniquement le code applicatif et les packages Python/TypeScript applicatifs.

## Responsabilité du backend installer

L'installateur backend `server` est le seul responsable du déploiement PostgreSQL local lorsque PostgreSQL est absent, puis de l'application des migrations base de données. Le scope Lite `all-in-one` suit la même règle car il embarque backend et base sur le même serveur.

Il doit :

- localiser les migrations dans la source unique `installers/migrations/postgresql` ;
- refuser tout dossier racine `migrations/` pour éviter deux sources de vérité ;
- détecter la famille Linux via `/etc/os-release` ;
- installer PostgreSQL si `psql` est absent avec le gestionnaire de paquets adapté (`dnf`, `apt-get` ou `zypper`) ;
- activer et démarrer `postgresql.service` avant l'initialisation PGDATA ;
- vérifier la readiness PostgreSQL avec `pg_isready` ;
- vérifier l'intégrité des fichiers de migration ;
- vérifier l'état actuel du schéma ;
- prendre un verrou de migration ;
- appliquer toutes les migrations manquantes ;
- refuser de démarrer le backend si le schéma est incohérent ;
- générer un rapport de migration ;
- vérifier les index, contraintes et partitions critiques après migration ;
- exposer un statut de migration via commande CLI et endpoint backend.

## Interdictions

- Le frontend ne doit jamais appliquer de migration.
- L'agent proxy collector Enterprise ne doit jamais appliquer de migration.
- Le frontend et l'agent proxy collector Enterprise ne doivent jamais installer PostgreSQL.
- Un installateur ne doit jamais modifier directement une table métier hors mécanisme de migration.
- Une migration ne doit jamais être ignorée silencieusement.
- Une installation ne doit jamais démarrer un backend sur un schéma non validé.

## Modes supportés

| Mode | Comportement |
|---|---|
| `--dry-run` | Calcule les migrations à appliquer sans modification. |
| `--apply` | Applique les migrations et démarre le service si validation OK. |
| `--migrate-only` | Applique les migrations sans installer le service applicatif. |
| `--verify-only` | Vérifie le schéma et les migrations déjà appliquées. |
| `--rollback` | Lance la procédure de retour documentée pour une installation échouée. |

## Preuves attendues

Le rapport de migration doit contenir :

- version initiale ;
- version cible ;
- migrations appliquées ;
- durée ;
- hash des fichiers ;
- statut des contraintes ;
- statut des index ;
- statut des partitions ;
- statut final ;
- identifiant de corrélation.

## Exigence de moteur installateur autonome transactionnel

Chaque programme d'installation sous `installers/setup/**/install.py` doit être exécutable sans dépendre d'un dossier `deploy/` externe. L'installateur doit déployer le contenu applicatif `src/`, le `pyproject.toml`, les dépendances de production `installers/requirements`, les migrations backend lorsque le scope gère PostgreSQL, puis rendre l'unité systemd depuis ses règles internes.

L'installation effective doit vérifier les prérequis OS, créer le virtualenv `/opt/openinfra/venv`, installer les dépendances de production du scope et installer le package OpenInfra local dans ce virtualenv. Les unités systemd doivent être activées et redémarrées uniquement après validation du payload et, pour les backends, après disponibilité PostgreSQL et application des migrations.

Toute écriture doit être transactionnelle : un échec doit restaurer les fichiers et dossiers remplacés ou supprimer les chemins nouvellement créés par la tentative courante. Les sauvegardes résiduelles `.openinfra-rollback` doivent pouvoir être restaurées par le mode `--rollback`.


### Politique de minimisation des migrations — v0.29.74

Les migrations PostgreSQL doivent être créées uniquement lorsqu'un changement de schéma, de contrainte, d'index, de partitionnement ou de données de compatibilité l'exige. Une correction UI, documentaire, CLI sans changement de persistance ou de validation frontend ne doit pas créer de migration. Les migrations déjà publiées ne sont pas fusionnées rétroactivement afin de préserver la table d'historique des environnements ayant déjà appliqué les versions précédentes.

Pour v0.29.74, aucun script `0032_*` n'est ajouté : la dernière migration reste `0031_itam_organization_identity.sql`.


Pour v0.29.75, une seule migration structurante `0032_itam_partner_registry.sql` est ajoutée pour le référentiel ITAM des partenaires accrédités. Cette migration n’annule pas la règle v0.29.74 : aucune migration ne doit être créée pour un simple correctif UI ; seules les évolutions de schéma métier justifient une nouvelle migration versionnée.


Pour v0.29.77, la migration structurante `0033_dcim_site_dependencies_rack_lifecycle.sql` ajoute le statut de cycle de vie des chassis/racks DCIM et les index nécessaires au catalogue actif par site, bâtiment, salle, ligne et colonne. Cette migration est justifiée par une évolution de schéma métier et reste additive.


Pour v0.29.78, la migration additive `0034_discovery_protocol_profiles.sql` crée le référentiel partitionné des profils protocoles Discovery SNMP/SSH/WinRM, avec contraintes de sécurité sur `vault://`, WinRM HTTPS, bornes de concurrence/rate-limit et index actifs par tenant/protocole/scope.
