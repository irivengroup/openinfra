# Volume 23 — Kubernetes avancé et mapping cloud-native

**Version :** 4.0.0  
**Statut :** obligatoire pour OpenInfra Enterprise  
**Domaine :** `K8S`  
**Nature :** spécification fonctionnelle et technique détaillée  
**Exclusion constante :** ce volume ne crée aucun module ITSM intégré.

## 1. Objectif

Cartographier Kubernetes et les environnements cloud-native de bout en bout, du pod jusqu’au rack, au réseau, aux certificats, aux flux et au service métier.

Ce volume complète le socle SFG/STG v3 en ajoutant des capacités fonctionnelles de niveau entreprise. Il conserve les exigences transversales OpenInfra : PostgreSQL Cluster, partitionnement des tables massives, API-first, sécurité Zero Trust, audit immuable, haute disponibilité, concurrence contrôlée, traitements asynchrones et traçabilité exigence → cas d’usage → test.

## 2. Périmètre fonctionnel obligatoire

| Capacité obligatoire |
|---|
| inventaire clusters, namespaces, nodes, workloads, pods, services, ingress, network policies et volumes |
| mapping pod → node → VM → hyperviseur → serveur → rack → salle |
| corrélation images, SBOM, certificats, secrets référencés et expositions externes |
| multi-cluster et clusters managés cloud |
| conformité labels, annotations, propriétaires et environnements |
| dépendances service mesh, ingress, load balancer et DNS |
| analyse capacité CPU/mémoire/stockage par cluster et namespace |
| détection dérives entre état attendu GitOps et état découvert |

## 3. Cas d’usage représentatifs

- Retrouver sur quel serveur physique et quel rack tourne un pod critique.
- Identifier les services Kubernetes exposés publiquement sans propriétaire.
- Comparer l’état GitOps attendu avec l’état découvert dans un cluster.

## 4. Modèle de données logique

Les entités suivantes sont ajoutées au dictionnaire de données v4. Elles doivent être modélisées avec identifiant stable, tenant, statut, propriétaire, horodatage, audit, règles de rétention et contraintes d’intégrité adaptées.

- `kubernetes_cluster`
- `kubernetes_namespace`
- `kubernetes_node`
- `kubernetes_workload`
- `kubernetes_pod`
- `kubernetes_service`
- `kubernetes_ingress`
- `kubernetes_network_policy`
- `persistent_volume`
- `storage_class`
- `container_image`
- `gitops_state`
- `service_mesh_relation`
- `managed_cluster_account`
- `kubernetes_compliance_finding`

## 5. Règles de gestion

- Toute donnée modifiée par ce volume doit être historisée avec ancien état, nouvel état, acteur, source et corrélation.
- Toute opération de masse doit proposer un dry-run lorsque l’effet métier est significatif.
- Tout export volumineux doit être asynchrone, paginé, borné et journalisé.
- Toute intégration externe doit être idempotente et protégée par rate limiting, timeout et circuit breaker.
- Toute donnée sensible doit être masquée dans les logs, exports et réponses API non privilégiées.
- Toute ressource doit être isolée par tenant et contrôlée par RBAC/ABAC.
- Les données massives doivent appliquer la stratégie hot/warm/cold et ne jamais être stockées dans une table monolithique non partitionnée.

## 6. APIs et événements

### Ressources REST minimales

- `/kubernetes-clusters`
- `/kubernetes-workloads`
- `/kubernetes-services`
- `/kubernetes-ingress`
- `/gitops-states`
- `/kubernetes-compliance-findings`

### Événements métier

- `kubernetes.workload.discovered`
- `kubernetes.exposure.detected`
- `kubernetes.gitops.drift.detected`

Les événements doivent être publiés via l’outbox transactionnelle OpenInfra afin de préserver la cohérence entre PostgreSQL et le bus d’événements.

## 7. Sécurité et conformité

- RBAC obligatoire par action : lecture, création, modification, suppression, export, administration, exécution de job.
- ABAC obligatoire pour tenant, site, environnement, criticité, propriétaire et domaine.
- Audit immuable pour toute opération critique.
- Secrets et données sensibles jamais exposés en clair.
- Webhooks signés et rejouables de manière contrôlée.
- Intégration SIEM possible par export événementiel.

## 8. Performance, volumétrie et résilience

- Pagination cursor-based obligatoire pour toute liste.
- Filtres sélectifs obligatoires sur endpoints massifs.
- Tris uniquement sur colonnes indexées.
- Jobs longs exécutés par workers spécialisés.
- Idempotency keys obligatoires pour imports, synchronisations et opérations critiques.
- Tables d’événements, observations, findings, mesures et historiques partitionnées par temps + tenant lorsque la volumétrie le justifie.
- Lecture analytique routable vers réplicas ou réplica reporting.
- p95 API critique inférieur à 500 ms sur jeux représentatifs.
- p99 API critique inférieur à 1 500 ms sur jeux représentatifs.

## 9. Critères d’acceptation

- un workload est rattachable à son service métier, son image, ses flux et son infrastructure sous-jacente
- les secrets Kubernetes sont référencés sans exposition de valeur
- les clusters managés conservent compte, région et fournisseur
- les données volumineuses de pods et événements sont bornées et partitionnées

## 10. Risques fonctionnels principaux

- Volatilité élevée des objets Kubernetes
- Exposition accidentelle de métadonnées sensibles

## 11. Exigences vérifiables du volume

| ID | Priorité | Type | Exigence | Vérification | Acceptation |
|---|---:|---|---|---|---|
| REQ-00459 | N1 | Fonctionnelle | OpenInfra doit fournir le module Kubernetes avancé et mapping cloud-native avec APIs, UI, audit, RBAC, imports/exports contrôlés et traçabilité complète. | Test fonctionnel bout-en-bout, revue API/UI et vérification audit. | Le module Kubernetes avancé et mapping cloud-native est utilisable par API et UI avec droits, audit et critères d’acceptation vérifiés. |
| REQ-00460 | N1 | Fonctionnelle | Le module Kubernetes avancé et mapping cloud-native doit être strictement séparé du périmètre ITSM et ne doit pas créer de ticket, incident, demande ou changement natif. | Revue fonctionnelle et tests négatifs sur les workflows. | Aucune capacité de ticketing natif n’est exposée dans ce module. |
| REQ-00461 | N1 | Données | Le modèle de données du module Kubernetes avancé et mapping cloud-native doit utiliser des entités typées, contraintes d’intégrité, propriétaires, tenant, statut, historique et audit. | Revue dictionnaire, tests migrations et tests contraintes. | Chaque entité critique possède clé stable, contraintes, audit et règles de rétention. |
| REQ-00462 | N1 | Performance | Les données volumineuses du module Kubernetes avancé et mapping cloud-native doivent être partitionnées, paginées, indexées et exploitées sans scan complet non maîtrisé. | Analyse DDL, tests EXPLAIN, benchmark API. | Les requêtes critiques utilisent les index attendus et les exports massifs sont asynchrones. |
| REQ-00463 | N1 | Sécurité | Le module Kubernetes avancé et mapping cloud-native doit appliquer RBAC/ABAC, isolation tenant, masquage des données sensibles et audit immuable des opérations critiques. | Tests RBAC/ABAC, tests audit et tests sécurité. | Un utilisateur sans droit ne peut ni lire ni modifier les ressources hors périmètre. |
| REQ-00464 | N1 | Résilience | Les traitements longs du module Kubernetes avancé et mapping cloud-native doivent être asynchrones, idempotents, relançables, annulables si possible et suivis par métriques. | Tests worker, crash recovery, dead-letter queue et reprise. | Un crash worker ne perd aucun job validé et l’état final reste cohérent. |
| REQ-00465 | N2 | Observabilité | Le module Kubernetes avancé et mapping cloud-native doit exposer métriques, logs structurés, traces et événements métier corrélables. | Test observabilité et contrôle dashboards. | Chaque opération critique produit log, métrique, trace et événement corrélés. |
| REQ-00466 | N1 | API | Les APIs du module Kubernetes avancé et mapping cloud-native doivent supporter pagination cursor-based, filtres sélectifs, tri indexé, OpenAPI et webhooks métier. | Tests API contractuels et tests de charge. | Les endpoints refusent les lectures volumineuses non filtrées et les contrats API sont validés. |
| REQ-00467 | N1 | Audit | Toute modification métier du module Kubernetes avancé et mapping cloud-native doit conserver ancien état, nouvel état, acteur, source, corrélation et preuve. | Tests audit et relecture historique. | Un changement peut être reconstitué avec preuve et horodatage. |
| REQ-00468 | N2 | Intégration | Le module Kubernetes avancé et mapping cloud-native doit publier des événements temps réel et consommer les données des autres domaines OpenInfra sans duplication incohérente. | Test event bus et test cohérence inter-domaines. | Les relations transverses sont référencées par identifiants stables et contrôles d’intégrité. |
| REQ-00469 | N1 | Fonctionnelle | Le module Kubernetes avancé et mapping cloud-native doit fournir au moins les capacités suivantes : inventaire clusters, namespaces, nodes, workloads, pods, services, ingress, network policies et volumes; mapping pod → node → VM → hyperviseur → serveur → rack → salle; corrélation images, SBOM, certificats, secrets référencés et expositions externes; multi-cluster et clusters managés cloud. | Scénarios nominaux API/UI et tests fonctionnels. | Les quatre capacités prioritaires sont démontrées avec données représentatives. |
| REQ-00470 | N2 | Fonctionnelle | Le module Kubernetes avancé et mapping cloud-native doit fournir les capacités avancées suivantes : conformité labels, annotations, propriétaires et environnements; dépendances service mesh, ingress, load balancer et DNS; analyse capacité CPU/mémoire/stockage par cluster et namespace; détection dérives entre état attendu GitOps et état découvert. | Tests fonctionnels et revue documentaire. | Les capacités avancées sont documentées, sécurisées et traçables. |
| REQ-00471 | N1 | Qualité | Les données du module Kubernetes avancé et mapping cloud-native doivent être vérifiées par règles qualité, exceptions justifiées et rapports de conformité. | Tests règles qualité et tests exceptions. | Les écarts sont détectés, priorisés, historisés et exportables. |
| REQ-00472 | N2 | Exploitation | Le module Kubernetes avancé et mapping cloud-native doit disposer de runbooks d’exploitation, sauvegarde, purge, restauration et support diagnostic. | Revue runbooks et test restauration ciblée. | Les procédures sont exécutables et reliées aux métriques de supervision. |
| REQ-00473 | N1 | Acceptation | Le module Kubernetes avancé et mapping cloud-native doit disposer de critères d’acceptation mesurables, de tests automatisés et d’une traçabilité exigence → cas d’usage → test. | Contrôle matrice de traçabilité. | Aucune exigence N1 du module n’est orpheline. |

## 12. Traçabilité

Toutes les exigences ci-dessus sont rattachées dans `11-Matrices/Traceabilite.csv` au cas d’usage `UC-0021` et aux tests `TST-REQ-*`. Les entités ajoutées sont présentes dans `04-Donnees/Dictionnaire.csv`.
