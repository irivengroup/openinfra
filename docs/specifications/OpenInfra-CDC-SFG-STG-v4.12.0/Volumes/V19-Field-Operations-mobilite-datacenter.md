# Volume 19 — Field Operations et mobilité datacenter

**Version :** 4.0.0  
**Statut :** obligatoire pour OpenInfra Enterprise  
**Domaine :** `FIELD`  
**Nature :** spécification fonctionnelle et technique détaillée  
**Exclusion constante :** ce volume ne crée aucun module ITSM intégré.

## 1. Objectif

Réduire les erreurs terrain par des fiches d’intervention, QR codes, mode mobile/offline et validations de localisation sans introduire un module ITSM.

Ce volume complète le socle SFG/STG v3 en ajoutant des capacités fonctionnelles de niveau enterprise. Il conserve les exigences transversales OpenInfra : PostgreSQL Cluster, partitionnement des tables massives, API-first, sécurité Zero Trust, audit immuable, haute disponibilité, concurrence contrôlée, traitements asynchrones et traçabilité exigence → cas d’usage → test.

## 2. Périmètre fonctionnel obligatoire

| Capacité obligatoire |
|---|
| génération de fiche d’intervention depuis équipement, rack, câble, PDU ou certificat |
| affichage chemin physique complet avec site, bâtiment, salle, ligne, colonne, X/Y/Z, rack, face et U |
| QR code et code-barres pour actif, rack, PDU, câble et emplacement |
| mode mobile avec consultation offline contrôlée |
| checklists de manipulation et validations avant/après |
| photos avant/après et preuves rattachées à l’actif |
| verrou logique d’intervention hors ITSM pour éviter manipulations concurrentes |
| avertissement sur dépendances critiques, flux, alimentation et SPOF avant intervention |

## 3. Cas d’usage représentatifs

- Générer une fiche de remplacement serveur avec localisation complète et dépendances critiques.
- Scanner un QR code de rack et vérifier que le bon équipement est manipulé.
- Effectuer une intervention en salle sans connectivité puis synchroniser les preuves.

## 4. Modèle de données logique

Les entités suivantes sont ajoutées au dictionnaire de données v4. Elles doivent être modélisées avec identifiant stable, tenant, statut, propriétaire, horodatage, audit, règles de rétention et contraintes d’intégrité adaptées.

- `field_operation_sheet`
- `physical_qr_code`
- `barcode_assignment`
- `offline_sync_package`
- `field_checklist`
- `field_evidence`
- `intervention_lock`
- `physical_verification_step`
- `before_after_photo`
- `field_operator_profile`
- `mobile_sync_event`
- `rack_visit`
- `cable_trace_task`
- `operation_safety_warning`
- `field_operation_audit`

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

- `/field-operation-sheets`
- `/qr-codes`
- `/field-checklists`
- `/field-evidence`
- `/intervention-locks`
- `/offline-sync-packages`

### Événements métier

- `field.sheet.generated`
- `field.evidence.attached`
- `field.operation.locked`
- `field.offline.sync.completed`

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

- une fiche terrain ne peut pas être générée si la localisation obligatoire est incomplète
- le mode offline ne stocke que le périmètre autorisé et expire automatiquement
- les preuves d’intervention sont immuables après validation
- le verrou d’intervention ne bloque pas la lecture ni la découverte automatique

## 10. Risques fonctionnels principaux

- Confusion avec ticketing ITSM
- Perte ou exposition de données dans un paquet offline

## 11. Exigences vérifiables du volume

| ID | Priorité | Type | Exigence | Vérification | Acceptation |
|---|---:|---|---|---|---|
| REQ-00399 | N1 | Fonctionnelle | OpenInfra doit fournir le module Field Operations et mobilité datacenter avec APIs, UI, audit, RBAC, imports/exports contrôlés et traçabilité complète. | Test fonctionnel bout-en-bout, revue API/UI et vérification audit. | Le module Field Operations et mobilité datacenter est utilisable par API et UI avec droits, audit et critères d’acceptation vérifiés. |
| REQ-00400 | N1 | Fonctionnelle | Le module Field Operations et mobilité datacenter doit être strictement séparé du périmètre ITSM et ne doit pas créer de ticket, incident, demande ou changement natif. | Revue fonctionnelle et tests négatifs sur les workflows. | Aucune capacité de ticketing natif n’est exposée dans ce module. |
| REQ-00401 | N1 | Données | Le modèle de données du module Field Operations et mobilité datacenter doit utiliser des entités typées, contraintes d’intégrité, propriétaires, tenant, statut, historique et audit. | Revue dictionnaire, tests migrations et tests contraintes. | Chaque entité critique possède clé stable, contraintes, audit et règles de rétention. |
| REQ-00402 | N1 | Performance | Les données volumineuses du module Field Operations et mobilité datacenter doivent être partitionnées, paginées, indexées et exploitées sans scan complet non maîtrisé. | Analyse DDL, tests EXPLAIN, benchmark API. | Les requêtes critiques utilisent les index attendus et les exports massifs sont asynchrones. |
| REQ-00403 | N1 | Sécurité | Le module Field Operations et mobilité datacenter doit appliquer RBAC/ABAC, isolation tenant, masquage des données sensibles et audit immuable des opérations critiques. | Tests RBAC/ABAC, tests audit et tests sécurité. | Un utilisateur sans droit ne peut ni lire ni modifier les ressources hors périmètre. |
| REQ-00404 | N1 | Résilience | Les traitements longs du module Field Operations et mobilité datacenter doivent être asynchrones, idempotents, relançables, annulables si possible et suivis par métriques. | Tests worker, crash recovery, dead-letter queue et reprise. | Un crash worker ne perd aucun job validé et l’état final reste cohérent. |
| REQ-00405 | N2 | Observabilité | Le module Field Operations et mobilité datacenter doit exposer métriques, logs structurés, traces et événements métier corrélables. | Test observabilité et contrôle dashboards. | Chaque opération critique produit log, métrique, trace et événement corrélés. |
| REQ-00406 | N1 | API | Les APIs du module Field Operations et mobilité datacenter doivent supporter pagination cursor-based, filtres sélectifs, tri indexé, OpenAPI et webhooks métier. | Tests API contractuels et tests de charge. | Les endpoints refusent les lectures volumineuses non filtrées et les contrats API sont validés. |
| REQ-00407 | N1 | Audit | Toute modification métier du module Field Operations et mobilité datacenter doit conserver ancien état, nouvel état, acteur, source, corrélation et preuve. | Tests audit et relecture historique. | Un changement peut être reconstitué avec preuve et horodatage. |
| REQ-00408 | N2 | Intégration | Le module Field Operations et mobilité datacenter doit publier des événements temps réel et consommer les données des autres domaines OpenInfra sans duplication incohérente. | Test event bus et test cohérence inter-domaines. | Les relations transverses sont référencées par identifiants stables et contrôles d’intégrité. |
| REQ-00409 | N1 | Fonctionnelle | Le module Field Operations et mobilité datacenter doit fournir au moins les capacités suivantes : génération de fiche d’intervention depuis équipement, rack, câble, PDU ou certificat; affichage chemin physique complet avec site, bâtiment, salle, ligne, colonne, X/Y/Z, rack, face et U; QR code et code-barres pour actif, rack, PDU, câble et emplacement; mode mobile avec consultation offline contrôlée. | Scénarios nominaux API/UI et tests fonctionnels. | Les quatre capacités prioritaires sont démontrées avec données représentatives. |
| REQ-00410 | N2 | Fonctionnelle | Le module Field Operations et mobilité datacenter doit fournir les capacités avancées suivantes : checklists de manipulation et validations avant/après; photos avant/après et preuves rattachées à l’actif; verrou logique d’intervention hors ITSM pour éviter manipulations concurrentes; avertissement sur dépendances critiques, flux, alimentation et SPOF avant intervention. | Tests fonctionnels et revue documentaire. | Les capacités avancées sont documentées, sécurisées et traçables. |
| REQ-00411 | N1 | Qualité | Les données du module Field Operations et mobilité datacenter doivent être vérifiées par règles qualité, exceptions justifiées et rapports de conformité. | Tests règles qualité et tests exceptions. | Les écarts sont détectés, priorisés, historisés et exportables. |
| REQ-00412 | N2 | Exploitation | Le module Field Operations et mobilité datacenter doit disposer de runbooks d’exploitation, sauvegarde, purge, restauration et support diagnostic. | Revue runbooks et test restauration ciblée. | Les procédures sont exécutables et reliées aux métriques de supervision. |
| REQ-00413 | N1 | Acceptation | Le module Field Operations et mobilité datacenter doit disposer de critères d’acceptation mesurables, de tests automatisés et d’une traçabilité exigence → cas d’usage → test. | Contrôle matrice de traçabilité. | Aucune exigence N1 du module n’est orpheline. |

## 12. Traçabilité

Toutes les exigences ci-dessus sont rattachées dans `11-Matrices/Traceabilite.csv` au cas d’usage `UC-0017` et aux tests `TST-REQ-*`. Les entités ajoutées sont présentes dans `04-Donnees/Dictionnaire.csv`.
