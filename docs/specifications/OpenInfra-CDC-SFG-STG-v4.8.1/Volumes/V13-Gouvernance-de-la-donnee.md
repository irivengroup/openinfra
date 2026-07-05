# Volume 13 — Gouvernance de la donnée et sources autoritatives

**Version :** 4.0.0  
**Statut :** obligatoire pour OpenInfra Enterprise  
**Domaine :** `GOV`  
**Nature :** spécification fonctionnelle et technique détaillée  
**Exclusion constante :** ce volume ne crée aucun module ITSM intégré.

## 1. Objectif

Garantir que la Source of Truth reste fiable, certifiée, gouvernée et exploitable contractuellement, même lorsque plusieurs sources automatiques produisent des informations divergentes.

Ce volume complète le socle SFG/STG v3 en ajoutant des capacités fonctionnelles de niveau enterprise. Il conserve les exigences transversales OpenInfra : PostgreSQL Cluster, partitionnement des tables massives, API-first, sécurité Zero Trust, audit immuable, haute disponibilité, concurrence contrôlée, traitements asynchrones et traçabilité exigence → cas d’usage → test.

## 2. Périmètre fonctionnel obligatoire

| Capacité obligatoire |
|---|
| définition des propriétaires fonctionnels et techniques par domaine de données |
| déclaration des sources autoritatives par objet, attribut, tenant, site et environnement |
| priorisation des sources avec score de confiance, score de fraîcheur et score de complétude |
| certification périodique des données critiques |
| gel contrôlé des objets critiques pendant opérations sensibles |
| règles de fusion, déduplication et résolution de conflit |
| journalisation des décisions de gouvernance et des exceptions |
| tableaux de bord de gouvernance par domaine, site, tenant et criticité |

## 3. Cas d’usage représentatifs

- Définir la source autoritative du numéro de série serveur comme découverte matérielle, tout en gardant la localisation comme donnée certifiée manuellement.
- Lancer une campagne de certification trimestrielle des équipements de production sans créer de ticket ITSM.
- Bloquer une modification automatique sur une application critique lorsque la source découverte contredit la donnée certifiée.

## 4. Modèle de données logique

Les entités suivantes sont ajoutées au dictionnaire de données v4. Elles doivent être modélisées avec identifiant stable, tenant, statut, propriétaire, horodatage, audit, règles de rétention et contraintes d’intégrité adaptées.

- `data_domain`
- `authoritative_source`
- `attribute_authority_rule`
- `data_owner`
- `technical_steward`
- `trust_score`
- `freshness_policy`
- `certification_campaign`
- `certification_decision`
- `governance_exception`
- `conflict_resolution_rule`
- `data_freeze`
- `stewardship_assignment`
- `source_priority_matrix`
- `data_lineage_record`

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

- `/data-domains`
- `/authoritative-sources`
- `/source-priority-rules`
- `/certification-campaigns`
- `/data-freezes`
- `/governance-exceptions`

### Événements métier

- `data.governance.rule.changed`
- `data.certification.completed`
- `data.conflict.resolved`
- `data.freeze.enabled`

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

- un attribut critique ne peut pas être déclaré sans règle de source autoritative
- toute résolution de conflit est historisée avec acteur, preuve et justification
- les campagnes de certification produisent un rapport exploitable par API et export
- les scores de confiance et de fraîcheur sont calculés de manière déterministe

## 10. Risques fonctionnels principaux

- Règles de priorité mal définies entraînant une perte de confiance dans le référentiel
- Excès de validation manuelle ralentissant les opérations automatisées

## 11. Exigences vérifiables du volume

| ID | Priorité | Type | Exigence | Vérification | Acceptation |
|---|---:|---|---|---|---|
| REQ-00309 | N1 | Fonctionnelle | OpenInfra doit fournir le module Gouvernance de la donnée et sources autoritatives avec APIs, UI, audit, RBAC, imports/exports contrôlés et traçabilité complète. | Test fonctionnel bout-en-bout, revue API/UI et vérification audit. | Le module Gouvernance de la donnée et sources autoritatives est utilisable par API et UI avec droits, audit et critères d’acceptation vérifiés. |
| REQ-00310 | N1 | Fonctionnelle | Le module Gouvernance de la donnée et sources autoritatives doit être strictement séparé du périmètre ITSM et ne doit pas créer de ticket, incident, demande ou changement natif. | Revue fonctionnelle et tests négatifs sur les workflows. | Aucune capacité de ticketing natif n’est exposée dans ce module. |
| REQ-00311 | N1 | Données | Le modèle de données du module Gouvernance de la donnée et sources autoritatives doit utiliser des entités typées, contraintes d’intégrité, propriétaires, tenant, statut, historique et audit. | Revue dictionnaire, tests migrations et tests contraintes. | Chaque entité critique possède clé stable, contraintes, audit et règles de rétention. |
| REQ-00312 | N1 | Performance | Les données volumineuses du module Gouvernance de la donnée et sources autoritatives doivent être partitionnées, paginées, indexées et exploitées sans scan complet non maîtrisé. | Analyse DDL, tests EXPLAIN, benchmark API. | Les requêtes critiques utilisent les index attendus et les exports massifs sont asynchrones. |
| REQ-00313 | N1 | Sécurité | Le module Gouvernance de la donnée et sources autoritatives doit appliquer RBAC/ABAC, isolation tenant, masquage des données sensibles et audit immuable des opérations critiques. | Tests RBAC/ABAC, tests audit et tests sécurité. | Un utilisateur sans droit ne peut ni lire ni modifier les ressources hors périmètre. |
| REQ-00314 | N1 | Résilience | Les traitements longs du module Gouvernance de la donnée et sources autoritatives doivent être asynchrones, idempotents, relançables, annulables si possible et suivis par métriques. | Tests worker, crash recovery, dead-letter queue et reprise. | Un crash worker ne perd aucun job validé et l’état final reste cohérent. |
| REQ-00315 | N2 | Observabilité | Le module Gouvernance de la donnée et sources autoritatives doit exposer métriques, logs structurés, traces et événements métier corrélables. | Test observabilité et contrôle dashboards. | Chaque opération critique produit log, métrique, trace et événement corrélés. |
| REQ-00316 | N1 | API | Les APIs du module Gouvernance de la donnée et sources autoritatives doivent supporter pagination cursor-based, filtres sélectifs, tri indexé, OpenAPI et webhooks métier. | Tests API contractuels et tests de charge. | Les endpoints refusent les lectures volumineuses non filtrées et les contrats API sont validés. |
| REQ-00317 | N1 | Audit | Toute modification métier du module Gouvernance de la donnée et sources autoritatives doit conserver ancien état, nouvel état, acteur, source, corrélation et preuve. | Tests audit et relecture historique. | Un changement peut être reconstitué avec preuve et horodatage. |
| REQ-00318 | N2 | Intégration | Le module Gouvernance de la donnée et sources autoritatives doit publier des événements temps réel et consommer les données des autres domaines OpenInfra sans duplication incohérente. | Test event bus et test cohérence inter-domaines. | Les relations transverses sont référencées par identifiants stables et contrôles d’intégrité. |
| REQ-00319 | N1 | Fonctionnelle | Le module Gouvernance de la donnée et sources autoritatives doit fournir au moins les capacités suivantes : définition des propriétaires fonctionnels et techniques par domaine de données; déclaration des sources autoritatives par objet, attribut, tenant, site et environnement; priorisation des sources avec score de confiance, score de fraîcheur et score de complétude; certification périodique des données critiques. | Scénarios nominaux API/UI et tests fonctionnels. | Les quatre capacités prioritaires sont démontrées avec données représentatives. |
| REQ-00320 | N2 | Fonctionnelle | Le module Gouvernance de la donnée et sources autoritatives doit fournir les capacités avancées suivantes : gel contrôlé des objets critiques pendant opérations sensibles; règles de fusion, déduplication et résolution de conflit; journalisation des décisions de gouvernance et des exceptions; tableaux de bord de gouvernance par domaine, site, tenant et criticité. | Tests fonctionnels et revue documentaire. | Les capacités avancées sont documentées, sécurisées et traçables. |
| REQ-00321 | N1 | Qualité | Les données du module Gouvernance de la donnée et sources autoritatives doivent être vérifiées par règles qualité, exceptions justifiées et rapports de conformité. | Tests règles qualité et tests exceptions. | Les écarts sont détectés, priorisés, historisés et exportables. |
| REQ-00322 | N2 | Exploitation | Le module Gouvernance de la donnée et sources autoritatives doit disposer de runbooks d’exploitation, sauvegarde, purge, restauration et support diagnostic. | Revue runbooks et test restauration ciblée. | Les procédures sont exécutables et reliées aux métriques de supervision. |
| REQ-00323 | N1 | Acceptation | Le module Gouvernance de la donnée et sources autoritatives doit disposer de critères d’acceptation mesurables, de tests automatisés et d’une traçabilité exigence → cas d’usage → test. | Contrôle matrice de traçabilité. | Aucune exigence N1 du module n’est orpheline. |

## 12. Traçabilité

Toutes les exigences ci-dessus sont rattachées dans `11-Matrices/Traceabilite.csv` au cas d’usage `UC-0011` et aux tests `TST-REQ-*`. Les entités ajoutées sont présentes dans `04-Donnees/Dictionnaire.csv`.
