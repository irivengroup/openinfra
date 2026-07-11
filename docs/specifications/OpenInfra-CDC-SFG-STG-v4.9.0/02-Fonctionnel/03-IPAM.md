---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# IPAM Enterprise++

## Objectif

L’IPAM couvre IPv4, IPv6, VRF, ASN, BGP, EVPN/VXLAN, MPLS, NAT, DHCP, DNS, DDI, RPKI, blocs RIR, conflits, plans et capacité.

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

### REQ-00006

Les allocations IP doivent être transactionnelles, idempotentes et sûres en concurrence.

**Acceptation :** 100 réservations simultanées dans le même préfixe ne produisent aucun doublon.

### REQ-00007

L’IPAM doit supporter IPv4, IPv6, VRF, ASN, BGP, EVPN/VXLAN, MPLS, NAT, DHCP, DNS, DDI, RPKI et blocs RIPE/ARIN/APNIC.

**Acceptation :** Chaque objet majeur dispose d’un modèle, d’une API et de critères de validation.

### REQ-00049

Le périmètre IPv4/IPv6 du volume IPAM Enterprise++ doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion IPv4/IPv6, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00050

Le domaine IPv4/IPv6 doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00051

Le domaine IPv4/IPv6 doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00052

Le périmètre VRF du volume IPAM Enterprise++ doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion VRF, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00053

Le domaine VRF doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00054

Le domaine VRF doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00055

Le périmètre ASN du volume IPAM Enterprise++ doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion ASN, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00056

Le domaine ASN doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00057

Le domaine ASN doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00058

Le périmètre BGP du volume IPAM Enterprise++ doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion BGP, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.



### REQ-00769

Le dashboard IPAM doit exposer les opérations Enterprise++ majeures VRF, agrégats, préfixes, plages, adresses, allocation, assistant de réservation, capacité, bindings réseau, VLAN/VXLAN, ASN/BGP, observations DNS/DHCP, conflits et prévisualisation DDI via les contrats backend existants.

**Acceptation :** Les opérations IPAM du dashboard ciblent des routes `/api/v1/ipam/*` réelles, la découverte API expose la section `ipam`, et aucune règle métier IPAM n'est dupliquée côté navigateur.


### REQ-00770

OpenInfra doit exposer une topologie opérationnelle IPAM consolidant VRF, agrégats, préfixes, plages, adresses, réservations, VLAN/VXLAN, ASN/BGP et observations DNS/DHCP sous forme de graphe noeuds/arêtes exploitable par API, CLI et dashboard.

**Acceptation :** `GET /api/v1/ipam/topology` et `openinfra ipam topology` retournent `summary`, `nodes`, `edges` et `integrity` ; le dashboard expose **Topologie opérationnelle IPAM** ; le graphe est construit à partir des repositories existants sans stockage parallèle.

## Critères d’acceptation

La capacité est acceptée si les scénarios nominaux, erreurs, droits insuffisants, conflits et imports/exports sont validés par tests automatisés et si les journaux d’audit permettent de reconstituer les opérations.
