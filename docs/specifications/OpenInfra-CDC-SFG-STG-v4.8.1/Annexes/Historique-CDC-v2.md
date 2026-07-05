# Cahier des charges enterprise — OpenInfra
## Ressources Inventory, DCIM, ITAM, Discovery, Dependency Mapping et IPAM avancé, sans fonction ITSM intégrée

**Version :** 2.0 Entreprise  
**Date :** 2026-07-02  
**Produit cible :** OpenInfra  
**Nature :** solution open source de référentiel d’infrastructure, DCIM, ITAM, autodécouverte, cartographie de dépendances et IPAM avancé  
**Statut :** cahier des charges consolidé, exploitable pour cadrage, consultation, conception, backlog produit et validation d’architecture  
**Niveau d’exigence :** enterprise / production critique / forte volumétrie  
**Exclusion structurante :** aucune fonction ITSM intégrée.

---

## 0. Résumé exécutif

OpenInfra doit être une plateforme open source d’enterprise jouant le rôle de **référentiel central d’infrastructure** et de **Ressources Inventory** pour les actifs physiques, virtuels, cloud, réseau, applicatifs, logiciels, IP, dépendances, localisations, contrats et capacités.

La solution doit reprendre les grands blocs fonctionnels d’une solution de type Device42 : inventaire, autodécouverte, DCIM, ITAM, IPAM, dépendances, API, imports/exports et visualisations, tout en supprimant toute fonction de ticketing ou ITSM intégrée. OpenInfra doit rester interopérable avec les outils ITSM externes, mais ne doit pas devenir un outil de gestion d’incidents, de demandes ou de changements.

OpenInfra doit être conçu dès l’origine pour :

- fonctionner en haute disponibilité ;
- supporter de très fortes volumétries ;
- utiliser PostgreSQL Cluster comme socle transactionnel principal ;
- supporter plus de **10 000 000 000 d’entrées** ;
- maintenir des temps de réponse faibles sur les requêtes critiques ;
- supporter de nombreux utilisateurs simultanés ;
- exécuter des imports massifs ;
- piloter des scans distribués ;
- garantir l’intégrité transactionnelle des réservations IP ;
- fournir une localisation physique univoque et immédiate de tout équipement.

Dans une salle technique ou un datacenter, la localisation doit obligatoirement inclure la **ligne** et la **colonne**. Cette exigence est de niveau 1, car elle réduit directement le temps d’intervention et le risque d’erreur de manipulation.

---

## 1. Objectifs métier

### 1.1 Objectif principal

Créer une solution open source professionnelle permettant à une enterprise de disposer d’un référentiel unique, fiable, historisé, interrogeable et exploitable pour piloter son infrastructure IT, ses datacenters, ses réseaux, ses adresses IP, ses dépendances applicatives et ses actifs.

### 1.2 Objectifs opérationnels

OpenInfra doit permettre :

1. de savoir précisément **ce qui existe** ;
2. de savoir **où se trouve physiquement chaque équipement** ;
3. de savoir **à quoi chaque équipement est connecté** ;
4. de savoir **quelle application dépend de quel composant** ;
5. de savoir **quelles IP, VLAN, VRF, DNS et DHCP sont utilisés** ;
6. de savoir **qui est propriétaire de chaque actif** ;
7. de savoir **quel est le statut, le cycle de vie et la criticité de chaque objet** ;
8. de fiabiliser les interventions en salle ;
9. de préparer les migrations, audits, remplacements, capacity planning et opérations de sécurité ;
10. d’alimenter les outils externes ITSM, SIEM, supervision, IAM, automatisation et reporting.

### 1.3 Objectifs de conformité enterprise

La solution doit être conçue selon une approche compatible avec les pratiques suivantes :

- ingénierie des exigences structurée ;
- exigences identifiables, vérifiables et traçables ;
- sécurité applicative vérifiable ;
- défense en profondeur ;
- gouvernance des risques cybersécurité ;
- architecture haute disponibilité ;
- supervision et exploitabilité ;
- CI/CD complète ;
- tests automatisés ;
- auditabilité ;
- réversibilité ;
- documentation d’exploitation.

---

## 2. Références structurantes

Ce cahier des charges s’aligne sur les pratiques et référentiels suivants :

| Référence | Usage dans OpenInfra |
|---|---|
| ISO/IEC/IEEE 29148 | Structuration des exigences, exigences vérifiables, traçabilité |
| OWASP ASVS v5 | Exigences de sécurité applicative et API |
| NIST Cybersecurity Framework 2.0 | Gouvernance cybersécurité, gestion des risques, fonctions Identify/Protect/Detect/Respond/Recover/Govern |
| PostgreSQL Documentation | Haute disponibilité, partitionnement, indexation, réplication, performance |
| OpenAPI Specification | Documentation API REST |
| OAuth2/OIDC | Authentification moderne et fédération d’identité |
| SAML2 | Fédération d’identité enterprise |
| Prometheus/OpenTelemetry | Observabilité, métriques, traces |
| SPDX/CycloneDX | SBOM et supply chain logicielle |
| Semantic Versioning | Versionnement produit et compatibilité API |

Ces références ne transforment pas OpenInfra en solution certifiée par défaut. Elles imposent un niveau de conception, de documentation, de vérification et d’exploitation conforme aux pratiques attendues en enterprise.

---

## 3. Définitions et acronymes

| Terme | Définition |
|---|---|
| Ressources Inventory | Référentiel considéré comme source fiable et prioritaire d’une information |
| CMDB | Configuration Management Database, référentiel des éléments de configuration et relations |
| DCIM | Data Center Infrastructure Management, gestion des infrastructures physiques de datacenter |
| ITAM | IT Asset Management, gestion des actifs IT et de leur cycle de vie |
| SAM | Software Asset Management, gestion des logiciels, versions et licences |
| IPAM | IP Address Management, gestion des adresses IP, réseaux, VRF, VLAN, DNS/DHCP |
| VRF | Virtual Routing and Forwarding, table de routage logique isolée |
| VLAN | Virtual Local Area Network, segmentation logique L2 |
| VXLAN/VNI | Virtual Extensible LAN / VXLAN Network Identifier |
| PDU | Power Distribution Unit, unité de distribution électrique |
| UPS | Uninterruptible Power Supply, alimentation sans interruption |
| RPO | Recovery Point Objective, perte de données maximale acceptable |
| RTO | Recovery Time Objective, temps maximal acceptable de rétablissement |
| RBAC | Role-Based Access Control, contrôle d’accès par rôles |
| ABAC | Attribute-Based Access Control, contrôle d’accès par attributs |
| SLO | Service Level Objective, objectif de niveau de service |
| SLA | Service Level Agreement, engagement contractuel de service |
| CI/CD | Continuous Integration / Continuous Delivery |
| mTLS | Mutual TLS, authentification mutuelle par certificats |
| PITR | Point-In-Time Recovery, restauration à un point précis dans le temps |
| WAL | Write-Ahead Log PostgreSQL |
| BRIN | Block Range Index, index PostgreSQL adapté aux très grandes tables corrélées physiquement |
| GIN/GiST | Types d’index PostgreSQL adaptés aux recherches complexes |

---

## 4. Périmètre

### 4.1 Périmètre inclus

OpenInfra doit couvrir obligatoirement :

| Domaine | Couverture obligatoire |
|---|---|
| Ressources Inventory | Objets, relations, statuts, propriétaires, historique, confiance, preuve |
| CMDB technique | CIs, relations, dépendances, impact analysis, service mapping |
| DCIM | Sites, bâtiments, salles, lignes, colonnes, racks, U, câbles, puissance, environnement |
| ITAM | Actifs, cycle de vie, coûts, contrats, garanties, fournisseurs, stocks |
| SAM | Logiciels, versions, installations, licences, conformité, fin de support |
| Discovery | Agentless, agent optionnel, collectors distribués, planification, preuves |
| Dependency Mapping | Graphes techniques, applicatifs, réseau, stockage, puissance, cloud |
| IPAM avancé | IPv4, IPv6, VRF, VLAN, VXLAN, DHCP, DNS, NAT, réservations transactionnelles |
| API | REST, GraphQL, Webhooks, SDK, CLI |
| Import/export | CSV, XLSX, JSON, YAML, API bulk, streaming, dry-run, rollback |
| Sécurité | SSO, RBAC, ABAC, audit, chiffrement, secrets, rate limiting |
| Exploitation | HA, sauvegarde, restauration, monitoring, logs, traces, métriques |
| DevSecOps | CI/CD, tests, sécurité, packaging, SBOM, migration validation |

### 4.2 Périmètre exclu

OpenInfra ne doit pas inclure :

- gestion native de tickets ;
- portail utilisateur de support ;
- incidents ITSM ;
- demandes ITSM ;
- problèmes ITIL ;
- change management ITIL intégré ;
- workflows de validation de tickets ;
- base de connaissances support ;
- SLA de ticketing ;
- moteur de workflow ITSM natif.

### 4.3 Intégration ITSM externe

OpenInfra doit s’intégrer avec des solutions ITSM externes sans se substituer à elles :

- ServiceNow ;
- Jira Service Management ;
- GLPI ;
- Redmine ;
- Freshservice ;
- Zammad ;
- OTRS/Znuny ;
- connecteurs génériques REST/Webhook.

Les intégrations doivent permettre :

- enrichissement de tickets par données OpenInfra ;
- synchronisation de CIs vers l’ITSM ;
- consultation des tickets liés depuis une fiche actif ;
- création d’événements ou webhooks vers ITSM ;
- aucun stockage natif de ticket comme objet principal OpenInfra.

---

## 5. Exigences de niveau 1 obligatoires

Les exigences de niveau 1 sont bloquantes. Une version d’OpenInfra ne peut être considérée conforme si une exigence de niveau 1 applicable n’est pas implémentée, testée, documentée et validée.

| ID | Exigence obligatoire | Critère d’acceptation |
|---|---|---|
| N1-001 | PostgreSQL Cluster doit être le socle principal de persistance transactionnelle | Toutes les entités transactionnelles critiques sont persistées dans PostgreSQL ; les autres stockages ne sont pas sources de vérité |
| N1-002 | La base doit être conçue pour plus de 10 milliards d’entrées | Modèle partitionné, indexé, benchmarké et documenté ; stratégie d’archivage et de requêtes critiques validée |
| N1-003 | La localisation en salle doit inclure ligne et colonne | Aucun équipement physique en salle ne peut être validé sans ligne et colonne |
| N1-004 | Les réservations IP doivent être transactionnelles et concurrentes | Tests de concurrence prouvant zéro collision sur allocations simultanées |
| N1-005 | Les imports massifs doivent être asynchrones, validables et rollbackables | Import dry-run, commit, reprise, rapport d’erreur et rollback disponibles |
| N1-006 | Les scans distribués ne doivent pas bloquer l’usage interactif | Jobs asynchrones, files, backpressure, quotas et monitoring disponibles |
| N1-007 | Aucun module ITSM intégré ne doit être livré | Audit fonctionnel confirmant absence de ticketing natif |
| N1-008 | Les API doivent être paginées, sécurisées et documentées | OpenAPI/GraphQL schema, pagination obligatoire, authN/authZ, tests API |
| N1-009 | RBAC et audit doivent couvrir les opérations critiques | Chaque opération critique produit un audit signé/loggué et vérifiable |
| N1-010 | Les secrets ne doivent jamais être stockés ou exposés en clair | Tests sécurité et revue code confirmant chiffrement, masquage et rotation |
| N1-011 | La solution doit être hautement disponible | Déploiement multi-nœuds, health checks, failover PostgreSQL et reprise jobs testés |
| N1-012 | Les migrations doivent être versionnées et réversibles lorsque possible | Tests upgrade, compatibilité ascendante et rollback documentés |
| N1-013 | Les fonctionnalités doivent être livrées avec tests et documentation | CI complète, couverture minimale, documentation à jour |
| N1-014 | Les données critiques doivent avoir une intégrité forte | Contraintes, transactions, unicité, FK et validations métier en place |
| N1-015 | Les requêtes critiques doivent respecter les objectifs de latence | Benchmarks p95/p99 sur jeux de données représentatifs |

---

## 6. Principes d’architecture

### 6.1 Architecture logique cible

OpenInfra doit suivre une architecture modulaire, API-first, orientée domaine et conçue pour une extraction progressive vers microservices si la volumétrie le justifie.

```text
[Clients Web / CLI / SDK / Automatisation / ITSM externe]
                            |
                        [API Gateway]
                            |
        +-------------------+-------------------+
        |                   |                   |
   [REST API]          [GraphQL API]        [Webhook API]
        |                   |                   |
        +-------------------+-------------------+
                            |
                    [Application Layer]
                            |
 +--------------------------+----------------------------+
 |                          |                            |
[Domain Services]      [Async Job Platform]       [Integration Layer]
 |                          |                            |
 |-- Ressources Inventory         |-- Discovery Jobs           |-- ITSM
 |-- DCIM                    |-- Import Jobs              |-- Cloud
 |-- ITAM/SAM                |-- Reconciliation Jobs      |-- Hypervisors
 |-- IPAM                    |-- Dependency Jobs          |-- DNS/DHCP
 |-- Dependency Mapping      |-- Capacity Jobs            |-- Network APIs
 |-- RBAC/Audit              |-- Maintenance Jobs         |-- SIEM/IAM
 |-- Reporting                                          
                            |
                    [Persistence Layer]
                            |
 +--------------------------+----------------------------+
 |                          |                            |
[PostgreSQL Cluster]   [Cache Redis/KeyDB]    [Search Index]
[Object Storage]       [Queue/Event Bus]      [Metrics/Logs]
```

### 6.2 Découpage en modules

| Module | Responsabilité |
|---|---|
| `core` | tenants, utilisateurs, rôles, permissions, tags, champs personnalisés |
| `ri` | objets de référence, relations, statuts, historisation |
| `dcim` | sites, bâtiments, salles, racks, câbles, énergie, environnement |
| `itam` | actifs, contrats, garanties, coûts, fournisseurs, stocks |
| `sam` | logiciels, licences, installations, conformité |
| `ipam` | adresses, préfixes, VRF, VLAN, DNS/DHCP, réservations |
| `discovery` | collectors, jobs, observations, preuves, rapprochement |
| `dependency` | graphes, relations, impact analysis, business services |
| `integration` | connecteurs externes, webhooks, synchronisation |
| `audit` | événements d’audit, traçabilité, conformité |
| `ops` | jobs, locks, maintenance, partitions, santé plateforme |
| `reporting` | vues matérialisées, rapports, analytics |

### 6.3 Architecture applicative

La solution doit appliquer :

- Clean Architecture ;
- architecture hexagonale ;
- Domain-Driven Design pour les domaines complexes ;
- séparation stricte domaine / application / infrastructure / interface ;
- dépendances orientées vers le domaine ;
- interfaces de ports/adapters pour toutes les intégrations ;
- absence de logique métier dans les contrôleurs API ;
- absence de logique métier dans les modèles ORM ;
- transactions gérées au niveau application service ;
- erreurs métier explicites ;
- événements de domaine pour les changements significatifs.

### 6.4 Monolithe modulaire puis extraction sélective

La première implémentation doit privilégier un monolithe modulaire robuste, car il apporte :

- cohérence transactionnelle plus maîtrisable ;
- migrations plus simples ;
- livraison plus rapide ;
- testabilité supérieure ;
- exploitation plus économique ;
- évolutivité suffisante via scalabilité horizontale applicative et PostgreSQL cluster.

Une extraction microservice n’est autorisée que si :

- une frontière métier est stabilisée ;
- les contrats API sont versionnés ;
- les tests contractuels existent ;
- l’observabilité est en place ;
- l’extraction ne casse aucune fonctionnalité existante ;
- la cohérence des données reste maîtrisée.

---

## 7. Modèle de données de référence

### 7.1 Principes généraux

Chaque objet OpenInfra doit disposer au minimum de :

- identifiant immuable ;
- tenant ;
- nom ;
- type ;
- statut ;
- source de vérité ;
- source d’origine ;
- propriétaire métier ;
- propriétaire technique ;
- criticité ;
- environnement ;
- tags ;
- attributs personnalisés contrôlés ;
- date de création ;
- date de modification ;
- auteur ou système d’origine ;
- version optimiste ;
- historique ;
- preuve de découverte si applicable ;
- score de confiance si applicable.

### 7.2 Gestion des statuts

Statuts standards :

- planned ;
- ordered ;
- received ;
- stocked ;
- staged ;
- active ;
- maintenance ;
- degraded ;
- retired ;
- disposed ;
- unknown ;
- discovered-unmatched ;
- conflict ;
- quarantined.

Les statuts doivent être extensibles par tenant, mais les statuts système ne doivent pas être supprimables.

### 7.3 Relations

Relations obligatoires :

| Relation | Sens |
|---|---|
| located_in | équipement vers localisation |
| mounted_in | équipement vers rack/U |
| connected_to | port vers port |
| powered_by | équipement vers PDU/circuit |
| depends_on | composant vers composant requis |
| hosts | hôte vers VM/conteneur/service |
| runs_on | application/service vers hôte |
| assigned_to | actif vers personne/équipe |
| owns | propriétaire vers objet |
| protected_by | service vers dispositif de sécurité |
| replicated_to | composant vers cible de réplication |
| backed_up_by | objet vers solution de sauvegarde |
| exposed_by | service vers VIP/load balancer/API gateway |
| belongs_to | objet vers groupe/tenant/site |
| replaces | actif vers actif remplacé |
| linked_to_ticket_external | objet vers référence ITSM externe |

### 7.4 Historisation

Les changements critiques doivent produire une version d’objet :

- snapshot avant/après ;
- diff ;
- utilisateur ou service account ;
- source ;
- horodatage UTC ;
- corrélation de requête ;
- justification si fournie ;
- identifiant de job si applicable ;
- trace de validation métier.

---

## 8. DCIM — exigences détaillées

### 8.1 Hiérarchie physique

OpenInfra doit gérer la hiérarchie suivante :

```text
Pays
 └── Région
      └── Ville
           └── Site
                └── Bâtiment
                     └── Étage
                          └── Salle technique / Datacenter
                               ├── Zone
                               ├── Ligne
                               ├── Colonne
                               ├── Rangée
                               ├── Rack / Baie
                               └── Équipement hors rack
```

### 8.2 Localisation physique univoque

Pour tout équipement physique, la localisation doit permettre une intervention immédiate. Le chemin doit être humainement lisible et techniquement stable.

Exemple :

```text
FR / Paris / DC-Lumière / Bâtiment B / Niveau -1 / Salle THD-01 / Zone Réseau / Ligne L04 / Colonne C12 / Rack R-L04-C12-03 / Face avant / U22-U23
```

Exigences :

- la ligne est obligatoire pour tout objet localisé dans une salle ;
- la colonne est obligatoire pour tout objet localisé dans une salle ;
- le rack est obligatoire pour tout équipement rackable installé ;
- la position U est obligatoire pour tout équipement installé en rack ;
- la face avant/arrière doit être gérée ;
- les équipements hors rack doivent disposer d’une position salle ligne/colonne ;
- les coordonnées X/Y doivent être disponibles pour plan graphique ;
- le chemin de localisation doit être exportable en QR code et code-barres ;
- toute modification de localisation doit être auditée.

### 8.3 Grille de salle

Chaque salle doit permettre de définir :

- système de coordonnées ;
- nombre de lignes ;
- nombre de colonnes ;
- conventions de nommage ;
- orientation nord/sud/est/ouest ;
- zones froides/chaudes ;
- allées ;
- zones interdites ;
- surfaces réservées ;
- capacités électriques par zone ;
- capacités thermiques par zone.

### 8.4 Racks et baies

OpenInfra doit gérer :

- rack standard 19 pouces ;
- rack réseau ;
- rack serveur ;
- baie opérateur ;
- châssis ;
- hauteur en U ;
- largeur ;
- profondeur ;
- poids maximum ;
- charge réelle ;
- capacité électrique ;
- orientation ;
- face avant/arrière ;
- équipements pleine profondeur ;
- équipements demi-profondeur ;
- équipements fractional-U ;
- panneaux de brassage ;
- tiroirs optiques ;
- PDU verticales et horizontales ;
- accessoires ;
- emplacements réservés ;
- conflits U ;
- collisions profondeur/face ;
- réservations futures.

### 8.5 Visualisations DCIM

L’interface doit fournir :

- plan de salle ;
- grille ligne/colonne ;
- vue rack elevation avant/arrière ;
- vue occupation U ;
- vue câblage ;
- vue alimentation ;
- vue thermique ;
- vue capacité ;
- vue spare parts ;
- vue changements récents ;
- export SVG/PNG/PDF ;
- fiche intervention imprimable ;
- scan QR code mobile.

### 8.6 Câblage

OpenInfra doit gérer :

- câbles cuivre ;
- câbles fibre ;
- câbles DAC ;
- câbles AOC ;
- câbles console ;
- câbles alimentation ;
- panneaux de brassage ;
- ports ;
- transceivers ;
- jarretières ;
- circuits multi-segments ;
- couleurs ;
- longueurs ;
- chemins ;
- étiquettes ;
- statut ;
- historique ;
- validation de compatibilité port/média ;
- détection de connexion incohérente.

### 8.7 Énergie

OpenInfra doit modéliser :

- arrivée électrique ;
- tableau ;
- disjoncteur ;
- circuit ;
- phase ;
- UPS ;
- PDU ;
- prise ;
- alimentation serveur ;
- chaîne A/B ;
- redondance ;
- capacité nominale ;
- consommation réelle ;
- surcharge ;
- marge ;
- historisation ;
- simulation d’ajout ;
- analyse de risque de coupure.

### 8.8 Environnement et capacité

OpenInfra doit gérer :

- température ;
- humidité ;
- pression ;
- airflow ;
- capteurs ;
- zones froides/chaudes ;
- alertes ;
- tendances ;
- capacité thermique ;
- seuils ;
- corrélation rack/zone ;
- capacité espace ;
- capacité U ;
- capacité puissance ;
- capacité refroidissement ;
- projections.

---

## 9. ITAM et SAM

### 9.1 IT Asset Management

OpenInfra doit gérer le cycle de vie complet des actifs :

1. planification ;
2. commande ;
3. réception ;
4. stockage ;
5. préparation ;
6. installation ;
7. production ;
8. maintenance ;
9. transfert ;
10. retrait ;
11. recyclage ;
12. destruction ;
13. preuve de destruction.

### 9.2 Données d’actif

Chaque actif doit contenir :

- asset tag ;
- numéro de série ;
- constructeur ;
- modèle ;
- SKU ;
- type ;
- statut ;
- date d’achat ;
- date de réception ;
- fournisseur ;
- bon de commande ;
- contrat support ;
- garantie ;
- coût ;
- devise ;
- centre de coût ;
- propriétaire ;
- responsable technique ;
- localisation ;
- criticité ;
- conformité ;
- historique ;
- pièces associées ;
- documents attachés.

### 9.3 Contrats, garanties et fournisseurs

OpenInfra doit gérer :

- contrats support ;
- contrats maintenance ;
- garanties constructeur ;
- garanties étendues ;
- dates de début/fin ;
- renouvellements ;
- clauses critiques ;
- fournisseurs ;
- contacts ;
- SLA contractuels externes ;
- documents ;
- alertes d’expiration.

### 9.4 Software Asset Management

OpenInfra doit inventorier :

- systèmes d’exploitation ;
- packages ;
- logiciels ;
- versions ;
- services ;
- bases de données ;
- middlewares ;
- bibliothèques ;
- certificats ;
- clés de licence chiffrées si autorisé ;
- contrats logiciels ;
- métriques de licence ;
- installations découvertes ;
- installations déclarées ;
- écarts ;
- fin de support ;
- obsolescence ;
- vulnérabilités associées via intégration externe.

---

## 10. Discovery automatique

### 10.1 Principes

La découverte doit être :

- distribuée ;
- planifiable ;
- agentless par défaut ;
- compatible agent optionnel ;
- sécurisée ;
- auditable ;
- idempotente ;
- reprise sur erreur ;
- non bloquante ;
- isolée par tenant et périmètre ;
- compatible fenêtres de scan ;
- contrôlée par RBAC ;
- limitée en débit ;
- observable.

### 10.2 Collectors

Chaque collector doit :

- avoir une identité unique ;
- s’enregistrer auprès du serveur ;
- utiliser mTLS ;
- recevoir des jobs ;
- publier des résultats signés ;
- chiffrer localement les secrets si stockage temporaire nécessaire ;
- supprimer les secrets après usage ;
- fonctionner derrière NAT si nécessaire ;
- supporter proxy ;
- gérer les interruptions ;
- limiter le nombre de connexions simultanées ;
- adapter automatiquement ses workers aux ressources disponibles ;
- exposer métriques et logs.

### 10.3 Méthodes de découverte

| Source | Méthode obligatoire |
|---|---|
| Linux/Unix | SSH, commandes contrôlées, inventaire OS, paquets, services, interfaces |
| Windows | WinRM, WMI, PowerShell restreint |
| Réseau | SNMPv2c/v3, LLDP, CDP, ARP, MAC tables |
| VMware | vCenter API |
| Hyper-V | WinRM/PowerShell |
| KVM | libvirt |
| Kubernetes | API Kubernetes |
| Docker | API Docker |
| AWS | API AWS |
| Azure | API Azure |
| GCP | API GCP |
| OpenStack | API OpenStack |
| DNS | zone transfer contrôlé, API, import zone |
| DHCP | leases, scopes, API |
| LDAP/AD | LDAP/LDAPS |
| PDU/UPS | SNMP/API |
| Storage | SNMP/API constructeur |
| Load balancers | API/SNMP/config export |
| Firewalls | API/SNMP/config export |
| Certificats | TLS scan, API, fichiers déclarés |

### 10.4 Rapprochement

Le moteur de rapprochement doit utiliser :

- numéro de série ;
- asset tag ;
- UUID matériel ;
- cloud resource ID ;
- vCenter MoRef ;
- Kubernetes UID ;
- hostname ;
- FQDN ;
- MAC address ;
- IP ;
- DNS ;
- modèle ;
- emplacement ;
- signature multi-critères ;
- score de confiance ;
- règles configurables.

### 10.5 Gestion des conflits

Aucune donnée de Ressources Inventory ne doit être écrasée silencieusement par la découverte. Un conflit doit être créé lorsque :

- la valeur découverte diverge de la valeur déclarée ;
- deux sources fiables donnent des valeurs différentes ;
- un objet est découvert sans correspondance ;
- un objet déclaré n’est plus découvert ;
- une adresse IP est active mais non déclarée ;
- une IP déclarée est inactive depuis une durée configurable.

Un conflit doit contenir :

- objet concerné ;
- attribut divergent ;
- valeur actuelle ;
- valeur découverte ;
- source ;
- fraîcheur ;
- score de confiance ;
- preuve ;
- résolution ;
- décision ;
- utilisateur ou règle ayant résolu.

---

## 11. Dependency Mapping

### 11.1 Objectif

OpenInfra doit produire une cartographie des dépendances permettant d’analyser les impacts techniques et métiers d’un incident, d’une migration, d’une opération de maintenance ou d’un changement externe.

### 11.2 Types de dépendances

OpenInfra doit gérer :

- application vers service ;
- service vers processus ;
- processus vers serveur ;
- serveur vers VM ;
- VM vers hyperviseur ;
- conteneur vers nœud ;
- pod vers service Kubernetes ;
- application vers base de données ;
- application vers queue ;
- application vers API ;
- serveur vers stockage ;
- serveur vers réseau ;
- interface vers switchport ;
- switchport vers VLAN ;
- VLAN vers subnet ;
- subnet vers VRF ;
- équipement vers rack ;
- équipement vers PDU ;
- PDU vers circuit ;
- circuit vers tableau ;
- certificat vers endpoint ;
- logiciel vers licence ;
- actif vers contrat.

### 11.3 Sources de dépendances

Sources possibles :

- connexions réseau observées ;
- ports écoutés ;
- processus ;
- configurations ;
- DNS ;
- load balancers ;
- ingress Kubernetes ;
- service mesh ;
- cloud security groups ;
- firewall policies ;
- traces applicatives ;
- données déclaratives ;
- imports ;
- tags ;
- annotations ;
- API externes.

### 11.4 Graphe

Le graphe de dépendances doit :

- être versionné ;
- être historisé ;
- supporter les requêtes de voisinage ;
- supporter les chemins courts ;
- supporter l’impact analysis ;
- limiter la profondeur pour préserver les performances ;
- permettre exports GraphML/DOT/JSON/SVG ;
- appliquer les permissions d’accès ;
- distinguer dépendance déclarée, découverte et inférée ;
- calculer un score de confiance.

---

## 12. IPAM avancé

### 12.1 Périmètre IPAM

OpenInfra doit gérer :

- IPv4 ;
- IPv6 ;
- RIR ;
- LIR ;
- ASN ;
- plages ASN ;
- aggregates ;
- supernets ;
- prefixes ;
- subnets ;
- ranges ;
- IP addresses ;
- réservations ;
- allocations ;
- DHCP scopes ;
- DHCP leases ;
- DNS zones ;
- DNS records ;
- reverse zones ;
- VRF ;
- route distinguishers ;
- route targets ;
- VLAN ;
- VLAN groups ;
- VXLAN/VNI ;
- EVPN ;
- NAT ;
- VIP ;
- anycast ;
- loopbacks ;
- point-to-point ;
- interfaces ;
- MAC addresses ;
- FHRP groups ;
- HSRP/VRRP/GLBP.

### 12.2 IPv4/IPv6

Exigences :

- parité fonctionnelle IPv4/IPv6 ;
- validation CIDR stricte ;
- recherche exacte ;
- recherche par plage ;
- recherche par parent ;
- hiérarchie automatique ;
- calcul capacité ;
- réservations ;
- rôles ;
- statuts ;
- associations DNS/DHCP ;
- associations interface ;
- historique ;
- audit.

### 12.3 VRF et chevauchement

OpenInfra doit permettre :

- adresses chevauchantes entre VRF ;
- unicité forcée par VRF si activée ;
- table globale ;
- route distinguisher ;
- route targets import/export ;
- tenant par VRF ;
- site par VRF ;
- environnement ;
- politiques d’allocation ;
- vues par VRF ;
- API tenant-aware.

### 12.4 Allocation transactionnelle

L’allocation IP doit être atomique et sûre en concurrence.

Exigences :

- next available IP transactionnel ;
- réservation sans collision ;
- verrou fin par préfixe ou plage ;
- idempotency key ;
- expiration de réservation ;
- commit explicite ;
- rollback ;
- audit ;
- intégration DNS/DHCP transactionnelle lorsque possible ;
- rollback compensatoire si un système externe échoue ;
- tests de concurrence.

### 12.5 DNS/DHCP

OpenInfra doit intégrer :

- BIND ;
- PowerDNS ;
- Microsoft DNS ;
- Kea DHCP ;
- ISC DHCP legacy ;
- Microsoft DHCP ;
- DNSForge si retenu dans l’écosystème ;
- connecteurs génériques API.

Fonctions :

- import zones ;
- import reverse zones ;
- corrélation A/AAAA/PTR ;
- détection DNS orphelin ;
- détection PTR manquant ;
- détection conflit DHCP/réservation ;
- prévisualisation écriture ;
- commit ;
- rollback ;
- audit.

### 12.6 Détection d’anomalies IPAM

OpenInfra doit détecter :

- IP dupliquée dans même VRF ;
- subnet chevauchant interdit ;
- IP hors préfixe ;
- range hors préfixe ;
- VLAN incohérent ;
- DNS contradictoire ;
- PTR absent ;
- PTR orphelin ;
- DHCP lease sur IP réservée ;
- MAC multiple ;
- interface multiple ;
- gateway dupliquée ;
- route incohérente ;
- IP active non déclarée ;
- IP déclarée inactive ;
- pool proche saturation.

---

## 13. Persistance PostgreSQL Cluster

### 13.1 Rôle de PostgreSQL

PostgreSQL Cluster est la persistance transactionnelle principale. Les autres systèmes sont auxiliaires.

| Stockage | Rôle | Source de vérité |
|---|---|---|
| PostgreSQL Cluster | transactions, référentiel, relations, IPAM, audit, jobs | Oui |
| Redis/KeyDB | cache, locks courts, rate limiting | Non |
| OpenSearch-compatible | recherche full-text, exploration | Non |
| Object storage | pièces jointes, imports bruts, exports, backups applicatifs | Non pour objets métier |
| Queue/Event bus | traitement asynchrone | Non |
| Metrics storage | métriques d’observabilité | Non |

### 13.2 Topologie HA minimale

```text
                    [VIP / HAProxy / PgBouncer]
                              |
              +---------------+---------------+
              |                               |
       [PostgreSQL Primary]          [Read Replicas]
              |
   +----------+----------+
   |                     |
[Synchronous Standby] [Async Standby]
              |
       [Backup / PITR / DR]
```

Exigences :

- Patroni ou mécanisme équivalent de failover ;
- consensus etcd/Consul si Patroni ;
- PgBouncer ;
- HAProxy ou équivalent ;
- réplication synchrone pour données critiques si exigence RPO stricte ;
- réplication asynchrone pour lecture et DR ;
- PITR ;
- WAL archiving ;
- tests de bascule ;
- runbooks.

### 13.3 Schémas PostgreSQL

| Schéma | Contenu |
|---|---|
| `core` | tenants, utilisateurs, rôles, permissions, tags, custom fields |
| `ri` | objets de référence, relations, statuts |
| `dcim` | sites, bâtiments, salles, racks, câbles, énergie, capteurs |
| `itam` | actifs, contrats, garanties, coûts, stocks |
| `sam` | logiciels, licences, installations |
| `ipam` | VRF, prefixes, IP, VLAN, DNS/DHCP, réservations |
| `discovery` | collectors, jobs, observations, preuves |
| `dependency` | graphes, nœuds, arêtes, versions |
| `audit` | audit logs |
| `history` | versions d’objets |
| `integration` | connecteurs, mappings, synchros |
| `ops` | jobs, locks, maintenance, outbox |
| `reporting` | vues matérialisées, agrégats |

### 13.4 Tables partitionnées obligatoires

| Table | Partitionnement |
|---|---|
| `audit.audit_event` | temps + hash tenant |
| `history.object_version` | temps + type objet |
| `discovery.observation` | temps + hash collector/tenant |
| `discovery.scan_result` | temps + job |
| `ipam.ip_observation` | temps + VRF/hash |
| `ipam.dhcp_lease_history` | temps + VRF |
| `dependency.edge_event` | temps + graph |
| `dcim.sensor_metric` | temps + salle/rack |
| `ops.outbox_event` | temps + statut |
| `ops.job_event` | temps + job type |

### 13.5 Indexation

Index obligatoires selon usages :

- B-tree sur identifiants, tenant, statuts, noms normalisés ;
- index composites tenant + clé métier ;
- index partiels sur objets actifs ;
- index couvrants pour listes critiques ;
- GIN sur JSONB uniquement pour champs filtrables validés ;
- GiST/SP-GiST pour plages et réseaux si applicable ;
- BRIN sur tables temporelles massives ;
- trigrammes pour recherche floue ;
- contraintes d’exclusion pour plages IP si adaptées ;
- index uniques tenant-aware.

### 13.6 Stratégie 10 milliards d’entrées

Pour dépasser 10 milliards d’entrées sans dégrader les requêtes critiques :

- séparer état courant et événements historiques ;
- stocker l’état courant dans tables fortement indexées ;
- stocker les observations massives dans tables append-only partitionnées ;
- limiter les index sur données froides ;
- utiliser partitions temporelles et hash ;
- archiver les partitions froides ;
- utiliser vues matérialisées pour dashboards ;
- forcer pagination et timeouts ;
- interdire les exports synchrones non filtrés ;
- utiliser COPY/bulk insert pour gros imports ;
- déplacer lectures analytiques vers réplicas ;
- mesurer p95/p99 ;
- maintenir statistiques PostgreSQL ;
- surveiller requêtes lentes et locks ;
- prévoir maintenance vacuum/analyze adaptée ;
- documenter les limites par endpoint.

---

## 14. API, CLI et intégrations

### 14.1 API REST

L’API REST doit couvrir 100 % des fonctionnalités métier exposées en UI.

Exigences :

- OpenAPI versionné ;
- pagination obligatoire ;
- filtrage ;
- tri ;
- champs sélectionnables ;
- rate limiting ;
- idempotency keys pour commandes critiques ;
- codes d’erreur normalisés ;
- corrélation request ID ;
- authN/authZ ;
- audit ;
- compatibilité ascendante ;
- dépréciation documentée.

### 14.2 API GraphQL

GraphQL doit être utilisé pour :

- navigation de relations ;
- graphes de dépendances ;
- vues composées ;
- requêtes DCIM enrichies ;
- exploration IPAM hiérarchique.

Contraintes :

- limitation de profondeur ;
- limitation de complexité ;
- autorisation par champ ;
- pagination obligatoire ;
- introspection contrôlée ;
- audit des requêtes sensibles.

### 14.3 Webhooks

Webhooks obligatoires :

- asset.created ;
- asset.updated ;
- asset.deleted ;
- location.changed ;
- ip.reserved ;
- ip.released ;
- ip.conflict.detected ;
- discovery.completed ;
- discovery.failed ;
- import.completed ;
- import.failed ;
- dependency.changed ;
- capacity.threshold.reached ;
- contract.expiring ;
- certificate.expiring ;
- audit.security_event.

### 14.4 CLI et SDK

OpenInfra doit fournir :

- CLI officielle ;
- SDK Python ;
- SDK Go ;
- exemples Ansible ;
- provider Terraform planifié ;
- collections Postman/Bruno ;
- documentation API ;
- exemples d’automatisation.

---

## 15. Interface utilisateur

### 15.1 Principes UX

L’interface doit être :

- claire ;
- rapide ;
- orientée exploitation ;
- adaptée aux grands volumes ;
- filtrable ;
- paginée ;
- accessible ;
- utilisable en salle via tablette ;
- capable de scanner QR code/code-barres ;
- compatible mode sombre ;
- orientée intervention.

### 15.2 Écrans obligatoires

- dashboard global ;
- dashboard DCIM ;
- dashboard IPAM ;
- dashboard discovery ;
- dashboard dépendances ;
- dashboard capacité ;
- recherche globale ;
- liste actifs ;
- fiche actif ;
- fiche rack ;
- fiche salle ;
- plan salle ligne/colonne ;
- rack elevation ;
- graphe dépendances ;
- vue impact analysis ;
- vue prefixes/IP ;
- réservation IP ;
- import/export ;
- conflits ;
- jobs ;
- collectors ;
- connecteurs ;
- audit ;
- administration RBAC.

---

## 16. Sécurité

### 16.1 Authentification

OpenInfra doit supporter :

- OIDC ;
- SAML2 ;
- LDAP/LDAPS ;
- Active Directory ;
- authentification locale désactivable ;
- MFA via IdP ;
- service accounts ;
- tokens API ;
- rotation ;
- révocation ;
- expiration ;
- sessions sécurisées.

### 16.2 Autorisation

Contrôle d’accès obligatoire :

- RBAC ;
- permissions fines ;
- scopes tenant/site/environnement ;
- permissions objet ;
- permissions champ sensible ;
- séparation lecture/écriture/admin ;
- séparation discovery/import/export ;
- séparation secrets ;
- délégation contrôlée.

ABAC recommandé pour :

- criticité ;
- environnement ;
- localisation ;
- propriétaire ;
- source ;
- tag ;
- tenant.

### 16.3 Secrets

Exigences :

- aucun secret en clair ;
- chiffrement applicatif ;
- intégration Vault compatible ;
- rotation ;
- masquage UI ;
- masquage logs ;
- accès audité ;
- chiffrement au repos ;
- chiffrement en transit ;
- suppression après usage collector ;
- séparation des secrets par périmètre.

### 16.4 Durcissement applicatif

OpenInfra doit protéger contre :

- injection SQL ;
- XSS ;
- CSRF si cookies ;
- SSRF depuis discovery/connecteurs ;
- path traversal ;
- désérialisation dangereuse ;
- upload malveillant ;
- brute force ;
- escalade de privilèges ;
- exposition de secrets ;
- IDOR/BOLA ;
- abus d’API ;
- requêtes coûteuses non bornées.

### 16.5 Audit sécurité

Audit obligatoire pour :

- connexions ;
- échecs de connexion ;
- modifications RBAC ;
- lecture secret ;
- création/modification/suppression objet critique ;
- import ;
- export ;
- réservation/libération IP ;
- lancement discovery ;
- changement connecteur ;
- modification localisation ;
- actions administratives ;
- changements de configuration.

---

## 17. Haute disponibilité, résilience et exploitation

### 17.1 Objectifs HA

| Composant | Exigence |
|---|---|
| API | multi-instances, stateless, load balanced |
| Workers | redémarrage automatique, jobs idempotents |
| Collectors | reprise après coupure, jobs rejouables |
| PostgreSQL | cluster HA, failover, backups, PITR |
| Cache | non source de vérité, perte tolérable |
| Queue | durable pour jobs critiques |
| Object storage | redondant, versionné si possible |

### 17.2 RPO/RTO

| Niveau | RPO | RTO |
|---|---:|---:|
| Standard | ≤ 1 minute | ≤ 5 minutes |
| Critique | ≤ 10 secondes | ≤ 2 minutes |
| DR distant | ≤ 15 minutes | ≤ 1 heure |

### 17.3 Sauvegarde/restauration

Exigences :

- sauvegarde complète ;
- sauvegarde incrémentale ;
- WAL archiving ;
- PITR ;
- tests de restauration automatisés ;
- restauration isolée ;
- chiffrement ;
- rétention ;
- immutabilité optionnelle ;
- documentation runbook ;
- alerte échec backup ;
- mesure RPO réel.

### 17.4 Maintenance

OpenInfra doit fournir :

- maintenance partitions ;
- purge contrôlée ;
- vacuum/analyze supervisé ;
- rotation logs ;
- rotation secrets ;
- vérification cohérence ;
- diagnostics ;
- health checks ;
- readiness checks ;
- liveness checks ;
- mode maintenance ;
- mode lecture seule dégradé.

---

## 18. Performance et scalabilité

### 18.1 Objectifs de performance

| Cas critique | Objectif p95 |
|---|---:|
| Recherche IP exacte | < 50 ms |
| Réservation IP | < 150 ms |
| Fiche actif | < 150 ms |
| Recherche équipement par nom exact | < 100 ms |
| Chemin de localisation | < 100 ms |
| Fiche rack | < 150 ms |
| Liste paginée 100 lignes | < 200 ms |
| Graphe dépendance niveau 1 | < 500 ms |
| Authentification via IdP | < 1 s hors latence IdP |
| Démarrage job asynchrone | < 500 ms |

### 18.2 Capacités minimales cibles

| Dimension | Cible minimale |
|---|---:|
| Utilisateurs simultanés | 500 |
| Requêtes API/minute | 10 000 |
| Collectors simultanés | 100 |
| Jobs asynchrones en file | 1 000 |
| Réservations IP concurrentes | 100 sans collision |
| Actifs référencés | ≥ 10 millions |
| Observations historiques | > 10 milliards |
| Préfixes IP | ≥ 10 millions |
| Adresses IP gérées | ≥ 1 milliard logique, avec matérialisation contrôlée |

### 18.3 Règles de conception performance

- pagination obligatoire ;
- curseurs pour gros volumes ;
- streaming exports ;
- bulk inserts ;
- backpressure ;
- queues ;
- workers auto-dimensionnés ;
- timeouts ;
- circuit breakers ;
- caches invalidables ;
- read replicas ;
- vues matérialisées ;
- requêtes préparées ;
- interdiction des scans non bornés ;
- limitation de profondeur GraphQL ;
- monitoring des requêtes lentes.

---

## 19. Observabilité

OpenInfra doit fournir :

- logs JSON ;
- request ID ;
- correlation ID ;
- traces OpenTelemetry ;
- métriques Prometheus ;
- dashboards Grafana ;
- alertes ;
- audit métier ;
- métriques DB ;
- métriques queues ;
- métriques collectors ;
- métriques discovery ;
- métriques IPAM ;
- métriques imports ;
- métriques API ;
- métriques sécurité.

Indicateurs obligatoires :

- latence p50/p95/p99 ;
- taux d’erreur ;
- saturation pool DB ;
- connexions PostgreSQL ;
- réplication lag ;
- locks longs ;
- requêtes lentes ;
- taille queues ;
- durée jobs ;
- taux d’échec discovery ;
- conflits ouverts ;
- fraîcheur des données ;
- backup success/failure ;
- RPO observé ;
- espace disque ;
- WAL ;
- partitions en retard.

---

## 20. Import/export massif

### 20.1 Formats

OpenInfra doit supporter :

- CSV ;
- XLSX ;
- JSON ;
- YAML ;
- API bulk ;
- ZIP signé ;
- exports Device42 ;
- exports NetBox ;
- exports Nautobot ;
- exports GLPI ;
- exports VMware ;
- exports cloud.

### 20.2 Processus import

Tout import doit suivre :

1. réception fichier ;
2. stockage objet ;
3. calcul hash ;
4. validation syntaxique ;
5. mapping ;
6. validation métier ;
7. dry-run ;
8. rapport d’impact ;
9. commit asynchrone ;
10. audit ;
11. rapport final ;
12. rollback si échec critique.

### 20.3 Exports

Exports obligatoires :

- CSV ;
- XLSX ;
- JSON ;
- YAML ;
- GraphML ;
- DOT ;
- SVG ;
- PDF rapport ;
- export streaming ;
- export incrémental ;
- export signé.

---

## 21. Migration et réversibilité

### 21.1 Sources de migration

OpenInfra doit prévoir des chemins de migration depuis :

- Device42 ;
- NetBox ;
- Nautobot ;
- GLPI ;
- spreadsheets ;
- exports CMDB internes ;
- DNS/DHCP existants ;
- vCenter ;
- cloud inventories ;
- scripts historiques.

### 21.2 Principes

Toute migration doit :

- être rejouable ;
- être auditable ;
- produire un rapport d’écarts ;
- préserver les identifiants externes ;
- conserver la source ;
- permettre dry-run ;
- permettre rollback applicatif ;
- documenter les règles de transformation ;
- gérer les conflits ;
- produire une matrice de correspondance.

---

## 22. DevSecOps, CI/CD et qualité

### 22.1 Pipeline obligatoire

La CI/CD doit inclure :

- checkout ;
- installation dépendances ;
- format check ;
- lint ;
- typage statique ;
- tests unitaires ;
- tests intégration ;
- tests API ;
- tests sécurité ;
- tests migrations ;
- tests performance ciblés ;
- couverture ;
- scan dépendances ;
- scan secrets ;
- SBOM ;
- build ;
- packaging ;
- vérification artefacts ;
- smoke tests ;
- publication uniquement si toutes les validations passent.

### 22.2 Couverture de tests

| Type | Objectif |
|---|---|
| Unitaires | règles métier, validations, allocations IP, relations |
| Intégration | PostgreSQL, API, discovery, imports |
| Fonctionnels | parcours UI/API critiques |
| Sécurité | RBAC, secrets, SSRF, injections, IDOR |
| Performance | requêtes critiques, imports, réservations IP |
| Concurrence | IPAM, jobs, imports, modifications concurrentes |
| Régression | non-régression fonctionnelle |
| Migration | upgrade/downgrade, compatibilité schéma |
| HA | failover PostgreSQL, reprise jobs |
| Packaging | images, charts, signatures, SBOM |

### 22.3 Critères de livraison

Aucune version ne doit être livrée si :

- une exigence N1 applicable échoue ;
- les tests critiques échouent ;
- la couverture minimale n’est pas atteinte ;
- une migration n’est pas testée ;
- une faille critique est détectée ;
- l’API documentée n’est pas alignée avec le code ;
- une fonctionnalité est documentée mais absente ;
- une fonctionnalité existante est supprimée sans remplacement compatible ;
- les artefacts contiennent caches ou fichiers temporaires.

---

## 23. Critères d’acceptation globaux

OpenInfra est conforme si :

1. la solution ne contient aucun module ITSM intégré ;
2. toutes les fonctionnalités critiques sont accessibles par API ;
3. l’UI couvre les parcours d’exploitation majeurs ;
4. la localisation ligne/colonne est obligatoire en salle ;
5. la fiche équipement affiche un chemin physique complet ;
6. le DCIM gère salle, rack, U, câbles, énergie, environnement ;
7. l’ITAM gère cycle de vie, contrats, garanties, stocks ;
8. le SAM gère logiciels, versions, installations et licences ;
9. l’IPAM gère IPv4, IPv6, VRF, VLAN, DNS/DHCP ;
10. l’allocation IP concurrente est sans collision ;
11. les imports massifs sont asynchrones, validables et rollbackables ;
12. les collectors discovery sont distribués et sécurisés ;
13. les conflits sont visibles et résolubles ;
14. les dépendances sont cartographiées ;
15. PostgreSQL Cluster est la source transactionnelle principale ;
16. les tables massives sont partitionnées ;
17. la stratégie 10 milliards d’entrées est documentée et benchmarkable ;
18. la sécurité couvre authN, authZ, secrets et audit ;
19. la haute disponibilité est testée ;
20. la CI/CD valide qualité, sécurité, tests, migrations et packaging.

---

## 24. Roadmap recommandée

### Phase 0 — Cadrage et architecture

- validation du CDC ;
- modèle domaine ;
- architecture cible ;
- choix stack ;
- stratégie PostgreSQL HA ;
- stratégie sécurité ;
- stratégie CI/CD ;
- critères d’acceptation.

### Phase 1 — Socle plateforme

- tenants ;
- utilisateurs ;
- RBAC ;
- audit ;
- PostgreSQL schema ;
- migrations ;
- API REST ;
- UI shell ;
- CI/CD ;
- observabilité ;
- packaging.

### Phase 2 — Ressources Inventory et DCIM

- objets de référence ;
- relations ;
- sites ;
- bâtiments ;
- salles ;
- grille ligne/colonne ;
- racks ;
- positions U ;
- câblage ;
- énergie ;
- visualisations.

### Phase 3 — IPAM avancé

- VRF ;
- aggregates ;
- prefixes ;
- ranges ;
- IP addresses ;
- réservations transactionnelles ;
- VLAN/VXLAN ;
- DNS/DHCP ;
- conflits ;
- capacité.

### Phase 4 — ITAM/SAM

- actifs ;
- cycle de vie ;
- contrats ;
- garanties ;
- stocks ;
- logiciels ;
- licences ;
- conformité.

### Phase 5 — Discovery distribuée

- orchestrateur ;
- collectors ;
- SSH ;
- WinRM ;
- SNMP ;
- cloud ;
- virtualisation ;
- Kubernetes ;
- rapprochement ;
- conflits.

### Phase 6 — Dependency Mapping

- graphe ;
- dépendances ;
- business services ;
- impact analysis ;
- visualisations ;
- exports.

### Phase 7 — Industrialisation extrême volumétrie

- benchmarks ;
- partitions ;
- vues matérialisées ;
- read replicas ;
- tests 10 milliards simulés/échantillonnés ;
- tuning PostgreSQL ;
- tests HA ;
- tests de charge ;
- runbooks.

---

## 25. Gouvernance projet

### 25.1 Rôles

| Rôle | Responsabilité |
|---|---|
| Sponsor | arbitrage métier et budget |
| Product Owner | priorisation fonctionnelle |
| Architecte solution | architecture globale |
| Architecte données | modèle PostgreSQL, performance, partitionnement |
| Architecte sécurité | sécurité, RBAC, secrets, audit |
| Lead backend | services domaine, API, jobs |
| Lead frontend | UI, visualisations, UX |
| DevOps/SRE | CI/CD, déploiement, HA, observabilité |
| QA automation | stratégie de tests et gates |
| Référent réseau | IPAM, VLAN, VRF, DNS/DHCP |
| Référent datacenter | DCIM, salle, rack, énergie, câblage |
| Référent ITAM | cycle de vie, contrats, licences |

### 25.2 Comités

- comité architecture ;
- comité sécurité ;
- comité performance ;
- comité données ;
- comité exploitation ;
- comité produit ;
- revue de release.

---

## 26. Risques majeurs et parades

| Risque | Impact | Parade obligatoire |
|---|---|---|
| Sous-estimation volumétrie | dégradation performance | partitionnement, benchmarks, séparation état courant/historique |
| Mauvaise qualité discovery | référentiel non fiable | score confiance, preuves, conflits, règles de rapprochement |
| Collision IP concurrente | incident réseau | transactions, locks fins, contraintes, tests concurrence |
| Modèle DCIM incomplet | erreurs intervention | ligne/colonne obligatoire, QR code, plans, validations |
| PostgreSQL mal dimensionné | indisponibilité | HA, tuning, replicas, monitoring, runbooks |
| API non gouvernée | dette technique | versioning, OpenAPI, tests contractuels |
| Sécurité insuffisante | fuite données/secrets | RBAC, chiffrement, audit, ASVS, scans sécurité |
| Imports destructifs | corruption référentiel | dry-run, rapport impact, rollback, audit |
| Dépendances non maîtrisées | graphes inutilisables | typage relations, score confiance, versions de graphe |
| UI non adaptée grands volumes | exploitation lente | pagination, recherche, filtres, vues sauvegardées |

---

## 27. Livrables attendus

| Livrable | Contenu |
|---|---|
| Dossier d’architecture | architecture logique, applicative, données, sécurité, exploitation |
| Modèle de données | schémas, contraintes, index, partitions |
| Spécification API | OpenAPI, GraphQL schema, webhooks |
| Backlog exigences | exigences identifiées, priorité, critères d’acceptation |
| Stratégie tests | unitaires, intégration, sécurité, performance, HA |
| Pipeline CI/CD | workflows, gates, artefacts, SBOM |
| Documentation exploitation | installation, backup, restore, upgrade, monitoring |
| Documentation utilisateur | UI, IPAM, DCIM, discovery, imports |
| Runbooks | incidents, failover, restauration, maintenance partitions |
| Plan migration | mapping sources, dry-run, transformation, rollback |
| Rapports de benchmark | requêtes critiques, charge API, concurrence IPAM |

---

## 28. Synthèse finale

OpenInfra doit être une solution open source d’enterprise, robuste et complète, couvrant Ressources Inventory, DCIM, ITAM, SAM, Discovery, Dependency Mapping et IPAM avancé, sans intégrer de fonction ITSM native.

Les exigences structurantes sont obligatoires : PostgreSQL Cluster, haute disponibilité, forte concurrence, haute performance, conception pour plus de 10 milliards d’entrées, localisation physique avec ligne et colonne en salle, sécurité by design, audit, API-first, tests et CI/CD.

Le projet doit être mené comme un produit d’infrastructure critique : exigences vérifiables, architecture propre, migrations maîtrisées, performance mesurée, sécurité validée, observabilité native et exploitation documentée.
