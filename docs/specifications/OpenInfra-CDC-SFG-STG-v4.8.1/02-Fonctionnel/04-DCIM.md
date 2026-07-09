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

### REQ-00765

Le dashboard DCIM doit exposer les opérations de câblage terrain permettant de définir un panneau de brassage, définir un port DCIM et connecter un câble via les contrats backend existants.

**Acceptation :** Le dashboard contient les opérations `Définir un panneau de brassage`, `Définir un port DCIM` et `Connecter un câble`, avec les champs endpoints A/B, connecteur, média, statut, chemin câble, longueur et libellé ; les appels passent par `/api/v1/dcim/patch-panels`, `/api/v1/dcim/ports` et `/api/v1/dcim/cables` sans logique métier de compatibilité côté navigateur.

### REQ-00766

Le dashboard DCIM doit exposer les opérations énergie/refroidissement permettant de définir un équipement électrique, définir un circuit électrique, définir une zone de refroidissement, réserver la puissance d’un équipement et consulter la capacité énergie/refroidissement d’un rack via les contrats backend existants.

**Acceptation :** Le dashboard contient les opérations `Définir un équipement électrique`, `Définir un circuit électrique`, `Définir une zone de refroidissement`, `Réserver la puissance équipement` et `Capacité énergie/refroidissement`; elles ciblent `/api/v1/dcim/power-devices`, `/api/v1/dcim/power-circuits`, `/api/v1/dcim/cooling-zones`, `/api/v1/dcim/power-reservations` et `/api/v1/dcim/energy-cooling-capacity` sans réimplémenter les règles de capacité, redondance A/B, derating ou marge thermique côté navigateur.

### REQ-00768

Le DCIM doit exposer un jumeau numérique initial de salle consolidant, pour un tenant et une salle donnés, le plan 2D, les racks, équipements montés ou posés au sol, panneaux de brassage, ports, câbles, circuits électriques, réservations de puissance, capacité énergie/refroidissement et élévations rack disponibles.

**Acceptation :** `GET /api/v1/dcim/digital-twin`, la commande CLI `openinfra dcim digital-twin` et le dashboard `Jumeau numérique salle` retournent une vue JSON cohérente sans créer de stockage parallèle ni dupliquer les règles métier DCIM.

## Critères d’acceptation

La capacité est acceptée si les scénarios nominaux, erreurs, droits insuffisants, conflits et imports/exports sont validés par tests automatisés et si les journaux d’audit permettent de reconstituer les opérations.
## v0.29.65 — Sites DCIM et dépendances

Les sites DCIM sont des objets de référence gérés avec cycle de vie : création, consultation, liste, modification et retrait logique. Le retrait d’un site retire logiquement les bâtiments, étages, salles et zones rattachés afin d’éviter les localisations orphelines sans supprimer l’historique.

Le portail web doit consommer le catalogue `/api/v1/dcim/topology-catalog` pour proposer des listes déroulantes dans les formulaires de création ou d’exploitation de ressources. Aucune saisie libre n’est autorisée pour les références `site`, `bâtiment`, `étage`, `salle`, `zone`, `rack`, `ligne` ou `colonne`.


## Cycle de vie explicite des dépendances topologiques

OpenInfra doit administrer explicitement les dépendances topologiques DCIM suivantes :

- bâtiments rattachés à un site actif ;
- étages rattachés à un bâtiment actif ;
- salles rattachées à un étage actif ;
- zones rattachées à une salle active et contraintes par la grille de lignes/colonnes de la salle.

Toute création doit refuser un parent absent, suspendu ou retiré. Toute suppression métier est un retrait logique (`status=retired`) et ne supprime aucune donnée physique. Les cascades non destructives sont obligatoires :

- retrait bâtiment → retrait des étages, salles et zones rattachés ;
- retrait étage → retrait des salles de l'étage et de leurs zones ;
- retrait salle → retrait des zones rattachées ;
- retrait zone → zone uniquement.

L'opération composite `define-room` reste compatible pour les scénarios d'initialisation rapide, mais le CRUD dédié des dépendances est le contrat d'administration courant.


## v0.29.79 — Bâtiments typés et étages générés

Les étages ne sont plus administrés comme un CRUD métier manuel dans les parcours opérateur. Ils restent des éléments internes d'un bâtiment et sont générés par OpenInfra à la création du bâtiment lorsque le type `Etages` est sélectionné.

Lors de la création d'un bâtiment, le champ `Type Batiment` accepte `Simple` ou `Etages`. Si `Etages` est choisi, `Niveau Initial` est obligatoire et borné de -20 à 0, `Niveau Final` est obligatoire et borné de 1 à 150. Les formulaires consomment ensuite l'expansion déterministe de cette plage.

Le code d'étage est généré selon `<code-site>_<code-bat>_ETG<num-etage>` et le nom selon `<code-site>/<code-bat>/ETG<num-etage>`. Aucun opérateur ne saisit manuellement le code ou le nom de l'étage dans les formulaires d'administration.
