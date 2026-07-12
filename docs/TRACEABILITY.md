## v0.31.4 — Correctif runtime Prometheus multiprocessus

| Exigence | Implémentation | Vérification |
|---|---|---|
| Runtime non-root | UID/GID Docker déterministes `10001:10001`, identiques au tmpfs Compose | test de contrat Docker/Compose et validateur observabilité |
| Démarrage multiprocessus | préflight d'écriture, nettoyage des fichiers mmap et diagnostic explicite avant Uvicorn | tests unitaires succès/refus et tests d'interfaces |
| Compatibilité | aucune migration, route métier, commande CLI ou feuille CSS modifiée | gates OpenAPI, packaging et comparaison CSS |

- Portée 0.31.4 : correctif de démarrage de l'observabilité multiprocessus ; EPIC-2005 reste fonctionnellement inchangé.

## v0.31.3 — P20 / EPIC-2005, observabilité et charge Enterprise

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| EPIC-2005 / CDC-PERF-008 / REQ-00837 / REQ-00838 | `OpenInfraTelemetry`, métriques Prometheus, traces OpenTelemetry, `/metrics` API/web | tests unitaires et intégration ASGI, validateur d'observabilité |
| SLO calculables | règles Prometheus, dashboard Grafana, métriques HTTP/files/workers/DB/réplication | validation YAML/JSON et tests de contrats |
| Qualification p95/p99 et saturation | profil versionné, cinq phases de charge, seuils exacts | tests du runner et moteur de certification |
| Endurance et absence de fuite | durée 6 h, mémoire/GC, métriques complètes | preuve `endurance.json` obligatoire |
| Chaos et récupération | quatre scénarios contrôlés, intégrité avant/après, perte acquittée interdite | tests du runner et preuve chaos obligatoire |
| Certification probatoire | empreintes SHA-256, rapport atomique, `--enforce`, runner Enterprise protégé | tests négatifs complets et workflow manuel |

- Portée 0.31.3 : instrumentation et chaîne de certification entièrement livrées.
- Une certification Enterprise réelle n'est acquise qu'après exécution du workflow sur une topologie représentative ; le sandbox de build ne constitue pas cette preuve.
- Aucun changement de CDC/roadmap n'est requis : les exigences EPIC-2005 existaient déjà.

# Traçabilité OpenInfra

## v0.31.2 — P20 / EPIC-2004, frontend modulaire et virtualisé

| Exigence | Implémentation | Vérification |
|---|---|---|
| REQ-00836 / CDC-PERF-007 | manifeste léger et huit chunks métier chargés par import dynamique | tests de présence, unicité des 274 opérations et absence de définitions métier dans le shell |
| Cache de requêtes | TTL/LRU mémoire, déduplication, `AbortController`, invalidation et générations anti-réponse obsolète | tests Node de concurrence/invalidation et parité source/runtime |
| Virtualisation | fenêtres bornées au-delà de 40 résultats dans les portails packagé et React | tests de bornes, géométrie et intégration |
| Web Vitals | LCP 2 500 ms, INP 200 ms et tâches longues 200 ms, mesures mémoire bornées | tests observers/budgets et événement `openinfra:web-vital` |
| Budgets bundle | JS initial brut ≤ 250 Kio et shell initial gzip ≤ 150 Kio | gate Vite, test Python et build CI |
| Compatibilité | routes, identifiants, permissions, i18n et thème inchangés | contrats frontend, API, accessibilité, comparaison CSS et smoke wheel |

- Portée 0.31.2 : EPIC-2004 fonctionnellement livré ; la qualification Web Vitals p75 sur topologie réelle et la certification de charge restent dans EPIC-2005.

## v0.31.1 — P20 / EPIC-2003, workers spécialisés métier

| Exigence | Implémentation | Vérification |
|---|---|---|
| REQ-00835 / EPIC-2003 | `ImportWorker`, `GraphWorker`, `RagWorker` sur le socle async partagé | tests unitaires de dispatch/payload et cycles d’intégration réels |
| Imports hors chemin interactif | artefact source externe, import simple ou massif, rapport résultat externalisé | tests import appliqué, bulk, erreurs et retry/DLQ |
| Graphes hors chemin interactif | traverse, impact, path, SPOF et export via worker `graph` | tests des cinq opérations et export d’artefact |
| RAG hors chemin interactif | sync RSOT, import documentaire borné, export réponses JSON/CSV | tests validation documentaire, pagination et formats |
| Moindre privilège | rôles workers dédiés combinant `async.worker` et permissions métier minimales | tests d’authentification par permission |
| Parité publique | dépôt d’artefacts et workers exposés en CLI, HTTP et OpenAPI | tests interfaces, découverte API et smoke wheel |

- Portée 0.31.1 : périmètre fonctionnel EPIC-2003 terminé ; la qualification PostgreSQL/S3 réelle, la rétention et le capacity planning restent des gates d’exploitation P20.

## v0.31.0 — P20 / EPIC-2003, incrément outbox et worker reporting

| Exigence | Implémentation | Vérification |
|---|---|---|
| REQ-00835 / EPIC-2003 | domaine async, service, repository JSON/PostgreSQL, migration `0054` | tests domaine, service, interfaces et migration |
| Atomicité et idempotence | unité de travail job/outbox/audit, clé unique par tenant | tests transactionnels et reprise |
| Fencing, retry et DLQ | lease token monotone, retries bornés, replay administré | tests stale worker, expiration et DLQ |
| Artefacts hors base | filesystem atomique et S3 compatible SigV4 | tests intégrité, tenant, signature et configuration |
| Parité publique | CLI, HTTP, OpenAPI et métriques | tests CLI/API/OpenAPI et smoke wheel |

- Portée 0.31.0 : socle générique et worker reporting pilote ; les workers imports, graphe et RAG restent à brancher dans les incréments suivants d’EPIC-2003.

## v0.30.7 — Pagination keyset et exports progressifs

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| REQ-00834 / EPIC-2002 — curseurs opaques | `CursorTokenCodec`, `PostgreSQLKeysetPage`, liaison tenant/filtres/scope et HMAC-SHA256 | tests unitaires de signature, altération, expiration de contexte et types |
| Pagination profonde stable | prédicats lexicographiques, index `0053`, suppression des `OFFSET` directs | test migration, gate source et benchmark p50/p95/p99 |
| Compatibilité ascendante | acceptation transitoire des curseurs numériques et émission immédiate d’un opaque | tests legacy offset et reprise opaque |
| Exports bornés | itération par pages, `SpooledTemporaryFile`, JSON/CSV/XLSX progressifs | tests de générateur one-shot, bascule disque, formats et signatures |
| CI/packaging | gate P20 dédié, benchmark JSON et migration embarquée | workflow CI, smoke wheel/sdist, quality gate |

## v0.30.0 — Socle haute performance Pro et Entreprise

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| REQ-00829 / EPIC-1901 — ASGI API/Web | `interfaces/asgi.py`, `interfaces/asgi_web.py`, politiques workers par édition, backpressure et lifespan | `test_asgi_performance_runtime.py`, smoke installé, quality gate |
| REQ-00830 / EPIC-1902 — pool PostgreSQL borné | `PostgreSQLConnectionPoolSettings`, `PostgreSQLConnectionPool`, budget workers × pool | tests acquisition, restitution, fermeture, timeout et configuration invalide |
| REQ-00831 / EPIC-1903 — BFF persistant/streaming | `httpx.AsyncClient` partagé, limites keep-alive, timeouts séparés et `client.stream` | tests MockTransport, flux brut, HEAD, corps bornés, erreurs et lifespan |
| REQ-00838 / EPIC-1904 — gate p95/p99 P19 | `benchmark_high_performance_runtime.py`, rapport JSON, contrôle CI bloquant | p95/p99 API, bootstrap et proxy ; `capacity_certification=false` |
| REQ-00840 — compatibilité | runtime `legacy`, contrats inchangés et portée d’environnement restaurée | régression CLI/HTTP/Web/OpenAPI, interruption et erreur de démarrage |
| EPIC-1905 — gouvernance | CDC 4.9.0, roadmap 2.1.0, ADR-0018 à ADR-0020, matrice performance et runbook | validateurs CDC/roadmap et `validate_enterprise_alignment.py` |

Les exigences REQ-00832 à REQ-00839 qui nécessitent PgBouncer, réplicas, pagination curseur, outbox/workers, frontend modulaire, observabilité système et stockage objet restent séquencées en P20. La réussite du benchmark P19 ne vaut pas certification de capacité Pro/Entreprise.

## v0.29.105 — Optimisation du chargement web

- Défaut corrigé : chargement lent du portail packagé, particulièrement lorsque le backend ou les catalogues métier répondent lentement.
- Transport : compression gzip déterministe, ETag par représentation, revalidation `304` et cache immutable des ressources versionnées.
- Bootstrap : endpoint local `/bootstrap.json` agrégeant configuration, statut BFF et version ; `/ready` reste asynchrone et non bloquant.
- Données métier : chargement paresseux et dédupliqué des catalogues pays, ITAM et DCIM selon les champs du formulaire sélectionné.
- UX/accessibilité : shell de chargement immédiatement visible, état de chargement annoncé par région `status`, sans régression WCAG 2.2 AA.
- Tests/CI : budgets gzip, cache, ETag, réponse 304, fan-out de démarrage, parité React/runtime, typage strict et régression web dédiée.
- CDC/roadmap : inchangés ; il s’agit d’un correctif de performance et de fiabilité sans évolution du périmètre contractuel.

## v0.29.104 — Reprise après sinistre multisite

- Roadmap existante : réalisation de P17 / `EPIC-1703`, sans extension du périmètre fonctionnel.
- Domaine : plans primaire/secours, mode de réplication, objectifs RPO/RTO, fraîcheur de sauvegarde et preuves immuables d’exercices `primary-site-loss`.
- Application : contrôle `multisite.admin`, garde Pro/Enterprise, validation des sites DCIM, évaluation déterministe de sept critères et audit transactionnel.
- Persistance : adaptateurs JSON/PostgreSQL, deux tables hash-partitionnées, contraintes, index et migration additive `0052`.
- Interfaces : sept commandes CLI, sept routes HTTP/OpenAPI et parité des portails React/runtime statique sous DCIM.
- Sécurité : aucune promotion, restauration, opération de fencing ou mutation DNS/VIP automatique ; `automatic_promotion=false` est inscrit dans l’audit.
- Exploitation : runbook de préparation, site loss, validation, failback et rollback non destructif.
- Tests/CI : domaine, service, CLI, HTTP, PostgreSQL, migration, Web, packaging et gate de régression dédié.
- CDC/roadmap : inchangés, car EPIC-1703 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## v0.29.103 — Multisite Enterprise distribué

- Roadmap existante : réalisation de P17 / `EPIC-1702`, sans extension du périmètre fonctionnel.
- Domaine : `RegionalDiscoveryRoute`, portée déterministe région/site/VRF, cycle actif/désactivé et réaffectation idempotente.
- Application : contrôle `multisite.admin`, garde d’édition Enterprise, validation DCIM/collector et délégation au moteur de jobs Discovery.
- Persistance : adaptateurs JSON/PostgreSQL, table hash-partitionnée, unicité du triplet de routage, clé étrangère collector et index d’audit.
- Interfaces : cinq commandes CLI, cinq routes HTTP, OpenAPI et parité des portails React/runtime statique.
- Sécurité : endpoint HTTPS obligatoire, collectors proxy uniquement, portée exacte, revalidation avant chaque job et aucun secret matérialisé.
- Tests/CI : domaine, service, CLI, HTTP, PostgreSQL, migration, Web, packaging et gate de régression dédié.
- CDC/roadmap : inchangés, car EPIC-1702 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## v0.29.102 — Multisite Pro centralisé

| Exigence | Implémentation | Tests / preuve |
|---|---|---|
| P17 / EPIC-1701 : backend central Pro multisite | `domain/multisite.py`, `application/multisite_services.py`, feature gate `centralized_multisite` | `test_multisite_services.py` vérifie Pro/Enterprise et le refus Lite |
| RBAC par site combiné aux rôles globaux | permissions `multisite.*`, rôles dédiés, affectations `SiteAccessGrant` | tests domaine, service, HTTP et CLI |
| Rapports consolidés par site | `MultisitePortfolioReport` et agrégation DCIM bornée | tests service et API avec contrôle anti-rapport partiel |
| Persistance scalable et auditée | JSON, PostgreSQL hash-partitionné, migration `0050`, audit transactionnel | tests repository et migration |
| Parité des interfaces | CLI `multisite`, 7 routes REST/OpenAPI, parcours DCIM Web | tests CLI, HTTP, OpenAPI et contrat Web |
| Absence d’agent régional en Pro | aucun endpoint/objet collector introduit ; feature distincte des agents Enterprise | test de contrat Web et revue de migration |

## v0.29.101 — RAG gouverné et cité

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| P16 / EPIC-1606, REQ-00013, REQ-00250 à REQ-00255 | `domain/rag.py`, `application/rag_services.py`, générateur extractif local | tests domaine, service et cas de sécurité |
| Filtrage avant recherche | permissions par document et requêtes JSON/PostgreSQL tenant-aware | tests Viewer/Admin et dépôt PostgreSQL |
| Réponses avec citations | `RagAnswer`, `RagCitation`, statut `insufficient-context` | tests invariants, HTTP et CLI |
| Synchronisation RSOT sans mutation | projection versionnée et permission `rsot.read` | tests service et absence de route destructive |
| Imports/exports relançables | `RagTransferJob`, lots, idempotence et artefacts SHA-256 | tests jobs, export JSON/CSV et téléchargement |
| Interfaces regroupées sous RSOT | 13 routes, commandes `rag`, React/runtime statique | tests OpenAPI, web, accessibilité et packaging |
| Persistance et audit | migration `0049_rag_governed_assistant.sql`, JSON/PostgreSQL, outbox | tests migration, repository et smoke du wheel |

## v0.29.100 — Correctif de démarrage du portail web

- Défaut corrigé : écran blanc du runtime statique lors du calcul des métriques SBOM.
- Cause : références à `FIELD_SETS.cursor` non déclaré dans cinq opérations de sécurité.
- Prévention : validation CI des références partagées, validation runtime du catalogue, rendu initial avant I/O et écran d’erreur accessible.

## v0.29.99 — SBOM, vulnérabilités et exposition contextualisée

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| P16 / EPIC-1605 | `domain/sbom.py`, `application/sbom_services.py`, adaptateurs JSON/PostgreSQL | tests domaine, service, CLI, HTTP et persistance |
| CycloneDX/SPDX versionnés | `SbomPayloadParser`, `SbomDocument`, empreintes et versions incrémentales | tests parseur, idempotence et comparaison de releases |
| CVE et exposition contextualisée | `VulnerabilityRecord`, `ExposureContext`, `RiskAssessment`, `RiskFinding` | tests score, exploitation connue, flux, criticité et contrôles compensatoires |
| Comparaison de releases | identité PURL logique et `SbomComparison` | tests ajout, retrait et changement de version |
| Interfaces regroupées sous Sécurité | 14 routes HTTP/OpenAPI, commandes `sbom`, portail React/runtime | tests CLI, HTTP, web, accessibilité et OpenAPI |
| Persistance et audit | migration `0048_sbom_vulnerabilities_exposure.sql`, dépôts, index et outbox | tests migration, PostgreSQL, packaging et smoke du wheel |
| Absence d’action intrusive | aucun scanner actif, aucun exécuteur ni remédiateur | tests frontend, revue statique et gate CI SBOM |

## v0.29.98 — GreenOps, énergie et capacité

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| P16 / EPIC-1604 | `domain/greenops.py`, `application/greenops_services.py`, adaptateurs JSON/PostgreSQL | tests domaine, service, CLI, HTTP et persistance |
| Mesures observées/estimées et provenance | `MeasurementKind`, `MeasurementSource`, `EnergyMeasurement` | `test_greenops_domain.py`, `test_greenops_services.py` |
| PUE, énergie et CO₂e reproductibles | `SustainabilityReport`, `CarbonFactor`, `GreenOpsPolicy` | tests rapports, facteurs, hypothèses et exports |
| Capacité, anomalies et recommandations | `CapacityForecast`, `EnergyAnomaly`, `ConsolidationCandidate`, `GreenScore` | tests prévisions, seuils et validation humaine obligatoire |
| Idempotence globale par tenant | registre PostgreSQL `greenops_measurement_idempotency` et digest SHA-256 | `test_greenops_migration.py`, contrats PostgreSQL |
| Interfaces regroupées sous DCIM | 16 routes HTTP/OpenAPI, commandes `greenops`, portail React/runtime | tests CLI, HTTP, web, accessibilité et OpenAPI |
| Persistance à grande volumétrie | migration `0047_greenops_energy_capacity.sql`, partitions temporelles et index | tests migration, packaging et smoke du wheel |

## v0.29.97 — Traçabilité FinOps et rangement de navigation

- Roadmap : P16 / `EPIC-1603` — consolidation des coûts et showback par service/tenant.
- Domaine : règles d’allocation, imports, coûts, périodes, budgets, anomalies, prévisions et rapports en précision `Decimal`.
- Application : imports idempotents, allocation déterministe, bucket non attribué, clôture par digest, showback et chargeback sans mutation comptable.
- Infrastructure : dépôts JSON/PostgreSQL, mapper, outbox et migration `0046_finops_costs_showback.sql`.
- Interfaces : 18 commandes/routes FinOps et groupe web **ITAM → FinOps & coûts**.
- Navigation : **Flux réseau** et **Conformité réseau** sous IPAM ; **Certificats & PKI** sous Sécurité.
- Tests : domaine, cas limites, service, HTTP, CLI, OpenAPI, migration, portail, sécurité, packaging et non-régression.

## v0.29.96 — Traçabilité simulation et migration

- Roadmap : P16 / `EPIC-1602` — simulation de changement, analyse d’impact et planification de migration.
- CDC : `REQ-00414` à `REQ-00428`.
- Domaine : scénarios, changements typés, constats, scores de préparation, groupes, blocages, vagues, rapports et comparaisons.
- Application : moteur d’impact réutilisant RSOT, Graphe et matrice de flux, sans mutation de production.
- Infrastructure : dépôts JSON/PostgreSQL, mapper, outbox et migration `0045_simulation_migration_planning.sql`.
- Interfaces : commandes `simulation`, neuf routes HTTP/OpenAPI et groupe web **RSOT → Simulation & migrations**.
- Tests : domaine, service, CLI, HTTP, OpenAPI, migration, portail, sécurité, packaging et non-régression.

## v0.29.95 — Field Operations mobile/offline

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| EPIC-1601, REQ-00399 à REQ-00413 | `domain/field_operations.py`, `application/field_operation_services.py`, adaptateurs JSON/PostgreSQL, migration `0044` | tests domaine, services, HTTP, CLI, migration, frontend |
| Fiche issue d’une cible localisée | `FieldLocationResolver`, `FieldOperationSheet` | `test_field_operation_services.py`, `test_field_operations_domain.py` |
| QR, checklist, preuves avant/après | domaine Field Operations et routes `/api/v1/field-*` | tests domaine, API et CLI |
| Verrou logique non bloquant pour les lectures | `InterventionLock`, repository idempotent et TTL | tests conflits, expiration et libération |
| Offline contrôlé, borné et expirant | `OfflineSyncPackage`, permission `field.sync`, SHA-256 canonique | tests création, lecture, synchronisation et empreinte invalide |
| Audit et outbox | transactions JSON/PostgreSQL, `field_event_outbox` partitionnée | tests workflow et migration |
| Mobile web organisé sous DCIM | React et runtime statique, contexte `Opérations terrain` | tests Node, accessibilité et contrats web |

## v0.29.94 — Performance volumétrique du graphe RSOT

- Roadmap existante : réalisation de `EPIC-1506` sans modification de son périmètre ni création d’une exigence CDC.
- Code : `openinfra.quality.dependency_graph_benchmark` génère deux topologies indexées et mesure parcours, filtre, SPOF et pagination.
- Tests : `test_dependency_graph_benchmark.py`, `test_dependency_graph_volume.py` et contrat GitHub Actions.
- CI : gate 5 000 nœuds sur Python 3.13, seuils p95 bloquants et rapport JSON.
- Documentation : objectifs, méthode, codes de sortie et commande reproductible dans le runbook Graphe.
- CDC et roadmap non réémis : aucune nouvelle recommandation fonctionnelle, technique, réglementaire ou architecturale.

## v0.29.93 — Traçabilité OpenAPI et formulaires globaux

- CDC : compléments v0.29.93 dans les exigences API/formulaires et RSOT.
- Roadmap : `REQ-00826` → `TST-P08-WEB-TYPED-VALIDATED-FORMS`, `REQ-00827` → `TST-P01-OPENAPI-UNIQUE-YAML-KEYS`, `REQ-00828` → `TST-P15-GRAPH-RSOT-NAVIGATION`.
- OpenAPI : suppression des routes DCIM dupliquées dans les deux documents et validation des clés YAML uniques.
- Interface : moteur commun `form-fields.js` pour inférence de type, validation amont et normalisation des valeurs.
- Dates : contrôles natifs `date`/`datetime-local`, style OpenInfra et conversion ISO-8601 avant appel API.
- Saisies libres : email, téléphone, code postal contextualisé par pays, IPv4/IPv6, CIDR, MAC, hostname, URL, JSON, CSV et texte contrôlés.
- Navigation : Graphe intégré aux groupes RSOT exploration, analyse d’impact et exports.
- Accessibilité : erreurs exposées par `aria-invalid` et validation native ; focus des formulaires sans modification d’épaisseur.
- CI : test de non-régression des doublons YAML, parité React/runtime et présence de l’asset partagé dans le wheel.

## v0.29.92 — Traçabilité visualisations d’impact et SPOF

- Roadmap existante : P15 / `EPIC-1505` — visualisations d’impact et identification des SPOF critiques.
- Domaine : `DependencySpofCandidate`, `DependencySpofReport`, `DependencyGraphExport` et formats JSON/CSV/GraphML.
- Application : analyse de dominateurs enracinés, filtres, classement, pagination opaque, signalement de troncature et exports bornés.
- Interfaces : commandes `graph spof` et `graph export`, routes `/api/v1/graph/spof` et `/api/v1/graph/export`, OpenAPI et portail FR/EN.
- UI : graphe en couches accessible, classement tabulaire SPOF, résultat brut, téléchargement et parité React/runtime packagé.
- Garanties : lecture seule RSOT, permission `rsot.read`, isolation tenant, audit, limites de charge, absence de remédiation automatique et écriture atomique des exports CLI.
- Tests : domaine, service, pagination, chemins alternatifs, formats d’export, CLI, HTTP, OpenAPI, web, accessibilité, sécurité et smoke du wheel.
- Base de données : aucune migration ; la projection réutilise les objets et relations RSOT existants.
- CDC/roadmap : inchangés, car EPIC-1505 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## v0.29.91 — Traçabilité conformité réseau

- Domaine : `network_config_compliance.py`.
- Application : `network_config_compliance_services.py`.
- Infrastructure : adaptateurs JSON/PostgreSQL et migration `0043_network_config_compliance.sql`.
- Interfaces : commandes `network-config`, six routes HTTP/OpenAPI et portail FR/EN.
- Roadmap : P15 / EPIC-1504 déjà planifié ; CDC et roadmap inchangés.

## v0.29.90 — Traçabilité certificats et PKI

- Roadmap existante : P15 / `EPIC-1503` — inventaire, chaînes, SAN, propriétaires, endpoints et alertes d'expiration.
- Domaine : `domain/certificate_pki.py` — matériau X.509, gouvernance, observations d'endpoints, hostname/SAN et états de santé.
- Application : `application/certificate_pki_services.py` — import, inventaire, retrait, observations idempotentes, évaluation bornée et audit.
- Infrastructure : `certificate_parser.py`, adaptateurs JSON/PostgreSQL et migration `0042_certificate_pki_inventory.sql`.
- Interfaces : sept commandes CLI, sept routes HTTP/OpenAPI et sept opérations web FR/EN.
- Sécurité : validation cryptographique des chaînes, refus des clés privées, permissions dédiées, isolation tenant et empreintes immuables.
- Tests : domaine, services, CLI, HTTP, portail, migration, row mapping PostgreSQL, CI, OpenAPI et packaging.
- CDC/roadmap : documents inchangés et non réémis ; l'epic et ses critères étaient déjà présents.

## v0.29.89 — Traçabilité matrice de flux

- Roadmap existante : P15 / `EPIC-1502` — matrice de flux déclarés et observés.
- Domaine : `domain/flow_matrix.py` — sélecteurs, protocoles, décisions, observations immuables et statuts de conformité.
- Application : `application/flow_matrix_services.py` — gouvernance, idempotence, comparaison bornée, pagination et audit.
- Persistance : adaptateurs JSON/PostgreSQL et migration `0041_flow_matrix.sql`, partitionnée et indexée par tenant.
- Interfaces : six commandes CLI, six routes HTTP/OpenAPI et six opérations web FR/EN.
- Sécurité : permissions `flow.read`/`flow.write`, rôles dédiés, isolation tenant et rejet des conflits d'idempotence.
- Tests : domaine, services, CLI, HTTP, portail, PostgreSQL, migration, OpenAPI, CI et packaging.
- CDC/roadmap : documents inchangés et non réémis ; l'epic et ses critères étaient déjà présents.

## v0.29.88 — Traçabilité accessibilité transversale

- CDC : `REQ-00789`, `REQ-00825`, `TST-WEB-090`, `TST-WEB-125`.
- Roadmap : P08 / `EPIC-0805`, `TST-P08-WEB-ACCESSIBLE-NAVIGATION`, `TST-P08-WEB-COMPACT-HEADER`.
- Code : portail React, runtime web packagé, moteur i18n partagé, feuille de style commune et workflow CI.
- Tests : lint JSX accessible, contrat DOM/CSS/ARIA Node.js, tests Python de parité, build Vite et validation frontend.
- Documentation : `docs/ui/WEB_ACCESSIBILITY.md`.

## v0.29.87 — Traçabilité ajustements header et mégamenu

- Exigences mises à jour : `REQ-00811` (mégamenu au survol/focus, clic de secours) et `REQ-00825` (hauteur initiale restaurée, recherche 50 % centrée, navigation compacte et états contrastés).
- Tests contractuels mis à jour : `TST-WEB-124`, `TST-WEB-125`, tests Node.js `responsive-navigation.test.mjs`, tests Python `test_responsive_navigation_contract.py` et `test_openinfra_web.py`.
- Roadmap réalignée sur `P08 / EPIC-0805` sans nouvel epic ni nouvelle migration.
- Parité stricte des assets `web/src/openinfra-theme.css` et `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`.

## v0.29.86 — Traçabilité navigation responsive web

- CDC : `REQ-00811` réalignée sur les trois modes de navigation et `REQ-00825` pour le header compact, les contrôles alignés et la hiérarchie des ombres.
- Roadmap : renforcement de `EPIC-0805` et ajout des validations `TST-P08-WEB-RESPONSIVE-NAVIGATION` et `TST-P08-WEB-COMPACT-HEADER`.
- Code : portail packagé `openinfra-web.js`, frontend React `main.jsx` et feuille de thème byte-identique.
- Garanties : sidebar uniquement sur écran large, mégamenu multicolonne intermédiaire, menu unique mobile, navigation complète, fermeture par `Échap`, backdrop et boutons, cibles tactiles de 44 px.
- Tests : Node.js, contrat Python, validation statique frontend et build Vite.

## v0.29.86 — Traçabilité graphe de dépendances RSOT

- Roadmap existante : P15 / `EPIC-1501` — graphe applications, services, réseau, stockage, DCIM et alimentation.
- Code : `domain/dependency.py`, `application/dependency_graph_services.py`, conteneur applicatif, CLI et API HTTP.
- Interfaces : commandes `graph traverse`, `graph impact`, `graph path`, routes `/api/v1/graph/*`, OpenAPI runtime et portail FR/EN.
- Garanties : lecture seule RSOT, isolation tenant, authentification `rsot.read`, parcours borné, cycles maîtrisés, historique `as_of`, résultats déterministes et audit.
- Tests : domaine, service, CLI, HTTP, portail, sécurité, OpenAPI et non-régression.
- Base de données : aucune migration ; réutilisation des objets et relations RSOT historisés.
- CDC/roadmap : EPIC-1501 était déjà planifié ; les documents sont néanmoins réémis en v0.29.86 pour la recommandation responsive distincte portée par `REQ-00811`, `REQ-00825` et `EPIC-0805`.

## v0.29.85 — Traçabilité nomenclature DCIM et i18n web

- `REQ-00820` → `TST-WEB-119` → `TST-P14-DCIM-GENERATED-BUILDING-FLOORS` → migration `0040_dcim_floor_nomenclature.sql`.
- `REQ-00824` → `TST-WEB-123` → `EPIC-0807` → `TST-P08-WEB-I18N-FR-EN`.
- Code : `FloorNomenclature`, migration JSON, dépôt PostgreSQL, CLI/API/OpenAPI et sélecteurs DCIM.
- UI : `web/src/i18n.js`, copie runtime byte-identique, tests Node.js, tests web Python, validateurs frontend et vérificateur d’artefact.
- Runtime web : priorité source/installé du portail packagé sur `web/dist`, avec test de non-régression après build React.

## v0.29.84 — Traçabilité correctif CI DCIM et GitHub Actions

- Incident CI historique : le smoke modèle physique utilisait `F01` après une ancienne normalisation concaténée, remplacée en v0.29.86 par les codes locaux `L-01`, `L00`, `L01`.
- Correction : extraction du champ `floor` dans la sortie JSON de `define-room`, puis réutilisation dans les commandes DCIM suivantes.
- Correction similaire : smoke câblage/énergie aligné sur le même contrat canonique.
- CI : `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, dependency review et CodeQL déjà compatibles Node.js 24.
- Prévention : tests des workflows et gate de sécurité interdisant les anciens majors Node.js 20.
- CDC/roadmap : non modifiés ; aucune nouvelle recommandation n’impacte l’existant.

## v0.29.83 — Traçabilité résilience workers et agents Discovery

- Roadmap existante : P14 / `EPIC-1406` — tests crash worker/agent, reprise jobs, DLQ, idempotence et non-perte.
- Migration : `0039_discovery_job_resilience.sql`.
- Code : domaine des jobs, port Discovery, dépôts JSON/PostgreSQL, service applicatif, CLI, API HTTP, OpenAPI et portail web.
- Garanties : bail expirant, fencing monotone, réservation concurrente atomique, retry borné, DLQ, rejeu audité et terminaison idempotente.
- Tests : domaine, service, concurrence, reprise après crash, interfaces CLI/HTTP, portail, migrations et authentification collector.
- CDC/roadmap : non modifiés ; aucune nouvelle recommandation n’impacte l’existant.

## v0.29.82 — Traçabilité réconciliation Discovery multisource

- CDC : `REQ-00823`, `TST-WEB-122`.
- Roadmap : P14 / `EPIC-1405`, `TST-P14-DISCOVERY-MULTISOURCE-RECONCILIATION`.
- Migration : `0038_discovery_multisource_reconciliation.sql`.
- Code : domaine Discovery, ports applicatifs, services, dépôts JSON/PostgreSQL, CLI, API HTTP, OpenAPI et portail web.
- Garanties : preuve immuable, scoring déterministe, conflit explicite, résolution justifiée, audit et `rsot_write_executed=false`.
- Tests : domaine, service, persistance JSON, CLI, API, web, migration et non-régression RSOT.

## v0.29.79 — Traçabilité profils Discovery

- CDC : `REQ-00819`, `TST-WEB-118`.
- Roadmap : `TST-P14-DISCOVERY-PROTOCOL-PROFILES`.
- Migration : `0034_discovery_protocol_profiles.sql`.
- Tests : domaine Discovery, service, CLI, API HTTP, politiques migrations, Ruff et Bandit.
