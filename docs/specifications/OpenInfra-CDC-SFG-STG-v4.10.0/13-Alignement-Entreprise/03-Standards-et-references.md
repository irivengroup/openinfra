# Standards et références d'alignement

Ce document liste les références utilisées pour cadrer la version 4.3.0. Les références servent d'inspiration et de garde-fous ; elles ne transforment pas OpenInfra en implémentation certifiée d'un référentiel donné.

## Ingénierie des exigences

- ISO/IEC/IEEE 29148 — ingénierie des exigences systèmes et logiciels.

## Sécurité applicative

- OWASP ASVS — base de vérification des contrôles de sécurité web/API.
- NIST Cybersecurity Framework 2.0 — gouvernance et gestion du risque cyber.

## API

- OpenAPI Specification 3.1 — description standard des API HTTP.
- GraphQL Specification — contrats de requêtes relationnelles contrôlées.

## Exploitation

- PostgreSQL documentation — partitionnement, réplication, observabilité SQL.
- Kubernetes/CNCF — déploiements résilients, stateless, probes, scaling, observabilité.

## Intégrations ITSM externes

- ServiceNow REST/CMDB APIs.
- Jira Service Management REST APIs.
- GLPI REST API.
- Freshservice APIs.
- APIs publiques Zendesk, Zammad, Redmine, OTRS/Znuny selon disponibilité et version.

## Limites

- OpenInfra ne revendique pas une conformité formelle sans audit externe.
- Les connecteurs ITSM doivent être validés par version cible de chaque outil.
- Les champs ITSM synchronisés doivent être paramétrables, car les modèles clients diffèrent.

