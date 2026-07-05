---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# V11 — Administration

## Positionnement

Le volume **V11 — Administration** décrit les spécifications applicables au domaine associé. Il est normatif pour la conception, le développement, les tests et la réception.

## Sections couvertes

| Section |
| --- |
| Déploiement |
| Kubernetes |
| Docker |
| Sauvegarde |
| PRA/PCA |
| Observabilité |

## Principes transverses

- API-first : toute capacité métier importante doit être exposée par API versionnée.
- Sécurité by design : RBAC, ABAC, audit, chiffrement et séparation tenant doivent être natifs.
- Observabilité by design : métriques, logs structurés, traces et événements doivent être corrélables.
- Performance by design : pagination, indexation, partitionnement et bornage des traitements sont obligatoires.
- Résilience by design : reprise, retry, dead-letter queue et idempotence doivent être prévus.
- Exploitabilité : chaque capacité doit être supervisable, sauvegardable et documentée.


## Déploiement

### Finalité

Le volet **Déploiement** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la Source of Truth.

### Règles de conception

- Les données critiques sont validées par contraintes métier et contraintes de base de données.
- Les opérations longues sont asynchrones, découpées en lots et relançables.
- Les lectures volumineuses utilisent la pagination cursor-based et des filtres sélectifs.
- Les écritures critiques sont transactionnelles, idempotentes et auditées.
- Les intégrations externes ne peuvent pas écraser silencieusement une donnée de référence.
- Les écarts entre découverte, import et vérité déclarative produisent un conflit explicite.
- Les données sensibles sont masquées selon les droits et jamais exposées dans les journaux.
- Les APIs publiques sont versionnées, documentées et soumises à rate limiting.

### Cas d’acceptation type

La capacité est acceptée si un administrateur habilité peut créer, consulter, modifier, historiser, exporter et auditer l’objet métier correspondant, et si un utilisateur non habilité ne peut ni le consulter ni le modifier hors périmètre.

## Kubernetes

### Finalité

Le volet **Kubernetes** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la Source of Truth.

### Règles de conception

- Les données critiques sont validées par contraintes métier et contraintes de base de données.
- Les opérations longues sont asynchrones, découpées en lots et relançables.
- Les lectures volumineuses utilisent la pagination cursor-based et des filtres sélectifs.
- Les écritures critiques sont transactionnelles, idempotentes et auditées.
- Les intégrations externes ne peuvent pas écraser silencieusement une donnée de référence.
- Les écarts entre découverte, import et vérité déclarative produisent un conflit explicite.
- Les données sensibles sont masquées selon les droits et jamais exposées dans les journaux.
- Les APIs publiques sont versionnées, documentées et soumises à rate limiting.

### Cas d’acceptation type

La capacité est acceptée si un administrateur habilité peut créer, consulter, modifier, historiser, exporter et auditer l’objet métier correspondant, et si un utilisateur non habilité ne peut ni le consulter ni le modifier hors périmètre.

## Docker

### Finalité

Le volet **Docker** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la Source of Truth.

### Règles de conception

- Les données critiques sont validées par contraintes métier et contraintes de base de données.
- Les opérations longues sont asynchrones, découpées en lots et relançables.
- Les lectures volumineuses utilisent la pagination cursor-based et des filtres sélectifs.
- Les écritures critiques sont transactionnelles, idempotentes et auditées.
- Les intégrations externes ne peuvent pas écraser silencieusement une donnée de référence.
- Les écarts entre découverte, import et vérité déclarative produisent un conflit explicite.
- Les données sensibles sont masquées selon les droits et jamais exposées dans les journaux.
- Les APIs publiques sont versionnées, documentées et soumises à rate limiting.

### Cas d’acceptation type

La capacité est acceptée si un administrateur habilité peut créer, consulter, modifier, historiser, exporter et auditer l’objet métier correspondant, et si un utilisateur non habilité ne peut ni le consulter ni le modifier hors périmètre.

## Sauvegarde

### Finalité

Le volet **Sauvegarde** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la Source of Truth.

### Règles de conception

- Les données critiques sont validées par contraintes métier et contraintes de base de données.
- Les opérations longues sont asynchrones, découpées en lots et relançables.
- Les lectures volumineuses utilisent la pagination cursor-based et des filtres sélectifs.
- Les écritures critiques sont transactionnelles, idempotentes et auditées.
- Les intégrations externes ne peuvent pas écraser silencieusement une donnée de référence.
- Les écarts entre découverte, import et vérité déclarative produisent un conflit explicite.
- Les données sensibles sont masquées selon les droits et jamais exposées dans les journaux.
- Les APIs publiques sont versionnées, documentées et soumises à rate limiting.

### Cas d’acceptation type

La capacité est acceptée si un administrateur habilité peut créer, consulter, modifier, historiser, exporter et auditer l’objet métier correspondant, et si un utilisateur non habilité ne peut ni le consulter ni le modifier hors périmètre.

## PRA/PCA

### Finalité

Le volet **PRA/PCA** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la Source of Truth.

### Règles de conception

- Les données critiques sont validées par contraintes métier et contraintes de base de données.
- Les opérations longues sont asynchrones, découpées en lots et relançables.
- Les lectures volumineuses utilisent la pagination cursor-based et des filtres sélectifs.
- Les écritures critiques sont transactionnelles, idempotentes et auditées.
- Les intégrations externes ne peuvent pas écraser silencieusement une donnée de référence.
- Les écarts entre découverte, import et vérité déclarative produisent un conflit explicite.
- Les données sensibles sont masquées selon les droits et jamais exposées dans les journaux.
- Les APIs publiques sont versionnées, documentées et soumises à rate limiting.

### Cas d’acceptation type

La capacité est acceptée si un administrateur habilité peut créer, consulter, modifier, historiser, exporter et auditer l’objet métier correspondant, et si un utilisateur non habilité ne peut ni le consulter ni le modifier hors périmètre.

## Observabilité

### Finalité

Le volet **Observabilité** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la Source of Truth.

### Règles de conception

- Les données critiques sont validées par contraintes métier et contraintes de base de données.
- Les opérations longues sont asynchrones, découpées en lots et relançables.
- Les lectures volumineuses utilisent la pagination cursor-based et des filtres sélectifs.
- Les écritures critiques sont transactionnelles, idempotentes et auditées.
- Les intégrations externes ne peuvent pas écraser silencieusement une donnée de référence.
- Les écarts entre découverte, import et vérité déclarative produisent un conflit explicite.
- Les données sensibles sont masquées selon les droits et jamais exposées dans les journaux.
- Les APIs publiques sont versionnées, documentées et soumises à rate limiting.

### Cas d’acceptation type

La capacité est acceptée si un administrateur habilité peut créer, consulter, modifier, historiser, exporter et auditer l’objet métier correspondant, et si un utilisateur non habilité ne peut ni le consulter ni le modifier hors périmètre.


## Exigences du volume

### REQ-00014 — N1 — Fonctionnelle

**Exigence :** La plateforme doit être déployable sur Kubernetes et Docker, avec observabilité, sauvegarde, PRA/PCA et runbooks.

**Justification :** Permettre exploitation industrielle.

**Vérification :** Test déploiement, test restauration, test supervision.

**Critère d’acceptation :** Les tableaux de bord et alertes critiques sont opérationnels.
### REQ-00256 — N1 — Exploitation

**Exigence :** Le périmètre Déploiement du volume Administration doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Déploiement fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Déploiement, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00257 — N2 — Audit

**Exigence :** Le domaine Déploiement doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00258 — N2 — Performance

**Exigence :** Le domaine Déploiement doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00259 — N1 — Exploitation

**Exigence :** Le périmètre Kubernetes du volume Administration doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Kubernetes fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Kubernetes, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00260 — N2 — Audit

**Exigence :** Le domaine Kubernetes doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00261 — N2 — Performance

**Exigence :** Le domaine Kubernetes doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00262 — N1 — Exploitation

**Exigence :** Le périmètre Docker du volume Administration doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Docker fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Docker, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00263 — N2 — Audit

**Exigence :** Le domaine Docker doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00264 — N2 — Performance

**Exigence :** Le domaine Docker doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00265 — N1 — Exploitation

**Exigence :** Le périmètre Sauvegarde du volume Administration doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Sauvegarde fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Sauvegarde, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00266 — N2 — Audit

**Exigence :** Le domaine Sauvegarde doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00267 — N2 — Performance

**Exigence :** Le domaine Sauvegarde doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00268 — N1 — Exploitation

**Exigence :** Le périmètre PRA/PCA du volume Administration doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine PRA/PCA fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion PRA/PCA, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00269 — N2 — Audit

**Exigence :** Le domaine PRA/PCA doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00270 — N2 — Performance

**Exigence :** Le domaine PRA/PCA doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00271 — N1 — Exploitation

**Exigence :** Le périmètre Observabilité du volume Administration doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Observabilité fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Observabilité, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00272 — N2 — Audit

**Exigence :** Le domaine Observabilité doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00273 — N2 — Performance

**Exigence :** Le domaine Observabilité doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00289 — N1 — Technique

**Exigence :** PostgreSQL doit être en version 16 ou supérieure sauf contrainte de support explicitement acceptée.

**Justification :** Bénéficier des capacités modernes de performance et observabilité.

**Vérification :** Contrôle manifeste de déploiement.

**Critère d’acceptation :** La version effective est visible dans le diagnostic système.
### REQ-00290 — N1 — Technique

**Exigence :** Le cluster doit utiliser un primaire lecture/écriture et au moins deux réplicas lecture seule.

**Justification :** Assurer HA et scalabilité lecture.

**Vérification :** Test d’intégration cluster.

**Critère d’acceptation :** Les lectures peuvent être routées vers réplicas, les écritures vers primaire.
### REQ-00291 — N1 — Technique

**Exigence :** PgBouncer doit être utilisé pour le pooling applicatif avec configuration adaptée aux transactions courtes.

**Justification :** Éviter saturation connexions PostgreSQL.

**Vérification :** Test charge connexions.

**Critère d’acceptation :** Le pool absorbe la charge cible sans épuisement des connexions.
### REQ-00292 — N1 — Technique

**Exigence :** pgBackRest ou équivalent doit gérer sauvegardes, WAL archiving et PITR.

**Justification :** Garantir restaurabilité.

**Vérification :** Test restauration.

**Critère d’acceptation :** Restauration à un instant donné démontrée sur environnement isolé.
### REQ-00293 — N1 — Technique

**Exigence :** Les tables audit, discovery, historique, métriques, relations, IP history, scans, cloud metadata, DNS/DHCP events doivent être partitionnées.

**Justification :** Prévenir croissance monolithique.

**Vérification :** Contrôle DDL automatique.

**Critère d’acceptation :** Chaque table massive a une clé de partition stable et documentée.
### REQ-00294 — N1 — Technique

**Exigence :** La stratégie hot/warm/cold doit être configurable par domaine, tenant et type d’événement.

**Justification :** Adapter rétention aux contraintes métier et coût.

**Vérification :** Test archivage/purge.

**Critère d’acceptation :** Les partitions froides sont externalisables vers S3, Parquet ou réplica analytique.
### REQ-00295 — N1 — Technique

**Exigence :** Chaque endpoint critique doit avoir un budget SQL, un timeout et une preuve EXPLAIN sur jeu représentatif.

**Justification :** Maîtriser latence p95/p99.

**Vérification :** Pipeline performance.

**Critère d’acceptation :** Les plans SQL de référence sont conservés et comparés.
### REQ-00296 — N1 — Technique

**Exigence :** pg_stat_statements doit être activé et supervisé.

**Justification :** Identifier requêtes lentes et régressions.

**Vérification :** Contrôle métriques.

**Critère d’acceptation :** Dashboard requêtes lentes opérationnel.
### REQ-00297 — N1 — Technique

**Exigence :** Les migrations doivent être versionnées, idempotentes, rejouables et accompagnées d’un plan rollback compatible.

**Justification :** Réduire risque d’évolution schéma.

**Vérification :** Test migration forward/rollback.

**Critère d’acceptation :** Une migration échouée ne laisse pas le schéma incohérent.
### REQ-00298 — N1 — Technique

**Exigence :** Le modèle doit séparer OLTP et analytique, PostgreSQL transactionnel ne servant pas d’entrepôt illimité.

**Justification :** Éviter surcharge transactionnelle.

**Vérification :** Revue architecture reporting.

**Critère d’acceptation :** Les exports/reportings lourds passent par files, vues matérialisées ou stockage analytique.


## Critères de réception du volume

Le volume est recevable si :

1. toutes les exigences N1 liées au volume sont couvertes ;
2. chaque exigence possède un test ou une preuve ;
3. les APIs sont documentées ;
4. les règles métier sont implémentées côté domaine et contrôlées côté base lorsque nécessaire ;
5. les scénarios d’erreur sont testés ;
6. les journaux d’audit sont exploitables ;
7. les performances critiques respectent les budgets définis ;
8. l’intégration à la Source of Truth est effective ;
9. la documentation d’exploitation existe ;
10. les risques résiduels sont acceptés.
