# Volume 17 — Conformité réseau et configuration attendue

**Version :** 4.0.0  
**Statut :** obligatoire pour OpenInfra Enterprise  
**Domaine :** `NCFG`  
**Nature :** spécification fonctionnelle et technique détaillée  
**Exclusion constante :** ce volume ne crée aucun module ITSM intégré.

## 1. Objectif

Comparer les configurations réseau découvertes avec des configurations attendues versionnées afin de détecter les dérives sans appliquer automatiquement de changement non validé.

Ce volume complète le socle SFG/STG v3 en ajoutant des capacités fonctionnelles de niveau entreprise. Il conserve les exigences transversales OpenInfra : PostgreSQL Cluster, partitionnement des tables massives, API-first, sécurité Zero Trust, audit immuable, haute disponibilité, concurrence contrôlée, traitements asynchrones et traçabilité exigence → cas d’usage → test.

## 2. Périmètre fonctionnel obligatoire

| Capacité obligatoire |
|---|
| définition de golden configurations par constructeur, modèle, rôle, site et environnement |
| contrôle conformité AAA, NTP, SNMP, syslog, TACACS/RADIUS, BGP, OSPF, VRF, VLAN et ACL |
| parsing sécurisé des configurations collectées |
| détection de drift par règle, section et criticité |
| historique des configurations découvertes avec chiffrement si nécessaire |
| rapports de conformité par équipement, site et domaine réseau |
| suggestions de remédiation non exécutées automatiquement |
| intégration avec matrice de flux et policy engine |

## 3. Cas d’usage représentatifs

- Vérifier que tous les switches de production utilisent les serveurs NTP et syslog approuvés.
- Détecter une différence de configuration BGP sur deux routeurs censés être symétriques.
- Produire un rapport de dérive par site avant un audit sécurité.

## 4. Modèle de données logique

Les entités suivantes sont ajoutées au dictionnaire de données v4. Elles doivent être modélisées avec identifiant stable, tenant, statut, propriétaire, horodatage, audit, règles de rétention et contraintes d’intégrité adaptées.

- `network_config_snapshot`
- `golden_config_template`
- `config_compliance_rule`
- `config_drift`
- `config_section`
- `remediation_suggestion`
- `network_os_profile`
- `parser_profile`
- `config_collection_job`
- `aaa_compliance_check`
- `routing_compliance_check`
- `firewall_compliance_check`
- `interface_compliance_check`
- `config_evidence`
- `config_exception`

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

- `/golden-configs`
- `/config-snapshots`
- `/config-compliance-rules`
- `/config-drifts`
- `/remediation-suggestions`

### Événements métier

- `network.config.collected`
- `network.config.drift.detected`
- `network.config.compliance.changed`

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

- une dérive identifie règle, équipement, section, preuve et criticité
- les configurations sensibles sont protégées contre exposition de secrets
- les remédiations proposées sont séparées de toute exécution automatique
- les règles de conformité sont versionnées et auditables

## 10. Risques fonctionnels principaux

- Parsing incomplet selon constructeurs
- Risque de confusion avec orchestration de changement réseau

## 11. Exigences vérifiables du volume

| ID | Priorité | Type | Exigence | Vérification | Acceptation |
|---|---:|---|---|---|---|
| REQ-00369 | N1 | Fonctionnelle | OpenInfra doit fournir le module Conformité réseau et configuration attendue avec APIs, UI, audit, RBAC, imports/exports contrôlés et traçabilité complète. | Test fonctionnel bout-en-bout, revue API/UI et vérification audit. | Le module Conformité réseau et configuration attendue est utilisable par API et UI avec droits, audit et critères d’acceptation vérifiés. |
| REQ-00370 | N1 | Fonctionnelle | Le module Conformité réseau et configuration attendue doit être strictement séparé du périmètre ITSM et ne doit pas créer de ticket, incident, demande ou changement natif. | Revue fonctionnelle et tests négatifs sur les workflows. | Aucune capacité de ticketing natif n’est exposée dans ce module. |
| REQ-00371 | N1 | Données | Le modèle de données du module Conformité réseau et configuration attendue doit utiliser des entités typées, contraintes d’intégrité, propriétaires, tenant, statut, historique et audit. | Revue dictionnaire, tests migrations et tests contraintes. | Chaque entité critique possède clé stable, contraintes, audit et règles de rétention. |
| REQ-00372 | N1 | Performance | Les données volumineuses du module Conformité réseau et configuration attendue doivent être partitionnées, paginées, indexées et exploitées sans scan complet non maîtrisé. | Analyse DDL, tests EXPLAIN, benchmark API. | Les requêtes critiques utilisent les index attendus et les exports massifs sont asynchrones. |
| REQ-00373 | N1 | Sécurité | Le module Conformité réseau et configuration attendue doit appliquer RBAC/ABAC, isolation tenant, masquage des données sensibles et audit immuable des opérations critiques. | Tests RBAC/ABAC, tests audit et tests sécurité. | Un utilisateur sans droit ne peut ni lire ni modifier les ressources hors périmètre. |
| REQ-00374 | N1 | Résilience | Les traitements longs du module Conformité réseau et configuration attendue doivent être asynchrones, idempotents, relançables, annulables si possible et suivis par métriques. | Tests worker, crash recovery, dead-letter queue et reprise. | Un crash worker ne perd aucun job validé et l’état final reste cohérent. |
| REQ-00375 | N2 | Observabilité | Le module Conformité réseau et configuration attendue doit exposer métriques, logs structurés, traces et événements métier corrélables. | Test observabilité et contrôle dashboards. | Chaque opération critique produit log, métrique, trace et événement corrélés. |
| REQ-00376 | N1 | API | Les APIs du module Conformité réseau et configuration attendue doivent supporter pagination cursor-based, filtres sélectifs, tri indexé, OpenAPI et webhooks métier. | Tests API contractuels et tests de charge. | Les endpoints refusent les lectures volumineuses non filtrées et les contrats API sont validés. |
| REQ-00377 | N1 | Audit | Toute modification métier du module Conformité réseau et configuration attendue doit conserver ancien état, nouvel état, acteur, source, corrélation et preuve. | Tests audit et relecture historique. | Un changement peut être reconstitué avec preuve et horodatage. |
| REQ-00378 | N2 | Intégration | Le module Conformité réseau et configuration attendue doit publier des événements temps réel et consommer les données des autres domaines OpenInfra sans duplication incohérente. | Test event bus et test cohérence inter-domaines. | Les relations transverses sont référencées par identifiants stables et contrôles d’intégrité. |
| REQ-00379 | N1 | Fonctionnelle | Le module Conformité réseau et configuration attendue doit fournir au moins les capacités suivantes : définition de golden configurations par constructeur, modèle, rôle, site et environnement; contrôle conformité AAA, NTP, SNMP, syslog, TACACS/RADIUS, BGP, OSPF, VRF, VLAN et ACL; parsing sécurisé des configurations collectées; détection de drift par règle, section et criticité. | Scénarios nominaux API/UI et tests fonctionnels. | Les quatre capacités prioritaires sont démontrées avec données représentatives. |
| REQ-00380 | N2 | Fonctionnelle | Le module Conformité réseau et configuration attendue doit fournir les capacités avancées suivantes : historique des configurations découvertes avec chiffrement si nécessaire; rapports de conformité par équipement, site et domaine réseau; suggestions de remédiation non exécutées automatiquement; intégration avec matrice de flux et policy engine. | Tests fonctionnels et revue documentaire. | Les capacités avancées sont documentées, sécurisées et traçables. |
| REQ-00381 | N1 | Qualité | Les données du module Conformité réseau et configuration attendue doivent être vérifiées par règles qualité, exceptions justifiées et rapports de conformité. | Tests règles qualité et tests exceptions. | Les écarts sont détectés, priorisés, historisés et exportables. |
| REQ-00382 | N2 | Exploitation | Le module Conformité réseau et configuration attendue doit disposer de runbooks d’exploitation, sauvegarde, purge, restauration et support diagnostic. | Revue runbooks et test restauration ciblée. | Les procédures sont exécutables et reliées aux métriques de supervision. |
| REQ-00383 | N1 | Acceptation | Le module Conformité réseau et configuration attendue doit disposer de critères d’acceptation mesurables, de tests automatisés et d’une traçabilité exigence → cas d’usage → test. | Contrôle matrice de traçabilité. | Aucune exigence N1 du module n’est orpheline. |

## 12. Traçabilité

Toutes les exigences ci-dessus sont rattachées dans `11-Matrices/Traceabilite.csv` au cas d’usage `UC-0015` et aux tests `TST-REQ-*`. Les entités ajoutées sont présentes dans `04-Donnees/Dictionnaire.csv`.
