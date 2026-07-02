# OpenInfra — Roadmap détaillée de développement

**Version :** 1.0.0  
**Référence :** Roadmap de réalisation pour le dossier OpenInfra CDC/SFG/STG v4.0.0  
**Approche :** programme industriel, agile contrôlé, gates Go/No-Go, exigences vérifiables, qualité bloquante.

---

## 1. Objectif de la roadmap

Cette roadmap transforme le dossier de spécifications OpenInfra en trajectoire de développement exploitable par une équipe d’architecture, de delivery, d’intégration et d’exploitation.

Elle couvre :

- le séquencement fonctionnel et technique ;
- les dépendances entre domaines ;
- les livrables attendus ;
- les critères d’entrée et de sortie ;
- les jalons ;
- les risques ;
- les validations ;
- la trajectoire MVP, Beta, Release Candidate et GA Enterprise.

La roadmap maintient les exigences structurantes : PostgreSQL Cluster, tables massives partitionnées, haute performance, haute résilience, concurrence forte, localisation physique ligne/colonne/X/Y/Z, API-first, sécurité by design et exclusion stricte de tout ITSM intégré.

---

## 2. Hypothèses de planification

- Sprints de deux semaines, avec démonstration et revue qualité à chaque fin de sprint.
- Équipe cible recommandée : 1 directeur programme, 1 product owner, 1 architecte entreprise, 1 architecte solution, 1 DBA PostgreSQL senior, 1 SRE, 3 à 5 backend engineers, 2 frontend engineers, 2 discovery/network engineers, 1 security engineer, 2 QA automation engineers, 1 technical writer.
- Le planning est exprimé en durées relatives T0 afin de rester indépendant de la date de lancement.
- La première mise en production utile doit viser le périmètre SOT + DCIM localisation + IPAM transactionnel + sécurité de base, avant les modules avancés.
- Les exigences N1 du CDC v4 sont non négociables : PostgreSQL Cluster, partitionnement des tables massives, performance, concurrence, résilience, absence d’ITSM intégré.
- Les modules IA/RAG ne doivent jamais modifier des données sans validation humaine explicite et doivent toujours appliquer les permissions avant restitution.

---

## 3. Streams d’exécution

| ID | Stream | Responsabilités |
|---|---|---|
| STR-PROD | Produit & fonctionnel | Vision, backlog, priorisation, UX métier, critères d’acceptation, démonstrations. |
| STR-ARCH | Architecture entreprise | C4, ADR/RFC, urbanisation, intégration, décisions structurantes, revues d’architecture. |
| STR-DATA | Data/PostgreSQL | Modèle, migrations, partitionnement, HA, index, performance SQL, archivage. |
| STR-BE | Backend/API | Domain services, REST, GraphQL, jobs, outbox, webhooks, sécurité applicative. |
| STR-FE | Frontend/UX | UI web, vues DCIM/IPAM/graphes, accessibilité, performance navigateur. |
| STR-DISC | Discovery/collectors | Collectors, protocoles, orchestration, secrets, réconciliation, preuves. |
| STR-SEC | Sécurité | IAM, RBAC/ABAC, audit, chiffrement, threat modeling, tests sécurité. |
| STR-SRE | Ops/SRE | Kubernetes, Helm, observabilité, sauvegarde, PRA/PCA, runbooks. |
| STR-QA | QA/Validation | Stratégie tests, automatisation, charge, chaos, sécurité, non-régression. |
| STR-DOC | Documentation & enablement | SFG/STG, guides admin, API, runbooks, formation, migration. |

---

## 4. Releases macro

| ID | Release | Phases | Période relative | Objectif | Livrables majeurs |
|---|---|---|---|---|---|
| REL-00 | Foundation Alpha | P00-P02 | T0 à T0+5 mois | Socle architecture, CI/CD, PostgreSQL HA, modèles core, API baseline. | Environnements prêts; cluster DB; quality gates; API baseline; migrations. |
| REL-01 | MVP SOT/DCIM/IPAM | P03-P05 | T0+3 à T0+10 mois | Référentiel, localisation, DCIM fondation, IPAM transactionnel, UI exploitant. | SOT; DCIM localisation; IPAM VRF IPv4/IPv6; audit; RBAC initial. |
| REL-02 | Beta Discovery & Imports | P06-P07 | T0+7 à T0+14 mois | Imports massifs, discovery distribuée, réconciliation, conflits et preuves. | Import async; collectors; matching; score confiance; dashboards jobs. |
| REL-03 | Beta Dependency/ITAM/Security | P08-P10 | T0+10 à T0+18 mois | Dépendances, flux, ITAM, licences, contrats, sécurité enterprise, policy engine. | Graphes; matrices flux; lifecycle; SSO/MFA; Vault; audit avancé. |
| REL-04 | Enterprise Extensions | P11-P13 | T0+14 à T0+26 mois | Field ops, simulation, FinOps, GreenOps, SBOM, exposition, IA/RAG gouvernée. | Mobile/offline; simulations; coûts; SBOM; RAG permission-aware. |
| REL-05 | GA Enterprise Scale | P14 | T0+20 à T0+30 mois | Industrialisation production, performance, chaos, HA, PRA/PCA, documentation et support. | Benchmarks; chaos; Helm; observabilité; runbooks; Go/No-Go GA. |

---

## 5. Phases programme

| ID | Phase | Période relative | Objectif | Critère de sortie |
|---|---|---|---|---|
| P00 | Cadrage programme et gouvernance | T0 à T0+1 mois | Sécuriser le périmètre, le pilotage, les règles d’architecture et les standards de livraison. | Go programme signé, backlog initial priorisé, gouvernance active. |
| P01 | Socle engineering et plateforme | T0+1 à T0+3 mois | Mettre en place le dépôt, l’architecture logicielle, la CI/CD, les environnements, le socle API et les conventions. | Pipeline vert, socle exécutable, tests de base, packaging reproductible. |
| P02 | Data Platform PostgreSQL Cluster | T0+2 à T0+5 mois | Implémenter la persistance transactionnelle HA, migrations, partitionnement, observabilité SQL et stratégie hot/warm/cold. | Cluster PostgreSQL validé, DDL initial versionné, partitions et migrations testées. |
| P03 | Source of Truth et modèle commun | T0+3 à T0+7 mois | Livrer le référentiel central : tenants, objets, relations, tags, custom fields, historique, audit et gouvernance minimale. | CRUD API/UI complet, historique time travel initial, audit, RBAC objet. |
| P04 | DCIM fondation et localisation univoque | T0+5 à T0+9 mois | Livrer sites, bâtiments, salles, grille ligne/colonne/X/Y/Z, racks, U, chemins physiques, QR codes. | Un équipement physique est localisable sans ambiguïté avec contraintes obligatoires. |
| P05 | IPAM Enterprise++ fondation | T0+5 à T0+10 mois | Livrer IPv4/IPv6, VRF, prefixes, plages, adresses, réservations transactionnelles, conflits et capacité. | Allocation IP concurrente sans collision, API IPAM utilisable en automatisation. |
| P06 | Imports, exports et migration initiale | T0+7 à T0+11 mois | Livrer imports massifs, dry-run, mapping, validation, rollback, reprise et exports asynchrones. | Import million de lignes validé, rapport d’impact, reprise après interruption. |
| P07 | Discovery distribuée et réconciliation | T0+8 à T0+14 mois | Livrer orchestrateur, collectors, SNMP/SSH/VMware/Cloud/Kubernetes, preuves, score de confiance et conflits. | Découverte distribuée non bloquante, réconciliation gouvernée, aucune écriture silencieuse. |
| P08 | Dependency Mapping et flux réseau | T0+10 à T0+16 mois | Livrer graphe de dépendances, analyse d’impact, matrice de flux déclarés/observés, SPOF et visualisations. | Graphe applicatif/réseau exploitable, flux comparés, impact calculé. |
| P09 | ITAM, licences, contrats et lifecycle | T0+11 à T0+17 mois | Livrer actifs, cycle de vie, logiciels, licences, contrats, garanties, EOL/EOS, coûts de base. | Inventaire complet avec conformité lifecycle et rapports contractuels. |
| P10 | Sécurité, conformité, politiques et audit avancé | T0+4 à T0+18 mois | Renforcer RBAC/ABAC, SSO/MFA, secrets, audit immuable, policy engine, conformité continue. | Contrôles sécurité validés, audit inviolable ou append-only, policies exécutées. |
| P11 | Field Operations et simulation | T0+14 à T0+20 mois | Livrer fiches intervention, mobile/offline, checklists, simulation placement/changement/migration. | Interventions terrain guidées, impacts simulés avant exécution. |
| P12 | FinOps, GreenOps, SBOM et exposition | T0+16 à T0+24 mois | Livrer coûts, chargeback/showback, énergie/carbone, SBOM, vulnérabilités contextualisées. | Pilotage coût/risque/énergie corrélé aux actifs et services. |
| P13 | IA/RAG et automatisation gouvernée | T0+18 à T0+26 mois | Livrer recherche naturelle, assistant RAG cité, détection anomalies, recommandations non destructives. | Réponses sourcées, filtrées par droits, aucune action destructive sans validation. |
| P14 | Industrialisation GA et scale enterprise | T0+20 à T0+30 mois | Valider production, performance, résilience, PRA/PCA, documentation, support, packaging et montée en charge. | Release GA signée, tests charge/chaos/PITR/failover passants, runbooks validés. |

---

## 6. Description détaillée par phase

## P00 — Cadrage programme et gouvernance

**Période relative :** T0 à T0+1 mois

**Objectif :** Sécuriser le périmètre, le pilotage, les règles d’architecture et les standards de livraison.

**Critère de sortie :** Go programme signé, backlog initial priorisé, gouvernance active.

### Epics de la phase

#### EPIC-0001 — Gouvernance programme OpenInfra

- **Stream :** STR-PROD
- **Priorité :** P1
- **Description :** Mettre en place comités, rôles, RACI, rituels, gestion des décisions et circuit d’arbitrage.
- **Livrables :** Charte programme; RACI; calendrier comités; règles de priorisation; modèle de reporting.
- **Dépendances :** Aucun
- **Acceptation :** Comité opérationnel actif, décisions tracées, backlog initial approuvé.

#### EPIC-0002 — Architecture principles & ADR framework

- **Stream :** STR-ARCH
- **Priorité :** P1
- **Description :** Définir les principes non négociables : API-first, PostgreSQL cluster, pas d’ITSM intégré, partitionnement massif, sécurité by design.
- **Livrables :** ADR initiaux; RFC d’exigences; conventions C4; grille de revue architecture.
- **Dépendances :** EPIC-0001
- **Acceptation :** Toute décision structurante dispose d’un ADR validé.

#### EPIC-0003 — Stratégie qualité et Definition of Done

- **Stream :** STR-QA
- **Priorité :** P1
- **Description :** Définir les seuils qualité, matrices de tests, gates CI/CD, sécurité, performance et documentation.
- **Livrables :** DoD; DoR; quality gates; stratégie de tests; politique couverture; modèle rapport release.
- **Dépendances :** EPIC-0001
- **Acceptation :** Aucune user story ne peut sortir sans tests, docs, critères et CI verte.

#### EPIC-0004 — Backlog macro et découpage releases

- **Stream :** STR-PROD
- **Priorité :** P1
- **Description :** Découper le CDC SFG/STG v4 en epics, features, stories et jalons livrables.
- **Livrables :** Backlog initial; mapping exigences→epics; releases MVP/Beta/GA; priorisation MoSCoW.
- **Dépendances :** EPIC-0001; EPIC-0002
- **Acceptation :** Chaque exigence N1 a une cible de release et un owner.


## P01 — Socle engineering et plateforme

**Période relative :** T0+1 à T0+3 mois

**Objectif :** Mettre en place le dépôt, l’architecture logicielle, la CI/CD, les environnements, le socle API et les conventions.

**Critère de sortie :** Pipeline vert, socle exécutable, tests de base, packaging reproductible.

### Epics de la phase

#### EPIC-0101 — Repository, packaging et conventions backend

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Créer le dépôt, structure modulaire, packaging reproductible, conventions de code et outillage développeur.
- **Livrables :** Repository; Makefile ou Taskfile; packaging; hooks; config lint/type/test; documentation dev.
- **Dépendances :** EPIC-0003
- **Acceptation :** Un développeur clone, installe, teste et lance localement en une procédure documentée.

#### EPIC-0102 — Socle domaine hexagonal

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Implémenter les couches domaine, application, infrastructure et interfaces avec frontières explicites.
- **Livrables :** Modules core; ports/adapters; erreurs typées; transactions applicatives; conventions DTO.
- **Dépendances :** EPIC-0101
- **Acceptation :** Le code respecte les frontières, contrôlées par tests d’architecture.

#### EPIC-0103 — API Gateway interne REST baseline

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Livrer API REST versionnée avec pagination, filtres, erreurs normalisées, OpenAPI et authentification minimale.
- **Livrables :** REST v1; OpenAPI; pagination cursor; filtres indexés; format erreur; health endpoints.
- **Dépendances :** EPIC-0102
- **Acceptation :** Toutes les listes imposent limite, curseur et tri contrôlé.

#### EPIC-0104 — Moteur jobs asynchrones baseline

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Livrer abstraction de jobs, workers, retries, DLQ, idempotence et observabilité de files.
- **Livrables :** Job service; worker runtime; retry/backoff; DLQ; métriques; cancellation.
- **Dépendances :** EPIC-0102
- **Acceptation :** Un job interrompu peut être repris sans duplication d’effet.

#### EPIC-0105 — Design system et shell applicatif

- **Stream :** STR-FE
- **Priorité :** P1
- **Description :** Créer la base UI : navigation, layouts, auth shell, tableaux paginés, formulaires, accessibilité.
- **Livrables :** Design system; UI shell; composants table/form/detail; navigation; tests UI.
- **Dépendances :** EPIC-0103
- **Acceptation :** L’UI consomme l’API versionnée et respecte les droits reçus.

#### EPIC-0106 — Environnements dev/test et CI/CD

- **Stream :** STR-SRE
- **Priorité :** P1
- **Description :** Mettre en place CI/CD complète : format, lint, types, tests, sécurité, build, artefacts, smoke.
- **Livrables :** GitHub Actions; images OCI; tests; scans; SBOM; artefacts; cache contrôlé.
- **Dépendances :** EPIC-0101
- **Acceptation :** Pipeline bloquant vert sur branche principale, artefacts reproductibles.

#### EPIC-0107 — Documentation développeur initiale

- **Stream :** STR-DOC
- **Priorité :** P1
- **Description :** Documenter installation, architecture, conventions, branches, contribution et troubleshooting.
- **Livrables :** README; guide dev; guide architecture; guide contribution; normes API.
- **Dépendances :** EPIC-0101
- **Acceptation :** Un nouveau contributeur installe et lance sans assistance non documentée.


## P02 — Data Platform PostgreSQL Cluster

**Période relative :** T0+2 à T0+5 mois

**Objectif :** Implémenter la persistance transactionnelle HA, migrations, partitionnement, observabilité SQL et stratégie hot/warm/cold.

**Critère de sortie :** Cluster PostgreSQL validé, DDL initial versionné, partitions et migrations testées.

### Epics de la phase

#### EPIC-0201 — PostgreSQL Cluster référence

- **Stream :** STR-DATA
- **Priorité :** P1
- **Description :** Livrer topologie primaire/réplicas, pooling, routage lecture/écriture, sauvegarde WAL et PITR.
- **Livrables :** Manifests; Patroni; PgBouncer; HAProxy; pgBackRest; runbooks; tests failover.
- **Dépendances :** EPIC-0106
- **Acceptation :** Bascule primaire et restauration PITR démontrées sur environnement test.

#### EPIC-0202 — Migrations versionnées et garde-fous DDL

- **Stream :** STR-DATA
- **Priorité :** P1
- **Description :** Mettre en place migrations applicatives, contrôles anti-table massive non partitionnée et rollback documenté.
- **Livrables :** Migrations; validateur DDL; pipeline migration; conventions naming; rollback.
- **Dépendances :** EPIC-0201
- **Acceptation :** La CI refuse une table massive sans partitionnement ou index critique attendu.

#### EPIC-0203 — Modèle core multi-tenant

- **Stream :** STR-DATA
- **Priorité :** P1
- **Description :** Livrer tenants, organisations, utilisateurs techniques, tags, champs personnalisés, référentiels communs.
- **Livrables :** Schéma core; contraintes; API core; tests multi-tenant; isolation logique.
- **Dépendances :** EPIC-0202
- **Acceptation :** Un objet ne peut pas être consulté hors périmètre tenant autorisé.

#### EPIC-0204 — Partitionnement hot/warm/cold

- **Stream :** STR-DATA
- **Priorité :** P1
- **Description :** Implémenter stratégie partitions temps/tenant/hash, rétention, archivage et restauration partitionnée.
- **Livrables :** Schémas partitionnés; jobs retention; export froid; runbook restauration; tests charge.
- **Dépendances :** EPIC-0202
- **Acceptation :** Tables massives partitionnées, purge/archivage testés, requêtes critiques bornées.

#### EPIC-0205 — Indexation et observabilité SQL

- **Stream :** STR-DATA
- **Priorité :** P1
- **Description :** Activer pg_stat_statements, plans critiques, métriques SQL, détection index inutiles/manquants.
- **Livrables :** Dashboards DB; alertes; catalogue requêtes critiques; scripts EXPLAIN; seuils.
- **Dépendances :** EPIC-0201
- **Acceptation :** Chaque endpoint critique dispose d’un plan SQL validé et surveillé.


## P03 — Source of Truth et modèle commun

**Période relative :** T0+3 à T0+7 mois

**Objectif :** Livrer le référentiel central : tenants, objets, relations, tags, custom fields, historique, audit et gouvernance minimale.

**Critère de sortie :** CRUD API/UI complet, historique time travel initial, audit, RBAC objet.

### Epics de la phase

#### EPIC-0301 — Entités Source of Truth

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Livrer objets génériques et spécialisés : devices, interfaces, services, applications, relations typées.
- **Livrables :** Domain model SOT; API CRUD; validation; recherche clé; tests invariants.
- **Dépendances :** EPIC-0203
- **Acceptation :** Création, modification, lecture et historisation fonctionnent via API et UI.

#### EPIC-0302 — Relations et graphe relationnel transactionnel

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Modéliser relations typées, cardinalités, périodes de validité, provenance et contraintes.
- **Livrables :** Relation service; API relations; contraintes; historique; visualisation basique.
- **Dépendances :** EPIC-0301
- **Acceptation :** Une relation possède type, source, validité, audit et droits associés.

#### EPIC-0303 — Historique time travel initial

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Implémenter snapshots/versions objets et relations permettant une restitution à date.
- **Livrables :** History model; API as-of-date; tests restitution; vues historisées.
- **Dépendances :** EPIC-0301; EPIC-0302
- **Acceptation :** Une requête à date restitue objet, relations et localisation cohérents.

#### EPIC-0304 — Audit applicatif central

- **Stream :** STR-SEC
- **Priorité :** P1
- **Description :** Journaliser opérations sensibles avec immutabilité logique, corrélation et export signé.
- **Livrables :** Audit service; audit API; schémas partitionnés; export signé; tests accès.
- **Dépendances :** EPIC-0204
- **Acceptation :** Aucune modification critique n’est possible sans audit complet.

#### EPIC-0305 — UI Source of Truth

- **Stream :** STR-FE
- **Priorité :** P1
- **Description :** Livrer listes, fiches, relations, historique, recherche, tags, filtres et actions batch contrôlées.
- **Livrables :** Pages SOT; détail objet; historique; recherche; formulaires; tests e2e.
- **Dépendances :** EPIC-0301; EPIC-0303
- **Acceptation :** Un exploitant peut consulter et modifier un actif selon ses droits.

#### EPIC-0306 — Gouvernance minimale des sources

- **Stream :** STR-PROD
- **Priorité :** P1
- **Description :** Définir source autoritative par domaine/attribut, priorité, fraîcheur et comportement conflit.
- **Livrables :** Règles gouvernance; API; UI; score confiance; tests conflit.
- **Dépendances :** EPIC-0301
- **Acceptation :** Un conflit de source n’écrase jamais silencieusement une donnée certifiée.


## P04 — DCIM fondation et localisation univoque

**Période relative :** T0+5 à T0+9 mois

**Objectif :** Livrer sites, bâtiments, salles, grille ligne/colonne/X/Y/Z, racks, U, chemins physiques, QR codes.

**Critère de sortie :** Un équipement physique est localisable sans ambiguïté avec contraintes obligatoires.

### Epics de la phase

#### EPIC-0401 — Modèle physique DCIM

- **Stream :** STR-DATA
- **Priorité :** P1
- **Description :** Livrer pays, région, ville, site, bâtiment, étage, salle, zone, ligne, colonne, coordonnées X/Y/Z.
- **Livrables :** Schéma DCIM; contraintes localisation; API; tests validation.
- **Dépendances :** EPIC-0301
- **Acceptation :** Un équipement en salle exige ligne et colonne avant validation.

#### EPIC-0402 — Racks, U, faces et capacité espace

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer racks, positions U, faces, orientation, réservations, conflits, capacité et contraintes physiques.
- **Livrables :** Rack service; U allocator; conflits; API; tests.
- **Dépendances :** EPIC-0401
- **Acceptation :** Deux équipements ne peuvent pas occuper un même U incompatible.

#### EPIC-0403 — QR codes et chemins intervention

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Générer chemins humains, QR codes, fiches localisation et preuve d’identification terrain.
- **Livrables :** QR service; fiche PDF/HTML; API; audit scan; tests.
- **Dépendances :** EPIC-0401; EPIC-0402
- **Acceptation :** Un technicien retrouve équipement via QR et chemin complet.

#### EPIC-0404 — Plans 2D salle et rack elevation

- **Stream :** STR-FE
- **Priorité :** P1
- **Description :** Livrer visualisation grille ligne/colonne, racks, faces, U, occupation et recherche visuelle.
- **Livrables :** Vue salle 2D; rack elevation; filtres; exports; tests UI.
- **Dépendances :** EPIC-0402
- **Acceptation :** La localisation visuelle correspond aux contraintes stockées en base.

#### EPIC-0405 — Câblage DCIM fondation

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Modéliser ports, câbles, patch panels, chemins, connecteurs et liaisons point-à-point.
- **Livrables :** Cable model; port model; API; validation; historique.
- **Dépendances :** EPIC-0402
- **Acceptation :** Un câble relie des ports compatibles et son chemin est historisé.

#### EPIC-0406 — Énergie et refroidissement fondation

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer PDU, UPS, circuits A/B, puissance, contraintes froid/chaud et capacité énergétique.
- **Livrables :** Power model; cooling zones; API capacité; règles alertes.
- **Dépendances :** EPIC-0401
- **Acceptation :** Placement refusé si capacité énergie/poids/refroidissement dépassée.


## P05 — IPAM Enterprise++ fondation

**Période relative :** T0+5 à T0+10 mois

**Objectif :** Livrer IPv4/IPv6, VRF, prefixes, plages, adresses, réservations transactionnelles, conflits et capacité.

**Critère de sortie :** Allocation IP concurrente sans collision, API IPAM utilisable en automatisation.

### Epics de la phase

#### EPIC-0501 — Modèle IPAM IPv4/IPv6/VRF

- **Stream :** STR-DATA
- **Priorité :** P1
- **Description :** Livrer VRF, aggregates, prefixes, ranges, IP, interfaces, types inet/cidr et contraintes.
- **Livrables :** Schéma IPAM; contraintes; index GiST/SP-GiST; API base; tests overlap.
- **Dépendances :** EPIC-0202
- **Acceptation :** Adresses chevauchantes autorisées uniquement dans espaces VRF distincts.

#### EPIC-0502 — Allocation IP transactionnelle

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Implémenter next available IP, réservation atomique, idempotency key, locks fins et audit.
- **Livrables :** IP allocator; API; tests concurrence; audit; erreurs normalisées.
- **Dépendances :** EPIC-0501; EPIC-0304
- **Acceptation :** 100 allocations concurrentes ne produisent aucune collision.

#### EPIC-0503 — VLAN/VXLAN/ASN/BGP fondation

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer VLAN groups, VNIs, ASN, route targets, BGP attributes et rattachements IPAM.
- **Livrables :** Modèles réseau; API; validations; imports; tests.
- **Dépendances :** EPIC-0501
- **Acceptation :** Les relations VRF/VLAN/VNI/ASN sont cohérentes et auditables.

#### EPIC-0504 — Détection conflits IPAM

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Détecter overlap interdit, IP dupliquée, IP hors subnet, DNS/PTR divergents, leases conflictuels.
- **Livrables :** Conflict engine; API conflits; UI; jobs; tests.
- **Dépendances :** EPIC-0502
- **Acceptation :** Chaque conflit produit preuve, sévérité, objet impacté et action proposée.

#### EPIC-0505 — UI IPAM opérationnelle

- **Stream :** STR-FE
- **Priorité :** P1
- **Description :** Livrer vues arborescentes, recherche IP, réservation, capacité, conflits et détails VRF.
- **Livrables :** Pages IPAM; recherche; reservation wizard; capacité; tests e2e.
- **Dépendances :** EPIC-0502; EPIC-0504
- **Acceptation :** Un ingénieur réserve une IP en VRF avec traçabilité complète.

#### EPIC-0506 — DDI intégration baseline

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Préparer connecteurs DNS/DHCP avec preview, transaction compensatoire, divergence detection.
- **Livrables :** Connecteur interface; BIND/PowerDNS/Kea baseline; dry-run; rollback compensatoire.
- **Dépendances :** EPIC-0502
- **Acceptation :** Une réservation peut générer une prévisualisation DNS/DHCP sans divergence silencieuse.


## P06 — Imports, exports et migration initiale

**Période relative :** T0+7 à T0+11 mois

**Objectif :** Livrer imports massifs, dry-run, mapping, validation, rollback, reprise et exports asynchrones.

**Critère de sortie :** Import million de lignes validé, rapport d’impact, reprise après interruption.

### Epics de la phase

#### EPIC-0601 — Import framework générique

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Livrer upload, parsing CSV/XLSX/JSON, mapping, validation, dry-run, rapport impact et job async.
- **Livrables :** Import service; mapping UI/API; validation; rapport; DLQ; tests.
- **Dépendances :** EPIC-0104; EPIC-0301
- **Acceptation :** Un import invalide ne modifie aucune donnée et produit un rapport exploitable.

#### EPIC-0602 — Import massif scalable

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Implémenter batch borné, COPY PostgreSQL si applicable, checkpoints, reprise et métriques.
- **Livrables :** Bulk pipeline; checkpoints; throttling; métriques; tests million lignes.
- **Dépendances :** EPIC-0601; EPIC-0204
- **Acceptation :** Import 1M lignes sans bloquer l’usage interactif.

#### EPIC-0603 — Exports asynchrones et signés

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Livrer exports filtrés, génération async, streaming contrôlé, stockage objet et signature.
- **Livrables :** Export service; formats CSV/XLSX/JSON; object storage; signature; audit.
- **Dépendances :** EPIC-0601
- **Acceptation :** Aucun export volumineux n’est exécuté en synchrone.

#### EPIC-0604 — Migration depuis référentiels existants

- **Stream :** STR-PROD
- **Priorité :** P1
- **Description :** Livrer mappings Device42/NetBox/Nautobot/GLPI/CSV génériques et stratégie de reprise.
- **Livrables :** Templates mapping; guide migration; dry-run; rapports écarts.
- **Dépendances :** EPIC-0601
- **Acceptation :** Une migration initiale peut être simulée avec rapport d’écarts complet.


## P07 — Discovery distribuée et réconciliation

**Période relative :** T0+8 à T0+14 mois

**Objectif :** Livrer orchestrateur, collectors, SNMP/SSH/VMware/Cloud/Kubernetes, preuves, score de confiance et conflits.

**Critère de sortie :** Découverte distribuée non bloquante, réconciliation gouvernée, aucune écriture silencieuse.

### Epics de la phase

#### EPIC-0701 — Registry collectors et identité forte

- **Stream :** STR-DISC
- **Priorité :** P1
- **Description :** Enregistrer collectors, gérer mTLS, périmètres, versions, heartbeat, secrets via Vault.
- **Livrables :** Collector registry; mTLS; heartbeat; scopes; API; UI; tests.
- **Dépendances :** EPIC-0104; EPIC-1002
- **Acceptation :** Un collector non autorisé ne peut recevoir aucun job.

#### EPIC-0702 — Discovery SNMP/LLDP/CDP

- **Stream :** STR-DISC
- **Priorité :** P1
- **Description :** Découvrir équipements réseau, interfaces, ports, VLAN, LLDP/CDP, MAC/ARP.
- **Livrables :** SNMP collector; LLDP/CDP parser; normalized observations; tests lab.
- **Dépendances :** EPIC-0701
- **Acceptation :** Les observations réseau sont historisées avec preuve et source.

#### EPIC-0703 — Discovery SSH/WinRM systèmes

- **Stream :** STR-DISC
- **Priorité :** P1
- **Description :** Découvrir Linux/Unix/Windows : matériel, OS, interfaces, logiciels, services, ports.
- **Livrables :** SSH collector; WinRM collector; parsers; secrets ephemeral; tests.
- **Dépendances :** EPIC-0701
- **Acceptation :** Les données système alimentent SOT sans écrasement silencieux.

#### EPIC-0704 — Discovery virtualisation et cloud

- **Stream :** STR-DISC
- **Priorité :** P1
- **Description :** Découvrir VMware, Proxmox, Hyper-V, Kubernetes, AWS/Azure/GCP/OpenStack.
- **Livrables :** Connecteurs; normalisation cloud; tags; mapping VM→host→rack.
- **Dépendances :** EPIC-0701
- **Acceptation :** Les ressources cloud/virtualisation ont identifiants stables et relations correctes.

#### EPIC-0705 — Réconciliation multi-sources

- **Stream :** STR-DISC
- **Priorité :** P1
- **Description :** Implémenter matching pondéré, score confiance, conflits, certification et règles de fusion.
- **Livrables :** Reconciliation engine; UI conflits; policies; tests cas ambigus.
- **Dépendances :** EPIC-0306; EPIC-0702; EPIC-0703
- **Acceptation :** Aucune donnée certifiée n’est remplacée sans règle explicite.

#### EPIC-0706 — Banc de discovery haute charge

- **Stream :** STR-QA
- **Priorité :** P1
- **Description :** Créer environnements simulés pour scans distribués, rate limiting, interruption/reprise.
- **Livrables :** Simulateurs; tests charge collectors; métriques; rapport.
- **Dépendances :** EPIC-0702; EPIC-0703
- **Acceptation :** Un scan massif ne dégrade pas les APIs critiques au-delà des seuils.


## P08 — Dependency Mapping et flux réseau

**Période relative :** T0+10 à T0+16 mois

**Objectif :** Livrer graphe de dépendances, analyse d’impact, matrice de flux déclarés/observés, SPOF et visualisations.

**Critère de sortie :** Graphe applicatif/réseau exploitable, flux comparés, impact calculé.

### Epics de la phase

#### EPIC-0801 — Graphe dépendances modèle et stockage

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Modéliser nœuds, arêtes, sources, temporalité, poids, preuve, criticité et partitionnement.
- **Livrables :** Graph model; API; jobs consolidation; index; tests.
- **Dépendances :** EPIC-0302; EPIC-0204
- **Acceptation :** Les arêtes massives sont partitionnées et consultables par filtres bornés.

#### EPIC-0802 — Analyse impact et SPOF

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Calculer chemins, dépendances entrantes/sortantes, single points of failure et services impactés.
- **Livrables :** Impact engine; API; rapports; tests graphes.
- **Dépendances :** EPIC-0801
- **Acceptation :** Un rapport liste composants impactés, criticité et incertitudes de source.

#### EPIC-0803 — Matrice de flux réseau

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer flux déclarés, observés, temporaires, propriétaires, validité, ports, protocoles, justification.
- **Livrables :** Flow model; API; import; export firewall; UI; audit.
- **Dépendances :** EPIC-0501; EPIC-0801
- **Acceptation :** Un flux déclaré possède owner, durée, justification et relations applicatives.

#### EPIC-0804 — Ingestion NetFlow/sFlow/IPFIX/firewall logs

- **Stream :** STR-DISC
- **Priorité :** P1
- **Description :** Importer flux observés, agréger, comparer au déclaré, détecter flux non autorisés ou orphelins.
- **Livrables :** Collectors flux; aggregation; retention; comparisons; metrics.
- **Dépendances :** EPIC-0803; EPIC-0204
- **Acceptation :** Les flux observés sont agrégés sans transformer PostgreSQL OLTP en entrepôt illimité.

#### EPIC-0805 — Visualisations graphes et flux

- **Stream :** STR-FE
- **Priorité :** P1
- **Description :** Livrer graphes interactifs, filtres, chemins, vues impact, export GraphML/DOT/SVG.
- **Livrables :** Graph UI; flow matrix UI; impact report; tests UX.
- **Dépendances :** EPIC-0802; EPIC-0803
- **Acceptation :** Un architecte explore un service métier et ses dépendances critiques.


## P09 — ITAM, licences, contrats et lifecycle

**Période relative :** T0+11 à T0+17 mois

**Objectif :** Livrer actifs, cycle de vie, logiciels, licences, contrats, garanties, EOL/EOS, coûts de base.

**Critère de sortie :** Inventaire complet avec conformité lifecycle et rapports contractuels.

### Epics de la phase

#### EPIC-0901 — ITAM actifs et cycle de vie

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer acquisition, stock, affectation, maintenance, retrait, destruction, pièces détachées.
- **Livrables :** ITAM model; workflows référentiels; API; UI; tests.
- **Dépendances :** EPIC-0301; EPIC-0401
- **Acceptation :** Un actif suit un cycle de vie complet avec audit et localisation.

#### EPIC-0902 — Logiciels et inventaires logiciels

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer logiciels, versions, installations, packages, services, empreintes et inventaires massifs.
- **Livrables :** Software model; imports discovery; partitioned inventories; tests.
- **Dépendances :** EPIC-0703; EPIC-0204
- **Acceptation :** Les inventaires logiciels massifs sont partitionnés et recherchables.

#### EPIC-0903 — Licences et conformité logicielle

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer contrats licences, droits, installations, sous/sur-licensing, règles éditeurs.
- **Livrables :** License model; compliance engine; reports; UI.
- **Dépendances :** EPIC-0902
- **Acceptation :** Un rapport identifie écarts de conformité par éditeur/application.

#### EPIC-0904 — Contrats, garanties et fournisseurs

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Gérer fournisseurs, contrats support, garanties, dates, coûts, SLA contractuels non ITSM.
- **Livrables :** Contract model; alerts; reports; imports.
- **Dépendances :** EPIC-0901
- **Acceptation :** Un actif expose ses garanties et contrats liés.

#### EPIC-0905 — Lifecycle Intelligence EOL/EOS

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Corréler modèles, OS, firmwares, contrats, garanties, EOL/EOS et risques par service.
- **Livrables :** Lifecycle model; rules; dashboards; imports vendors.
- **Dépendances :** EPIC-0901; EPIC-0802
- **Acceptation :** Les actifs en fin de support sont reliés aux services impactés.


## P10 — Sécurité, conformité, politiques et audit avancé

**Période relative :** T0+4 à T0+18 mois

**Objectif :** Renforcer RBAC/ABAC, SSO/MFA, secrets, audit immuable, policy engine, conformité continue.

**Critère de sortie :** Contrôles sécurité validés, audit inviolable ou append-only, policies exécutées.

### Epics de la phase

#### EPIC-1001 — SSO/OIDC/SAML/MFA

- **Stream :** STR-SEC
- **Priorité :** P1
- **Description :** Implémenter authentification entreprise, mapping groupes, sessions, service accounts et tokens.
- **Livrables :** OIDC; SAML; MFA via IdP; token API; session policies; tests.
- **Dépendances :** EPIC-0103
- **Acceptation :** Authentification locale désactivable, groupes IdP mappés aux rôles.

#### EPIC-1002 — Vault et secrets discovery

- **Stream :** STR-SEC
- **Priorité :** P1
- **Description :** Intégrer Vault ou backend secrets compatible, rotation, injection temporaire et masquage.
- **Livrables :** Secret provider; scopes; rotation hooks; audit; tests.
- **Dépendances :** EPIC-1001
- **Acceptation :** Aucun secret discovery n’est stocké en clair ni affiché en logs.

#### EPIC-1003 — RBAC/ABAC avancé

- **Stream :** STR-SEC
- **Priorité :** P1
- **Description :** Implémenter permissions fines par tenant, site, domaine, objet, champ, action et contexte.
- **Livrables :** Policy model; enforcement backend/frontend; tests droits; audit refus.
- **Dépendances :** EPIC-1001; EPIC-0203
- **Acceptation :** Un utilisateur ne voit ni champs ni objets hors périmètre.

#### EPIC-1004 — Audit append-only et preuve

- **Stream :** STR-SEC
- **Priorité :** P1
- **Description :** Renforcer audit avec intégrité, chaînage hash ou stockage append-only et exports vérifiables.
- **Livrables :** Audit integrity; verification; signed exports; retention.
- **Dépendances :** EPIC-0304
- **Acceptation :** Une altération d’audit est détectable.

#### EPIC-1005 — Policy Engine conformité continue

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Exécuter règles de conformité : naming, owner, IPAM, localisation, certificats, sécurité, cloud, tags.
- **Livrables :** Rule engine; DSL contrôlé; scheduler; exceptions; dashboards.
- **Dépendances :** EPIC-0306; EPIC-1003
- **Acceptation :** Chaque non-conformité possède preuve, sévérité, owner et exception éventuelle.

#### EPIC-1006 — Security verification program

- **Stream :** STR-QA
- **Priorité :** P1
- **Description :** Threat modeling, SAST, dependency scan, secrets scan, DAST, tests RBAC/ABAC, supply chain.
- **Livrables :** Threat models; security CI; reports; penetration checklist.
- **Dépendances :** EPIC-1001; EPIC-1003
- **Acceptation :** Aucune release ne sort avec vulnérabilité critique non traitée.


## P11 — Field Operations et simulation

**Période relative :** T0+14 à T0+20 mois

**Objectif :** Livrer fiches intervention, mobile/offline, checklists, simulation placement/changement/migration.

**Critère de sortie :** Interventions terrain guidées, impacts simulés avant exécution.

### Epics de la phase

#### EPIC-1101 — Field operations mobile web

- **Stream :** STR-FE
- **Priorité :** P1
- **Description :** Livrer interface mobile responsive/offline pour consultation localisation, checklists, photos et scan QR.
- **Livrables :** PWA; offline cache sécurisé; QR scan; checklists; upload photos.
- **Dépendances :** EPIC-0403; EPIC-1003
- **Acceptation :** Un technicien suit une intervention même avec connectivité intermittente.

#### EPIC-1102 — Journal intervention sans ITSM

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Enregistrer actions terrain, preuves, photos, validations et verrou logique d’intervention sans ticketing.
- **Livrables :** Field operation model; audit; attachments; locks; exports.
- **Dépendances :** EPIC-1101
- **Acceptation :** Le journal est rattaché aux actifs sans créer de module ITSM.

#### EPIC-1103 — Simulation placement DCIM

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Simuler ajout/déplacement équipement selon espace, énergie, refroidissement, poids, réseau et dépendances.
- **Livrables :** Simulation engine DCIM; reports; API; UI.
- **Dépendances :** EPIC-0406; EPIC-0802
- **Acceptation :** Le système refuse ou avertit selon contraintes violées.

#### EPIC-1104 — Simulation changement infrastructure

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Simuler suppression subnet, changement VLAN, coupure PDU/switch, migration application et impacts.
- **Livrables :** Change simulation; impact reports; snapshots; compare.
- **Dépendances :** EPIC-0802; EPIC-0504
- **Acceptation :** Un rapport avant/après expose impacts et incertitudes.

#### EPIC-1105 — Migration planning

- **Stream :** STR-PROD
- **Priorité :** P1
- **Description :** Gérer vagues de migration, move groups, readiness score, contraintes, dépendances bloquantes.
- **Livrables :** Migration model; planner UI; scoring; reports.
- **Dépendances :** EPIC-1104
- **Acceptation :** Une vague de migration liste dépendances, risques et prérequis.


## P12 — FinOps, GreenOps, SBOM et exposition

**Période relative :** T0+16 à T0+24 mois

**Objectif :** Livrer coûts, chargeback/showback, énergie/carbone, SBOM, vulnérabilités contextualisées.

**Critère de sortie :** Pilotage coût/risque/énergie corrélé aux actifs et services.

### Epics de la phase

#### EPIC-1201 — FinOps cost model

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Modéliser coûts cloud, datacenter, licences, énergie, support, contrats et allocation.
- **Livrables :** Cost model; imports; showback; chargeback; reports.
- **Dépendances :** EPIC-0904; EPIC-0406
- **Acceptation :** Un coût est imputable à application, service, tenant ou centre de coûts.

#### EPIC-1202 — GreenOps sustainability

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Calculer consommation, PUE, CO2 estimé, équipements zombies, consolidation et rapports énergie.
- **Livrables :** Energy/carbon model; dashboards; recommendations.
- **Dépendances :** EPIC-0406; EPIC-1201
- **Acceptation :** Un rapport énergie/carbone est disponible par site, rack et service.

#### EPIC-1203 — SBOM registry

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Importer CycloneDX/SPDX, versionner SBOM, relier composants, licences, CVE et applications.
- **Livrables :** SBOM model; import; diff; API; UI.
- **Dépendances :** EPIC-0902; EPIC-1005
- **Acceptation :** Une SBOM est liée à une release applicative et exploitable pour risque licence/CVE.

#### EPIC-1204 — Exposure & vulnerability context

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Corréler vulnérabilités externes avec actifs, logiciels, exposition internet, flux et criticité métier.
- **Livrables :** Vulnerability context; integrations; prioritization; dashboards.
- **Dépendances :** EPIC-1203; EPIC-0803
- **Acceptation :** Le risque est priorisé selon exposition et criticité, pas seulement score brut.

#### EPIC-1205 — Certificate & PKI avancé

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Découvrir certificats TLS, chaînes, SAN, expiration, algorithmes faibles, owners et endpoints.
- **Livrables :** Cert inventory; scans; Kubernetes/cloud integrations; alerts.
- **Dépendances :** EPIC-0703; EPIC-1005
- **Acceptation :** Un certificat expirant est relié à application, endpoint et propriétaire.


## P13 — IA/RAG et automatisation gouvernée

**Période relative :** T0+18 à T0+26 mois

**Objectif :** Livrer recherche naturelle, assistant RAG cité, détection anomalies, recommandations non destructives.

**Critère de sortie :** Réponses sourcées, filtrées par droits, aucune action destructive sans validation.

### Epics de la phase

#### EPIC-1301 — Index RAG permission-aware

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Construire index documentaire et référentiel filtré par droits, sources citées, fraîcheur et scopes.
- **Livrables :** Indexing pipeline; ACL filtering; citations; freshness.
- **Dépendances :** EPIC-1003; EPIC-0301
- **Acceptation :** Une réponse ne révèle jamais un objet non autorisé.

#### EPIC-1302 — Assistant langage naturel

- **Stream :** STR-FE
- **Priorité :** P1
- **Description :** Livrer UI assistant pour recherche, explication, requêtes guidées et génération de rapports non destructifs.
- **Livrables :** Assistant UI; conversation context; report generation; guardrails.
- **Dépendances :** EPIC-1301
- **Acceptation :** Chaque réponse opérationnelle cite les sources OpenInfra consultées.

#### EPIC-1303 — Anomaly detection gouvernée

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Détecter anomalies IPAM, discovery, flux, capacité, coûts, certificats et inventaire avec validation humaine.
- **Livrables :** Anomaly jobs; scoring; review UI; feedback loop.
- **Dépendances :** EPIC-1005; EPIC-1201
- **Acceptation :** Une anomalie ne modifie aucune donnée sans approbation explicite.

#### EPIC-1304 — Recommandations placement et préfixes

- **Stream :** STR-BE
- **Priorité :** P1
- **Description :** Proposer placement rack et optimisation de préfixes IP avec justification, contraintes et simulation.
- **Livrables :** Recommendation engine; reports; confidence scores.
- **Dépendances :** EPIC-1103; EPIC-0504
- **Acceptation :** Une recommandation explique contraintes, données sources et limites.


## P14 — Industrialisation GA et scale enterprise

**Période relative :** T0+20 à T0+30 mois

**Objectif :** Valider production, performance, résilience, PRA/PCA, documentation, support, packaging et montée en charge.

**Critère de sortie :** Release GA signée, tests charge/chaos/PITR/failover passants, runbooks validés.

### Epics de la phase

#### EPIC-1401 — Performance enterprise certification

- **Stream :** STR-QA
- **Priorité :** P1
- **Description :** Benchmarks API/DB/import/discovery/IPAM/graph sur jeux synthétiques et profils réalistes.
- **Livrables :** Bench suite; reports p95/p99; SQL plans; gating perf.
- **Dépendances :** EPIC-0205; EPIC-0602; EPIC-0801
- **Acceptation :** p95/p99 critiques dans les objectifs définis ou dérogation formelle.

#### EPIC-1402 — Chaos et résilience

- **Stream :** STR-QA
- **Priorité :** P1
- **Description :** Tests panne worker, API, DB primaire, réseau, queue, object storage, secrets backend.
- **Livrables :** Chaos tests; failover reports; recovery runbooks.
- **Dépendances :** EPIC-0201; EPIC-0104; EPIC-1002
- **Acceptation :** Aucun job validé perdu et reprise documentée.

#### EPIC-1403 — Packaging Kubernetes/Helm production

- **Stream :** STR-SRE
- **Priorité :** P1
- **Description :** Livrer charts, values, probes, autoscaling, policies, ingress, secrets, backups et upgrade.
- **Livrables :** Helm charts; OCI images; manifests; upgrade tests.
- **Dépendances :** EPIC-0106; EPIC-0201
- **Acceptation :** Déploiement reproductible sur cluster Kubernetes de référence.

#### EPIC-1404 — Observabilité complète

- **Stream :** STR-SRE
- **Priorité :** P1
- **Description :** Dashboards API, DB, jobs, collectors, queues, front, erreurs, traces, logs, alertes.
- **Livrables :** Grafana dashboards; Prometheus alerts; Loki; OpenTelemetry traces.
- **Dépendances :** EPIC-0205; EPIC-0104
- **Acceptation :** Tout incident critique possède métriques, logs et traces corrélables.

#### EPIC-1405 — Documentation exploitation et formation

- **Stream :** STR-DOC
- **Priorité :** P1
- **Description :** Finaliser guides admin, runbooks, API, migration, sécurité, sauvegarde, PRA, formation.
- **Livrables :** Docs versionnées; runbooks; guides formation; catalogue API.
- **Dépendances :** Toutes phases
- **Acceptation :** Une équipe exploitante peut installer, opérer, sauvegarder, restaurer et diagnostiquer.

#### EPIC-1406 — Go/No-Go GA Enterprise

- **Stream :** STR-PROD
- **Priorité :** P1
- **Description :** Exécuter checklist finale de conformité exigences, risques, sécurité, performance, support et documentation.
- **Livrables :** Go/No-Go report; release notes; known limitations; support model.
- **Dépendances :** EPIC-1401; EPIC-1402; EPIC-1403; EPIC-1404; EPIC-1405
- **Acceptation :** GA signée uniquement si exigences N1 passantes ou dérogées formellement.


---

## 7. Jalons de pilotage

| ID | Jalon | Phase | Définition |
|---|---|---|---|
| M00 | Kickoff programme | P00 | Gouvernance, conventions et backlog initial validés. |
| M01 | Architecture baseline | P01 | Monolithe modulaire, API-first, ADR, repository, CI/CD, environnements prêts. |
| M02 | PostgreSQL HA baseline | P02 | Cluster primaire + deux réplicas, PgBouncer/HAProxy, migrations versionnées, PITR démontré. |
| M03 | MVP Source of Truth | P03 | Objets, relations, audit, historique, RBAC et API/UI de base. |
| M04 | MVP DCIM/IPAM | P04/P05 | Localisation ligne/colonne/X/Y/Z et IPAM transactionnel exploitables. |
| M05 | Beta Discovery | P07 | Collectors SNMP/SSH/VMware/Kubernetes/Cloud avec réconciliation gouvernée. |
| M06 | Beta Dependency & Flow | P08 | Graphe, flux déclarés/observés, impact analysis et SPOF. |
| M07 | Beta ITAM/Security | P09/P10 | Cycle de vie, licences, contrats, SSO/MFA, audit et policy engine. |
| M08 | Release Candidate Enterprise | P11/P12/P13 | Field ops, simulation, FinOps/GreenOps/SBOM et RAG gouverné. |
| M09 | GA Enterprise | P14 | Performance, résilience, PRA, sécurité, documentation et support validés. |

---

## 8. Gates Go/No-Go

| ID | Gate | Phase | Critères Go | Critères No-Go |
|---|---|---|---|---|
| GATE-00 | Cadrage validé | P00 | Backlog priorisé, exigences N1 identifiées, gouvernance active, risques initiaux acceptés. | Bloquer P01 si absence de responsable produit, architecte, DBA/SRE ou QA lead. |
| GATE-01 | Engineering ready | P01 | CI verte, packaging reproductible, standards code/tests/docs actifs, environments créés. | Bloquer P02/P03 si pipeline non bloquant ou absence de tests automatisés. |
| GATE-02 | Data ready | P02 | PostgreSQL HA, PITR, migrations, partitionnement, observabilité SQL validés. | Bloquer données massives si partitionnement ou PITR non validés. |
| GATE-03 | MVP operational | P05 | SOT, DCIM localisation, IPAM réservation et audit utilisables par API/UI. | Bloquer discovery si SOT/IPAM non stables. |
| GATE-04 | Discovery safe | P07 | Collectors mTLS, secrets, rate limiting, réconciliation, conflits et preuves validés. | Bloquer scans larges si gouvernance sources incomplète. |
| GATE-05 | Enterprise beta | P10 | Graphes, flux, ITAM, SSO/MFA, Vault, RBAC/ABAC, policy engine disponibles. | Bloquer extensions avancées si sécurité ou audit insuffisants. |
| GATE-06 | RC hardening | P13 | Extensions enterprise terminées, tests e2e, docs utilisateur, risques résiduels maîtrisés. | Bloquer GA si performance, chaos ou docs d’exploitation non passants. |
| GATE-07 | GA signed | P14 | Sécurité, performance, résilience, PRA/PCA, observabilité, documentation et support validés. | Aucune GA avec exigence N1 non passée sans dérogation signée. |

---

## 9. Chemin critique

Le chemin critique du programme est le suivant :

1. Gouvernance et standards d’architecture.
2. Socle engineering et CI/CD.
3. PostgreSQL Cluster HA, migrations, partitionnement et observabilité SQL.
4. Source of Truth avec audit, historique, RBAC et gouvernance des sources.
5. DCIM localisation physique et IPAM transactionnel.
6. Imports massifs et discovery distribuée.
7. Réconciliation multi-sources.
8. Dependency mapping, flux réseau et impact analysis.
9. Sécurité enterprise, policy engine et audit avancé.
10. Extensions enterprise : field operations, simulation, FinOps, GreenOps, SBOM, exposition, IA/RAG.
11. Performance, chaos, PRA/PCA, packaging Kubernetes, documentation et Go/No-Go GA.

Aucun module de découverte large, d’IA/RAG, de simulation ou de synchronisation externe ne doit être lancé avant stabilisation du socle de sécurité, des droits, de l’audit et de la gouvernance de la donnée.

---

## 10. Stratégie MVP

Le MVP doit rester strict et exploitable. Il doit contenir uniquement les capacités indispensables pour prouver la valeur et valider les choix d’architecture :

- authentification de base et RBAC initial ;
- modèle tenant ;
- Source of Truth devices/interfaces/relations ;
- sites, bâtiments, salles, ligne, colonne, coordonnées X/Y/Z ;
- racks, positions U et chemins physiques ;
- IPAM IPv4/IPv6, VRF, prefixes, adresses ;
- réservation IP transactionnelle ;
- audit ;
- historique initial ;
- API REST versionnée ;
- UI web minimale ;
- PostgreSQL Cluster validé ;
- CI/CD complète ;
- tests unitaires, intégration, API et sécurité de base.

Ne doivent pas entrer dans le MVP : IA/RAG, GreenOps, FinOps avancé, SBOM, 3D avancée, NetFlow à grande échelle, migration planning complet, conformité réseau avancée et jumeau numérique complet.

---

## 11. Stratégie Beta

La Beta doit démontrer la capacité à alimenter automatiquement le référentiel et à produire de la valeur d’exploitation :

- imports massifs ;
- discovery SNMP/SSH/VMware/Kubernetes/Cloud ;
- réconciliation multi-sources ;
- score de confiance ;
- conflits gouvernés ;
- dependency mapping ;
- matrice de flux ;
- ITAM ;
- sécurité enterprise ;
- policy engine ;
- tests de charge intermédiaires.

---

## 12. Stratégie GA Enterprise

La GA ne doit pas être une simple stabilisation fonctionnelle. Elle doit démontrer :

- capacité de production ;
- performance mesurée ;
- p95/p99 conformes ;
- failover PostgreSQL ;
- restauration PITR ;
- reprise jobs ;
- sauvegardes testées ;
- chaos tests ;
- sécurité vérifiée ;
- scans supply chain ;
- runbooks ;
- Helm charts ;
- observabilité ;
- documentation exploitable ;
- support et procédures d’upgrade.

---

## 13. Organisation recommandée des versions

- **0.x Alpha technique :** socle, architecture, data platform, API, CI/CD.
- **1.0 MVP :** SOT, DCIM localisation, IPAM transactionnel, audit, UI minimale.
- **1.5 Beta :** imports, discovery, réconciliation, conflits, premières dépendances.
- **2.0 Enterprise Core :** dependency mapping, ITAM, sécurité enterprise, policy engine.
- **2.5 Enterprise Extensions :** field operations, simulation, FinOps, GreenOps, SBOM, exposition.
- **3.0 GA Enterprise Scale :** performance, HA, PRA/PCA, observabilité, documentation et support.

---

## 14. Principes de pilotage qualité

Chaque epic doit respecter :

- exigences rattachées ;
- critères d’acceptation mesurables ;
- tests unitaires ;
- tests d’intégration ;
- tests API ;
- tests de sécurité si concerné ;
- tests de performance si volumétrie ou concurrence ;
- documentation utilisateur ou exploitation ;
- traçabilité dans les matrices ;
- validation CI/CD ;
- preuve de non-régression.

Une fonctionnalité est considérée terminée uniquement si elle est intégrée, testée, documentée, validée et observable.

---

## 15. Roadmap des validations

Le fichier `09-roadmap-tests-validation.csv` détaille les tests par phase. Les validations bloquantes majeures sont :

- migrations et partitionnement en P02 ;
- réservation IP concurrente en P05 ;
- réconciliation sans écrasement silencieux en P07 ;
- RBAC/ABAC et secrets en P10 ;
- performance, chaos, upgrade et PRA en P14.

---

## 16. Risques majeurs

Le fichier `08-roadmap-risques.csv` contient le registre initial. Les risques à suivre dès le lancement sont :

- volumétrie extrême PostgreSQL ;
- dérive de scope ;
- complexité discovery ;
- qualité insuffisante de la donnée ;
- exposition de données par IA/RAG ;
- bascule PostgreSQL insuffisamment testée ;
- complexité des connecteurs ;
- UI avancée DCIM/graphes.

---

## 17. Décision de lancement recommandée

Le programme peut être lancéé si les conditions suivantes sont réunies :

- sponsor métier et sponsor technique nommés ;
- product owner disponible ;
- architecte entreprise et architecte solution assignés ;
- DBA PostgreSQL senior assigné dès P01 ;
- SRE assigné dès P01 ;
- QA automation présent dès P01 ;
- backlog exigences importé dans l’outil de pilotage ;
- gates Go/No-Go acceptés ;
- environnement de développement prévu ;
- stratégie de données de test validée ;
- politique de sécurité et secrets définie.

Sans ces prérequis, le risque de produire un prototype non industrialisable est élevé.
