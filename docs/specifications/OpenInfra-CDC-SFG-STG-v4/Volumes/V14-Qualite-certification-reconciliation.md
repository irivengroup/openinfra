# Volume 14 — Qualité, certification et réconciliation des données

**Version :** 4.0.0  
**Statut :** obligatoire pour OpenInfra Enterprise  
**Domaine :** `DQ`  
**Nature :** spécification fonctionnelle et technique détaillée  
**Exclusion constante :** ce volume ne crée aucun module ITSM intégré.

## 1. Objectif

Détecter, qualifier, prioriser et corriger les incohérences du référentiel sans écrasement silencieux, avec preuves et réconciliation maîtrisée.

Ce volume complète le socle SFG/STG v3 en ajoutant des capacités fonctionnelles de niveau entreprise. Il conserve les exigences transversales OpenInfra : PostgreSQL Cluster, partitionnement des tables massives, API-first, sécurité Zero Trust, audit immuable, haute disponibilité, concurrence contrôlée, traitements asynchrones et traçabilité exigence → cas d’usage → test.

## 2. Périmètre fonctionnel obligatoire

| Capacité obligatoire |
|---|
| détection des doublons, orphelins, valeurs manquantes et incohérences inter-domaines |
| moteur de règles de qualité configurable par domaine et criticité |
| score qualité global et score qualité par objet |
| réconciliation multi-sources avec seuils de confiance |
| gestion des exceptions justifiées avec expiration |
| rapports de qualité par tenant, site, application et propriétaire |
| correction en lot avec prévisualisation et rollback |
| historique time travel des campagnes qualité |

## 3. Cas d’usage représentatifs

- Identifier tous les équipements sans ligne/colonne ou sans propriétaire et produire un rapport priorisé.
- Détecter deux serveurs découverts avec le même numéro de série mais des noms différents.
- Réconcilier une IP déclarée dans l’IPAM avec une IP observée active mais non attribuée.

## 4. Modèle de données logique

Les entités suivantes sont ajoutées au dictionnaire de données v4. Elles doivent être modélisées avec identifiant stable, tenant, statut, propriétaire, horodatage, audit, règles de rétention et contraintes d’intégrité adaptées.

- `quality_rule`
- `quality_finding`
- `duplicate_candidate`
- `orphan_object`
- `missing_attribute_finding`
- `reconciliation_job`
- `reconciliation_candidate`
- `reconciliation_decision`
- `quality_score`
- `quality_exception`
- `data_quality_campaign`
- `correction_batch`
- `quality_dashboard_snapshot`
- `finding_evidence`
- `quality_sla_policy`

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

- `/quality-rules`
- `/quality-findings`
- `/reconciliation-jobs`
- `/duplicate-candidates`
- `/quality-scores`
- `/quality-exceptions`

### Événements métier

- `data.quality.finding.created`
- `data.reconciliation.completed`
- `data.quality.score.changed`

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

- chaque finding possède une preuve, une criticité, une règle source et un statut
- la correction de masse exige un dry-run et un rapport avant application
- une exception qualité a une justification, une portée et une date d’expiration
- les écarts IPAM/DNS/DHCP sont visibles dans un tableau de bord dédié

## 10. Risques fonctionnels principaux

- Accumulation de findings non traités
- Règles qualité trop agressives générant de faux positifs

## 11. Exigences vérifiables du volume

| ID | Priorité | Type | Exigence | Vérification | Acceptation |
|---|---:|---|---|---|---|
| REQ-00324 | N1 | Fonctionnelle | OpenInfra doit fournir le module Qualité, certification et réconciliation des données avec APIs, UI, audit, RBAC, imports/exports contrôlés et traçabilité complète. | Test fonctionnel bout-en-bout, revue API/UI et vérification audit. | Le module Qualité, certification et réconciliation des données est utilisable par API et UI avec droits, audit et critères d’acceptation vérifiés. |
| REQ-00325 | N1 | Fonctionnelle | Le module Qualité, certification et réconciliation des données doit être strictement séparé du périmètre ITSM et ne doit pas créer de ticket, incident, demande ou changement natif. | Revue fonctionnelle et tests négatifs sur les workflows. | Aucune capacité de ticketing natif n’est exposée dans ce module. |
| REQ-00326 | N1 | Données | Le modèle de données du module Qualité, certification et réconciliation des données doit utiliser des entités typées, contraintes d’intégrité, propriétaires, tenant, statut, historique et audit. | Revue dictionnaire, tests migrations et tests contraintes. | Chaque entité critique possède clé stable, contraintes, audit et règles de rétention. |
| REQ-00327 | N1 | Performance | Les données volumineuses du module Qualité, certification et réconciliation des données doivent être partitionnées, paginées, indexées et exploitées sans scan complet non maîtrisé. | Analyse DDL, tests EXPLAIN, benchmark API. | Les requêtes critiques utilisent les index attendus et les exports massifs sont asynchrones. |
| REQ-00328 | N1 | Sécurité | Le module Qualité, certification et réconciliation des données doit appliquer RBAC/ABAC, isolation tenant, masquage des données sensibles et audit immuable des opérations critiques. | Tests RBAC/ABAC, tests audit et tests sécurité. | Un utilisateur sans droit ne peut ni lire ni modifier les ressources hors périmètre. |
| REQ-00329 | N1 | Résilience | Les traitements longs du module Qualité, certification et réconciliation des données doivent être asynchrones, idempotents, relançables, annulables si possible et suivis par métriques. | Tests worker, crash recovery, dead-letter queue et reprise. | Un crash worker ne perd aucun job validé et l’état final reste cohérent. |
| REQ-00330 | N2 | Observabilité | Le module Qualité, certification et réconciliation des données doit exposer métriques, logs structurés, traces et événements métier corrélables. | Test observabilité et contrôle dashboards. | Chaque opération critique produit log, métrique, trace et événement corrélés. |
| REQ-00331 | N1 | API | Les APIs du module Qualité, certification et réconciliation des données doivent supporter pagination cursor-based, filtres sélectifs, tri indexé, OpenAPI et webhooks métier. | Tests API contractuels et tests de charge. | Les endpoints refusent les lectures volumineuses non filtrées et les contrats API sont validés. |
| REQ-00332 | N1 | Audit | Toute modification métier du module Qualité, certification et réconciliation des données doit conserver ancien état, nouvel état, acteur, source, corrélation et preuve. | Tests audit et relecture historique. | Un changement peut être reconstitué avec preuve et horodatage. |
| REQ-00333 | N2 | Intégration | Le module Qualité, certification et réconciliation des données doit publier des événements temps réel et consommer les données des autres domaines OpenInfra sans duplication incohérente. | Test event bus et test cohérence inter-domaines. | Les relations transverses sont référencées par identifiants stables et contrôles d’intégrité. |
| REQ-00334 | N1 | Fonctionnelle | Le module Qualité, certification et réconciliation des données doit fournir au moins les capacités suivantes : détection des doublons, orphelins, valeurs manquantes et incohérences inter-domaines; moteur de règles de qualité configurable par domaine et criticité; score qualité global et score qualité par objet; réconciliation multi-sources avec seuils de confiance. | Scénarios nominaux API/UI et tests fonctionnels. | Les quatre capacités prioritaires sont démontrées avec données représentatives. |
| REQ-00335 | N2 | Fonctionnelle | Le module Qualité, certification et réconciliation des données doit fournir les capacités avancées suivantes : gestion des exceptions justifiées avec expiration; rapports de qualité par tenant, site, application et propriétaire; correction en lot avec prévisualisation et rollback; historique time travel des campagnes qualité. | Tests fonctionnels et revue documentaire. | Les capacités avancées sont documentées, sécurisées et traçables. |
| REQ-00336 | N1 | Qualité | Les données du module Qualité, certification et réconciliation des données doivent être vérifiées par règles qualité, exceptions justifiées et rapports de conformité. | Tests règles qualité et tests exceptions. | Les écarts sont détectés, priorisés, historisés et exportables. |
| REQ-00337 | N2 | Exploitation | Le module Qualité, certification et réconciliation des données doit disposer de runbooks d’exploitation, sauvegarde, purge, restauration et support diagnostic. | Revue runbooks et test restauration ciblée. | Les procédures sont exécutables et reliées aux métriques de supervision. |
| REQ-00338 | N1 | Acceptation | Le module Qualité, certification et réconciliation des données doit disposer de critères d’acceptation mesurables, de tests automatisés et d’une traçabilité exigence → cas d’usage → test. | Contrôle matrice de traçabilité. | Aucune exigence N1 du module n’est orpheline. |

## 12. Traçabilité

Toutes les exigences ci-dessus sont rattachées dans `11-Matrices/Traceabilite.csv` au cas d’usage `UC-0012` et aux tests `TST-REQ-*`. Les entités ajoutées sont présentes dans `04-Donnees/Dictionnaire.csv`.
