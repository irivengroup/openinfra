---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# RSOT (Ressource Source of Truth)

## Objectif

Le référentiel centralise les objets d’infrastructure et leurs relations. Il applique golden record, score de confiance, reconciliation, time travel, audit et cycle de vie.

## Capacités obligatoires

- Création, consultation, modification contrôlée et historisation des objets.
- Recherche par identifiants, tags, relations, tenant, site et état.
- Import/export asynchrone lorsque le volume dépasse les seuils.
- Audit systématique des actions critiques.
- API REST et GraphQL si la capacité est consommable par automatisation.
- RBAC/ABAC tenant-aware.
- Détection et gestion des conflits de données.
- Tests unitaires, intégration, performance et sécurité selon criticité.

## Règles métier structurantes

1. La donnée déclarative validée reste prioritaire sur une découverte brute, sauf règle de réconciliation explicite.
2. Les suppressions critiques doivent être logiques ou précédées d’une preuve de non-impact.
3. Les objets liés ne doivent jamais être rendus orphelins sans événement de conflit ou règle de compensation.
4. Les imports doivent produire un rapport d’impact avant application.
5. Les modifications massives doivent être découpées en lots, auditables et annulables lorsque le domaine le permet.
6. Les données sensibles doivent être chiffrées, masquées et auditables.
7. Les recherches doivent être indexées et bornées.

## Exigences associées

### REQ-00004

Tout équipement physique doit être localisable par bâtiment, étage, salle, ligne, colonne, coordonnées X/Y/Z, rack, face et position U si applicable.

**Acceptation :** Impossible de valider un équipement physique en salle sans ligne et colonne.

### REQ-00005

Le référentiel doit conserver un historique complet time travel permettant de reconstituer l’état à une date donnée.

**Acceptation :** Une requête as-of-date restitue objets, relations et localisations cohérents.

### REQ-00031

Le périmètre Modèle de données complet du volume Référentiel RSOT (Ressource Source of Truth) doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Modèle de données complet, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00032

Le domaine Modèle de données complet doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00033

Le domaine Modèle de données complet doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00034

Le périmètre Gestion des équipements du volume Référentiel RSOT (Ressource Source of Truth) doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Gestion des équipements, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00035

Le domaine Gestion des équipements doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00036

Le domaine Gestion des équipements doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00037

Le périmètre Localisation X/Y/Z du volume Référentiel RSOT (Ressource Source of Truth) doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Localisation X/Y/Z, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00038

Le domaine Localisation X/Y/Z doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00039

Le domaine Localisation X/Y/Z doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00040

Le périmètre Historique du volume Référentiel RSOT (Ressource Source of Truth) doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Historique, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.



## Critères d’acceptation

La capacité est acceptée si les scénarios nominaux, erreurs, droits insuffisants, conflits et imports/exports sont validés par tests automatisés et si les journaux d’audit permettent de reconstituer les opérations.

## Complément v0.29.14 — Qualité, certification et score RSOT

OpenInfra doit fournir une capacité native de qualité et certification RSOT exposée par CLI, API et dashboard web.

Règles obligatoires :

- chaque objet RSOT peut être évalué individuellement ;
- chaque tenant peut obtenir une synthèse paginée des statuts qualité RSOT ;
- le score agrège au minimum la complétude, la fraîcheur, l’autorité de source et la confiance ;
- un objet incomplet ou obsolète ne doit jamais être marqué certifié ;
- une source non autoritative par rapport aux règles de gouvernance RSOT doit produire une alerte visible ;
- les évaluations doivent être protégées par RBAC et auditées ;
- les chemins primaires sont `openinfra rsot quality-object`, `openinfra rsot quality-summary`, `/api/v1/rsot/quality/object` et `/api/v1/rsot/quality/summary` ;
- les alias `sot` restent acceptés uniquement pour compatibilité ascendante.

## Complément v0.29.25 — Taxonomie catégories / types de ressources

OpenInfra doit gérer les ressources RSOT selon une taxonomie normalisée composée d’une catégorie métier et d’un type rattaché à cette catégorie.

Catégories minimales obligatoires :

- `server` : serveurs physiques, serveurs rack, blades, tours, hôtes hyperviseurs, machines virtuelles, hôtes conteneurs et appliances de calcul ;
- `personal-computer` : laptops, desktops, workstations, thin clients, all-in-one, tablettes et kiosques ;
- `monitor-peripheral` : écrans, claviers, souris, docks, webcams, casques, imprimantes, scanners, lecteurs codes-barres et consoles KVM ;
- `network-device` : switches, routeurs, firewalls, load balancers, contrôleurs Wi-Fi, points d’accès, VPN gateways, SD-WAN edges, TAP et interfaces réseau ;
- `storage` : baies, NAS, SAN switches, contrôleurs, shelves, disques, SSD/NVMe, librairies de bandes, appliances de sauvegarde et nœuds object storage ;
- `power-supply` : UPS, PDU, ATS, STS, redresseurs, onduleurs, batteries, générateurs, busways et compteurs électriques ;
- `rack-facility` : racks, armoires, patch panels, fiber panels, gestion de câbles, confinement, dalles et accessoires rack ;
- `cooling` : CRAC, CRAH, in-row coolers, échangeurs, chillers, humidificateurs et capteurs environnementaux ;
- `security-safety` : caméras CCTV, contrôle d’accès, lecteurs biométriques, centrales incendie, détecteurs et alarmes ;
- `telecom` : PBX, passerelles VoIP, téléphones IP, modems, transpondeurs optiques, multiplexeurs et liens radio ;
- `cloud-virtualization` : comptes cloud, régions, VPC, subnets cloud, security groups, instances, volumes, clusters Kubernetes, nœuds, conteneurs et namespaces ;
- `software-service` : applications, services, API, services web, bases de données, middleware, brokers, licences, certificats et zones DNS ;
- `cable-connectivity` : câbles cuivre, fibres, patch cords, trunks, transceivers, modules SFP/QSFP et cassettes ;
- `mobile-iot` : smartphones, terminaux durcis, passerelles IoT, PLC, capteurs et actionneurs ;
- `other` : actifs génériques, ressources externes et équipements inconnus.

Règles obligatoires :

1. Le catalogue doit être exposé par `openinfra rsot resource-taxonomy` et `/api/v1/rsot/resource-taxonomy`.
2. Les opérations de création, modification et réconciliation doivent accepter `resource_category` et `resource_type`.
3. Le backend doit rejeter tout type incompatible avec la catégorie sélectionnée.
4. Les objets historisés doivent conserver `resource_category` et `resource_type` dans les attributs et au niveau de la représentation API.
5. Les anciens `kind` legacy restent tolérés uniquement pendant la période de migration contrôlée vers RSOT.
6. Les formulaires web doivent filtrer automatiquement les types selon la catégorie choisie.
7. Le mécanisme de filtrage dépendant doit être générique et réutilisable par tout composant exposant une structure catégorie/type.
### Sélecteurs catégorie/type et valeurs internes

Les interfaces opérateur doivent afficher les libellés métier de la taxonomie RSOT dans les listes déroulantes de catégories et de types. Les valeurs techniques normalisées demeurent internes à la solution et sont les seules transmises aux contrats API/CLI. Les types génériques `physical-server` et `disk` sont retirés car les spécialisations `rack-server`, `blade-server`, `tower-server`, `hdd`, `ssd` et `nvme-drive` couvrent explicitement ces cas.

## Complément OpenInfra v0.29.93 — Graphe intégré au périmètre RSOT

Le Graphe de dépendances constitue une vue et une capacité d’analyse du RSOT. Il doit être rangé dans la navigation RSOT, sous des groupes dédiés à l’exploration, à l’analyse d’impact et aux exports, et ne doit pas apparaître comme composant métier autonome. Ce rangement ne modifie ni les contrats API `/api/v1/graph/*`, ni la CLI `openinfra graph`, ni les permissions existantes.
