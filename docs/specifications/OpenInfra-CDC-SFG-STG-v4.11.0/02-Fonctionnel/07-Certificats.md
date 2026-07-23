---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Certificats

## Objectif

Le module certificats inventorie les certificats TLS, chaînes, autorités, expirations, usages, endpoints et risques.

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
