---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# ITAM

## Objectif

L’ITAM gère actifs, logiciels, licences, garanties, contrats, dépréciation, coûts, stock, fin de vie et preuves de destruction.

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

### REQ-00175

Le périmètre Actifs du volume ITAM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Actifs, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00176

Le domaine Actifs doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00177

Le domaine Actifs doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00178

Le périmètre Logiciels du volume ITAM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Logiciels, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00179

Le domaine Logiciels doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00180

Le domaine Logiciels doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00181

Le périmètre Licences du volume ITAM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Licences, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00182

Le domaine Licences doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00183

Le domaine Licences doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00184

Le périmètre Garanties du volume ITAM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Garanties, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00185

Le domaine Garanties doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00186

Le domaine Garanties doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.



## Critères d’acceptation

La capacité est acceptée si les scénarios nominaux, erreurs, droits insuffisants, conflits et imports/exports sont validés par tests automatisés et si les journaux d’audit permettent de reconstituer les opérations.


### REQ-00814 — Organisations ITAM parent des tenants

Le domaine ITAM doit gérer les organisations comme référentiel parent des tenants. Une organisation représente l’entreprise, le groupe ou l’entité juridique cliente ; un tenant représente une subdivision rattachée, par exemple `organisation=Orange` et `tenant=DSI`.

**Carte d’identité entreprise obligatoire :** code organisation, raison sociale, nom d’usage, numéro d’immatriculation, identifiant fiscal, pays ISO 3166-1 alpha-2, ville, adresse siège, email de contact, contact support, statut et description.

**Règles métier :** aucun tenant, support ou enregistrement de licence ne doit être créé sans tenant actif rattaché à une organisation active. Les formulaires de ressources sélectionnent l’organisation, filtrent les tenants associés et proposent l’organisation comme tenant implicite si aucun tenant actif n’existe encore. Le retrait d’une organisation est logique et retire ses tenants sans supprimer l’historique.

**Acceptation :** services, CLI, API HTTP, OpenAPI, migration PostgreSQL, portail web et tests de non-régression valident le modèle Organisation → Tenant et l’absence de libellé ambigu `Entité propriétaire` dans les formulaires actifs.


### REQ-00815 — Formulaires ITAM racine et hiérarchie pertinente

Les formulaires ITAM doivent exposer uniquement les rattachements métier pertinents au niveau de l'objet manipulé. Une organisation est une entité racine : ses formulaires de création, modification et retrait ne doivent pas présenter de sélecteur Organisation parent, Tenant parent ou tenant de sécurité. Un tenant est une subdivision d'une organisation : ses formulaires doivent sélectionner l'organisation parente, puis le tenant cible uniquement pour les opérations de consultation, modification ou retrait. Les ressources, supports et licences restent rattachés au couple Organisation → Tenant filtré.

**Migrations :** cette correction est purement UI/contrat de formulaire ; elle ne doit pas créer de nouvelle migration PostgreSQL. Les migrations déjà publiées restent immuables et `0031_itam_organization_identity.sql` demeure conservée pour compatibilité des environnements existants.

**Acceptation :** les tests frontend et web statiques valident l'absence de `Tenant de sécurité` et `scope_tenant_id` dans les formulaires web, l'absence de sélecteurs globaux sur les opérations Organisation/Tenant, la présence de sélecteurs tenant cible filtrés pour modification/retrait tenant et l'absence de migration `0032_*`.


### REQ-00816 — Fournisseurs, éditeurs et supports tiers ITAM accrédités

Le domaine ITAM doit gérer un référentiel de partenaires rattachés à une organisation active. Un partenaire représente un constructeur matériel, un éditeur logiciel ou un support tiers. Chaque partenaire doit porter une carte d’identité entreprise complète : identifiant partenaire, organisation de rattachement, catégorie, raison sociale, nom d’usage, numéro d’immatriculation, identifiant fiscal, pays ISO 3166-1 alpha-2, ville, adresse, code postal, email de contact, au moins un contact téléphonique, contact support, site web optionnel, statut et description.

**Règles métier :** un constructeur ou éditeur ne peut fournir du matériel, un logiciel, une garantie ou une licence que s’il est actif et accrédité pour l’organisation concernée. Un support tiers ne peut être utilisé dans un contrat de support que s’il est actif, rattaché à la même organisation et de catégorie support tiers. Les formulaires garanties, licences et supports ne doivent plus s’appuyer sur un fournisseur libre mais sur le référentiel des partenaires filtré par organisation et catégorie.

**Migrations :** le référentiel est livré dans une seule migration PostgreSQL structurante `0032_itam_partner_registry.sql`, afin de limiter le nombre de migrations tout en conservant l’immutabilité des migrations déjà publiées.

**Acceptation :** services, CLI, API HTTP, migration PostgreSQL, portail web, OpenAPI et tests de non-régression valident le CRUD des partenaires, le filtrage par organisation/catégorie et le blocage des garanties, licences ou supports sans partenaire actif accrédité.

## v0.29.80 — Adresse complète des organisations et partenaires

Une organisation ITAM expose une adresse et des coordonnées minimales : pays, ville, adresse, code postal, email de contact, téléphone et contact support. Un partenaire ITAM expose également un code postal obligatoire dans sa carte d’identité entreprise. Le portail web utilise le libellé `Pays` et affiche uniquement le nom du pays, tout en soumettant le code ISO alpha-2.
