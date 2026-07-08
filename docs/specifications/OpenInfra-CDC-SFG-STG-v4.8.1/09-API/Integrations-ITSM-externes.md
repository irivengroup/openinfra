# Intégrations ITSM externes — Pro et Entreprise uniquement

## Objectif

OpenInfra doit pouvoir s'intégrer aux principales solutions ITSM externes dans les éditions Pro et Entreprise, sans intégrer de module ITSM natif.

## Principe d'intégration

OpenInfra agit comme référentiel d'infrastructure et fournisseur de contexte. L'ITSM externe reste maître des tickets, incidents, demandes, changements, SLA et files de traitement.

## Connecteurs obligatoires

| Connecteur | Edition Pro | Edition Entreprise | Capacités minimales |
|---|---:|---:|---|
| ServiceNow | Oui | Oui | CMDB CI sync, ticket context, webhooks, import set/CMDB mapping |
| Jira Service Management | Oui | Oui | lien asset/ticket, enrichissement issue/request, webhooks |
| GLPI | Oui | Oui | synchronisation d'actifs, liens tickets externes, inventaire contexte |
| Freshservice | Oui | Oui | requester/ticket/asset context, webhooks, synchronisation contrôlée |
| Zendesk | Optionnel | Oui | liens tickets, contexte équipement/application |
| Zammad | Optionnel | Oui | liens tickets, contexte équipement/application |
| Redmine | Optionnel | Oui | liens issues, contexte actif/application |
| OTRS/Znuny | Optionnel | Oui | liens tickets, contexte actif/application |

## Données synchronisables

Données sortantes d'OpenInfra vers ITSM :

- CI équipement ;
- CI application ;
- CI service métier ;
- localisation physique ;
- dépendances critiques ;
- propriétaire ;
- criticité ;
- statut ;
- support constructeur ;
- support tiers ;
- garantie ;
- liens de dépendance ;
- IP/DNS ;
- informations DCIM ;
- exposition ;
- risques ;
- dernier état découvert.

Données entrantes depuis ITSM :

- identifiant ticket externe ;
- URL ticket externe ;
- statut externe ;
- type externe ;
- priorité externe ;
- lien vers CI externe ;
- horodatage de synchronisation ;
- identifiant système source.

## Règles de non-écrasement

Un connecteur ITSM ne doit jamais écraser silencieusement :

- le support constructeur ;
- la garantie constructeur ;
- les données RSOT (Ressource Source of Truth) certifiées ;
- les relations critiques validées ;
- les champs dont la source autoritative n'est pas l'ITSM.

En cas de divergence, OpenInfra crée un conflit explicite avec :

- source A ;
- source B ;
- attribut concerné ;
- valeur actuelle ;
- valeur proposée ;
- score de confiance ;
- date de découverte ;
- règle de résolution applicable.

## Sécurité des connecteurs

Chaque connecteur doit :

- utiliser OAuth2, token API, mTLS ou mécanisme officiel supporté par l'outil cible ;
- stocker les secrets dans Vault ou magasin de secrets chiffré ;
- appliquer RBAC ;
- journaliser les synchronisations ;
- masquer les secrets ;
- appliquer rate limiting ;
- gérer retry avec backoff ;
- disposer d'une dead-letter queue ;
- supporter dry-run ;
- être désactivable sans impact sur la RSOT (Ressource Source of Truth).

## Critères d'acceptation

- Un connecteur Pro/Entreprise peut synchroniser un CI sans créer de ticket interne OpenInfra.
- Un ticket externe peut être lié à un actif OpenInfra sans être copié comme ticket natif.
- Une panne ITSM n'empêche pas l'usage du référentiel OpenInfra.
- Une divergence ITSM vs OpenInfra crée un conflit explicite.
- Les connecteurs respectent les feature gates d'édition.
- Les connecteurs ne sont pas installés ni activables en Lite.

