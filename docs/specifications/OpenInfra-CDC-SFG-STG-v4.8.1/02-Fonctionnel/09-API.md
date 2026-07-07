---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# API fonctionnelle

## Objectif

Les capacités fonctionnelles sont accessibles par REST, GraphQL, webhooks, SDK, CLI et bus d’événements.

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

### REQ-00012

Toutes les APIs volumineuses doivent imposer cursor pagination, limite stricte, filtres sélectifs et tri indexé.

**Acceptation :** Un endpoint volumineux sans filtre sélectif est refusé.

### REQ-00217

Le périmètre REST du volume API & Intégrations doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion REST, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00218

Le domaine REST doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00219

Le domaine REST doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00220

Le périmètre GraphQL du volume API & Intégrations doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion GraphQL, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00221

Le domaine GraphQL doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00222

Le domaine GraphQL doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00223

Le périmètre Webhooks du volume API & Intégrations doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Webhooks, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00224

Le domaine Webhooks doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00225

Le domaine Webhooks doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00226

Le périmètre Bus d’événements du volume API & Intégrations doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Bus d’événements, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00227

Le domaine Bus d’événements doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.



## Critères d’acceptation

La capacité est acceptée si les scénarios nominaux, erreurs, droits insuffisants, conflits et imports/exports sont validés par tests automatisés et si les journaux d’audit permettent de reconstituer les opérations.

### REQ-00774 — Dashboard court et contenu d’accueil isolé

Le portail openinfra-web doit afficher le titre d’accueil court **Dashboard**. Les métriques runtime et les cartes de synthèse des composants appartiennent exclusivement à cette page d’accueil ; elles ne doivent pas être réaffichées lorsqu’un opérateur navigue vers les pages ITRM, IPAM, DCIM, Discovery ou Sécurité.

**Acceptation :** Le titre long `Dashboard de pilotage OpenInfra` est absent des assets runtime ; les métriques `openinfra-dashboard-metrics` et les statistiques `Statistiques des composants OpenInfra` sont conditionnées à `overview` ; les pages composants affichent uniquement la titlebar contextuelle, le formulaire métier et le résultat éventuel.

### REQ-00775 — Ombres de contenu allégées openinfra-web

Le portail openinfra-web doit réduire la mise en perspective des blocs de contenu afin que la page soit plus fluide visuellement. Les effets de profondeur du header et du menu latéral ne sont pas modifiés ; les blocs métier doivent utiliser des tokens CSS dédiés plus légers.

**Acceptation :** Les variables `--openinfra-content-shadow` et `--openinfra-content-shadow-hover` sont présentes dans les assets runtime ; `.openinfra-titlebar`, `.openinfra-metric`, `.openinfra-operation-card`, `.openinfra-overview-summary`, `.openinfra-component-card` et `.card` utilisent les ombres allégées.
