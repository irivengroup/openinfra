# Volume 15 — Flux réseau, matrices de flux et segmentation

**Version :** 4.0.0  
**Statut :** obligatoire pour OpenInfra Enterprise  
**Domaine :** `FLOW`  
**Nature :** spécification fonctionnelle et technique détaillée  
**Exclusion constante :** ce volume ne crée aucun module ITSM intégré.

## 1. Objectif

Maintenir une matrice de flux déclarée, l’observer en continu et la comparer aux flux réels pour soutenir sécurité, migration, segmentation et analyse d’impact.

Ce volume complète le socle SFG/STG v3 en ajoutant des capacités fonctionnelles de niveau entreprise. Il conserve les exigences transversales OpenInfra : PostgreSQL Cluster, partitionnement des tables massives, API-first, sécurité Zero Trust, audit immuable, haute disponibilité, concurrence contrôlée, traitements asynchrones et traçabilité exigence → cas d’usage → test.

## 2. Périmètre fonctionnel obligatoire

| Capacité obligatoire |
|---|
| modélisation source, destination, protocole, port, environnement, justification et durée de validité |
| comparaison flux déclarés et flux observés par NetFlow, sFlow, IPFIX, firewall logs et discovery applicative |
| détection des flux non autorisés, orphelins, expirés ou déclarés mais non observés |
| visualisation des flux par application, service, tenant, VRF, site et environnement |
| export contrôlé vers équipes firewall ou outils de sécurité externes |
| simulation d’impact avant modification firewall, segmentation ou migration |
| gestion des flux temporaires avec expiration et audit |
| corrélation flux ↔ dépendances applicatives ↔ IPAM ↔ certificats |

## 3. Cas d’usage représentatifs

- Comparer les flux observés entre une application web et sa base de données avec les flux déclarés.
- Identifier les flux de production vers recette non autorisés.
- Simuler le blocage d’un port firewall et lister les applications impactées.

## 4. Modèle de données logique

Les entités suivantes sont ajoutées au dictionnaire de données v4. Elles doivent être modélisées avec identifiant stable, tenant, statut, propriétaire, horodatage, audit, règles de rétention et contraintes d’intégrité adaptées.

- `flow_rule`
- `flow_observation`
- `flow_matrix`
- `flow_endpoint`
- `flow_protocol`
- `flow_justification`
- `flow_expiration_policy`
- `observed_connection`
- `firewall_policy_mapping`
- `segmentation_zone`
- `flow_risk_score`
- `flow_exception`
- `flow_export_job`
- `flow_drift`
- `flow_impact_report`

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

- `/flow-rules`
- `/flow-observations`
- `/flow-matrices`
- `/segmentation-zones`
- `/flow-drift`
- `/flow-impact-reports`

### Événements métier

- `flow.observed`
- `flow.drift.detected`
- `flow.expired`
- `flow.impact.computed`

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

- un flux déclaré contient source, destination, protocole, port, propriétaire et justification
- les flux observés massifs sont stockés en tables partitionnées et agrégés
- un export firewall volumineux est toujours asynchrone
- un flux temporaire expiré devient non conforme sans suppression de l’historique

## 10. Risques fonctionnels principaux

- Volume de flux observés très élevé
- Confusion entre matrice de flux et validation de changement ITSM

## 11. Exigences vérifiables du volume

| ID | Priorité | Type | Exigence | Vérification | Acceptation |
|---|---:|---|---|---|---|
| REQ-00339 | N1 | Fonctionnelle | OpenInfra doit fournir le module Flux réseau, matrices de flux et segmentation avec APIs, UI, audit, RBAC, imports/exports contrôlés et traçabilité complète. | Test fonctionnel bout-en-bout, revue API/UI et vérification audit. | Le module Flux réseau, matrices de flux et segmentation est utilisable par API et UI avec droits, audit et critères d’acceptation vérifiés. |
| REQ-00340 | N1 | Fonctionnelle | Le module Flux réseau, matrices de flux et segmentation doit être strictement séparé du périmètre ITSM et ne doit pas créer de ticket, incident, demande ou changement natif. | Revue fonctionnelle et tests négatifs sur les workflows. | Aucune capacité de ticketing natif n’est exposée dans ce module. |
| REQ-00341 | N1 | Données | Le modèle de données du module Flux réseau, matrices de flux et segmentation doit utiliser des entités typées, contraintes d’intégrité, propriétaires, tenant, statut, historique et audit. | Revue dictionnaire, tests migrations et tests contraintes. | Chaque entité critique possède clé stable, contraintes, audit et règles de rétention. |
| REQ-00342 | N1 | Performance | Les données volumineuses du module Flux réseau, matrices de flux et segmentation doivent être partitionnées, paginées, indexées et exploitées sans scan complet non maîtrisé. | Analyse DDL, tests EXPLAIN, benchmark API. | Les requêtes critiques utilisent les index attendus et les exports massifs sont asynchrones. |
| REQ-00343 | N1 | Sécurité | Le module Flux réseau, matrices de flux et segmentation doit appliquer RBAC/ABAC, isolation tenant, masquage des données sensibles et audit immuable des opérations critiques. | Tests RBAC/ABAC, tests audit et tests sécurité. | Un utilisateur sans droit ne peut ni lire ni modifier les ressources hors périmètre. |
| REQ-00344 | N1 | Résilience | Les traitements longs du module Flux réseau, matrices de flux et segmentation doivent être asynchrones, idempotents, relançables, annulables si possible et suivis par métriques. | Tests worker, crash recovery, dead-letter queue et reprise. | Un crash worker ne perd aucun job validé et l’état final reste cohérent. |
| REQ-00345 | N2 | Observabilité | Le module Flux réseau, matrices de flux et segmentation doit exposer métriques, logs structurés, traces et événements métier corrélables. | Test observabilité et contrôle dashboards. | Chaque opération critique produit log, métrique, trace et événement corrélés. |
| REQ-00346 | N1 | API | Les APIs du module Flux réseau, matrices de flux et segmentation doivent supporter pagination cursor-based, filtres sélectifs, tri indexé, OpenAPI et webhooks métier. | Tests API contractuels et tests de charge. | Les endpoints refusent les lectures volumineuses non filtrées et les contrats API sont validés. |
| REQ-00347 | N1 | Audit | Toute modification métier du module Flux réseau, matrices de flux et segmentation doit conserver ancien état, nouvel état, acteur, source, corrélation et preuve. | Tests audit et relecture historique. | Un changement peut être reconstitué avec preuve et horodatage. |
| REQ-00348 | N2 | Intégration | Le module Flux réseau, matrices de flux et segmentation doit publier des événements temps réel et consommer les données des autres domaines OpenInfra sans duplication incohérente. | Test event bus et test cohérence inter-domaines. | Les relations transverses sont référencées par identifiants stables et contrôles d’intégrité. |
| REQ-00349 | N1 | Fonctionnelle | Le module Flux réseau, matrices de flux et segmentation doit fournir au moins les capacités suivantes : modélisation source, destination, protocole, port, environnement, justification et durée de validité; comparaison flux déclarés et flux observés par NetFlow, sFlow, IPFIX, firewall logs et discovery applicative; détection des flux non autorisés, orphelins, expirés ou déclarés mais non observés; visualisation des flux par application, service, tenant, VRF, site et environnement. | Scénarios nominaux API/UI et tests fonctionnels. | Les quatre capacités prioritaires sont démontrées avec données représentatives. |
| REQ-00350 | N2 | Fonctionnelle | Le module Flux réseau, matrices de flux et segmentation doit fournir les capacités avancées suivantes : export contrôlé vers équipes firewall ou outils de sécurité externes; simulation d’impact avant modification firewall, segmentation ou migration; gestion des flux temporaires avec expiration et audit; corrélation flux ↔ dépendances applicatives ↔ IPAM ↔ certificats. | Tests fonctionnels et revue documentaire. | Les capacités avancées sont documentées, sécurisées et traçables. |
| REQ-00351 | N1 | Qualité | Les données du module Flux réseau, matrices de flux et segmentation doivent être vérifiées par règles qualité, exceptions justifiées et rapports de conformité. | Tests règles qualité et tests exceptions. | Les écarts sont détectés, priorisés, historisés et exportables. |
| REQ-00352 | N2 | Exploitation | Le module Flux réseau, matrices de flux et segmentation doit disposer de runbooks d’exploitation, sauvegarde, purge, restauration et support diagnostic. | Revue runbooks et test restauration ciblée. | Les procédures sont exécutables et reliées aux métriques de supervision. |
| REQ-00353 | N1 | Acceptation | Le module Flux réseau, matrices de flux et segmentation doit disposer de critères d’acceptation mesurables, de tests automatisés et d’une traçabilité exigence → cas d’usage → test. | Contrôle matrice de traçabilité. | Aucune exigence N1 du module n’est orpheline. |

## 12. Traçabilité

Toutes les exigences ci-dessus sont rattachées dans `11-Matrices/Traceabilite.csv` au cas d’usage `UC-0013` et aux tests `TST-REQ-*`. Les entités ajoutées sont présentes dans `04-Donnees/Dictionnaire.csv`.
