---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# DCIM

## Objectif

Le DCIM modélise bâtiments, salles, lignes, colonnes, X/Y/Z, allées chaudes/froides, racks, patch panels, PDU, énergie, refroidissement, capacité et jumeau numérique.

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

### REQ-00009

Le DCIM doit fournir plans 2D/3D, racks, patch panels, PDU, énergie, refroidissement, capacité et jumeau numérique.

**Acceptation :** Le parcours site → salle → rack → équipement → câble → alimentation est navigable.

### REQ-00127

Le périmètre Plans 2D/3D du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Plans 2D/3D, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00128

Le domaine Plans 2D/3D doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00129

Le domaine Plans 2D/3D doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00130

Le périmètre Coordonnées ligne/colonne/X/Y/Z du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Coordonnées ligne/colonne/X/Y/Z, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00131

Le domaine Coordonnées ligne/colonne/X/Y/Z doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00132

Le domaine Coordonnées ligne/colonne/X/Y/Z doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00133

Le périmètre Racks du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Racks, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00134

Le domaine Racks doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00135

Le domaine Racks doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00136

Le périmètre Patch panels du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Patch panels, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00137

Le domaine Patch panels doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.


### REQ-00763

Le DCIM doit exposer la localisation et la relocalisation d’un équipement par API HTTP et formulaire web, en réutilisant les contraintes existantes de salle, ligne, colonne, rack, face, position U, hauteur U et coordonnées X/Y/Z.

**Acceptation :** Un équipement peut être localisé par `POST /api/v1/dcim/locations` et par le dashboard sans contourner les contrôles de conflit rack/U ni les règles ligne/colonne obligatoires.

### REQ-00764

Le DCIM doit exposer l’élévation rack dans le dashboard opérateur en réutilisant le contrat API `GET /api/v1/dcim/rack-elevation`, avec sélection explicite du rack, de la face et du format de rendu.

**Acceptation :** Le dashboard contient l’opération `Élévation rack`, les champs Site/Bâtiment/Salle/Rack/Face rack/Format rendu, et transmet la requête au backend sans recalculer l’occupation U côté navigateur.

## Critères d’acceptation

La capacité est acceptée si les scénarios nominaux, erreurs, droits insuffisants, conflits et imports/exports sont validés par tests automatisés et si les journaux d’audit permettent de reconstituer les opérations.
