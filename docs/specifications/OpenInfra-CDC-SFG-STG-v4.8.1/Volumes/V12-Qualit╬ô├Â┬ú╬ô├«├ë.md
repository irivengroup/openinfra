---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# V12 — Qualité

## Positionnement

Le volume **V12 — Qualité** décrit les spécifications applicables au domaine associé. Il est normatif pour la conception, le développement, les tests et la réception.

## Sections couvertes

| Section |
| --- |
| Tests |
| CI/CD |
| Performances |
| Critères d’acceptation |
| Matrice d’exigences |

## Principes transverses

- API-first : toute capacité métier importante doit être exposée par API versionnée.
- Sécurité by design : RBAC, ABAC, audit, chiffrement et séparation tenant doivent être natifs.
- Observabilité by design : métriques, logs structurés, traces et événements doivent être corrélables.
- Performance by design : pagination, indexation, partitionnement et bornage des traitements sont obligatoires.
- Résilience by design : reprise, retry, dead-letter queue et idempotence doivent être prévus.
- Exploitabilité : chaque capacité doit être supervisable, sauvegardable et documentée.


## Tests

### Finalité

Le volet **Tests** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## CI/CD

### Finalité

Le volet **CI/CD** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Performances

### Finalité

Le volet **Performances** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Critères d’acceptation

### Finalité

Le volet **Critères d’acceptation** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Matrice d’exigences

### Finalité

Le volet **Matrice d’exigences** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

### REQ-00015 — N1 — Fonctionnelle

**Exigence :** Chaque exigence N1 doit disposer d’un critère d’acceptation, d’un test associé et d’une traçabilité vers un cas d’usage.

**Justification :** Garantir pilotage contractuel et vérification.

**Vérification :** Contrôle matrice exigences/tests.

**Critère d’acceptation :** Aucune exigence N1 orpheline dans la matrice.
### REQ-00274 — N1 — Qualité

**Exigence :** Le périmètre Tests du volume Qualité doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Tests fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Tests, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00275 — N2 — Audit

**Exigence :** Le domaine Tests doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00276 — N1 — Performance

**Exigence :** Le domaine Tests doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00277 — N1 — Qualité

**Exigence :** Le périmètre CI/CD du volume Qualité doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine CI/CD fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion CI/CD, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00278 — N2 — Audit

**Exigence :** Le domaine CI/CD doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00279 — N1 — Performance

**Exigence :** Le domaine CI/CD doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00280 — N1 — Qualité

**Exigence :** Le périmètre Performances du volume Qualité doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Performances fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Performances, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00281 — N2 — Audit

**Exigence :** Le domaine Performances doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00282 — N1 — Performance

**Exigence :** Le domaine Performances doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00283 — N1 — Qualité

**Exigence :** Le périmètre Critères d’acceptation du volume Qualité doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Critères d’acceptation fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Critères d’acceptation, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00284 — N2 — Audit

**Exigence :** Le domaine Critères d’acceptation doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00285 — N1 — Performance

**Exigence :** Le domaine Critères d’acceptation doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00286 — N1 — Qualité

**Exigence :** Le périmètre Matrice d’exigences du volume Qualité doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Matrice d’exigences fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Matrice d’exigences, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00287 — N2 — Audit

**Exigence :** Le domaine Matrice d’exigences doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00288 — N1 — Performance

**Exigence :** Le domaine Matrice d’exigences doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00299 — N1 — Performance

**Exigence :** Recherche par identifiant inférieure à 50 ms p95 sur jeu représentatif.

**Justification :** Accès opérationnel immédiat.

**Vérification :** Benchmark API.

**Critère d’acceptation :** p95 mesuré inférieur au seuil.
### REQ-00300 — N1 — Performance

**Exigence :** Recherche indexée simple inférieure à 200 ms p95.

**Justification :** Préserver expérience utilisateur.

**Vérification :** Benchmark API.

**Critère d’acceptation :** p95 mesuré inférieur au seuil.
### REQ-00301 — N1 — Performance

**Exigence :** Recherche IPAM dans VRF inférieure à 300 ms p95.

**Justification :** IPAM doit rester rapide avec VRF et chevauchements.

**Vérification :** Benchmark IPAM.

**Critère d’acceptation :** p95 mesuré inférieur au seuil.
### REQ-00302 — N1 — Performance

**Exigence :** Recherche équipement par clé unique inférieure à 100 ms p95.

**Justification :** Support interventions rapides.

**Vérification :** Benchmark ITRM.

**Critère d’acceptation :** p95 mesuré inférieur au seuil.
### REQ-00303 — N1 — Performance

**Exigence :** Pagination API standard inférieure à 500 ms p95.

**Justification :** Navigation stable.

**Vérification :** Benchmark API.

**Critère d’acceptation :** p95 mesuré inférieur au seuil.
### REQ-00304 — N1 — Performance

**Exigence :** Insertion batch supérieure ou égale à 50 000 lignes/minute par worker.

**Justification :** Support imports/discovery massifs.

**Vérification :** Benchmark batch.

**Critère d’acceptation :** Débit mesuré atteint ou dépasse le seuil.
### REQ-00305 — N1 — Performance

**Exigence :** p95 API critique inférieur à 500 ms et p99 inférieur à 1 500 ms.

**Justification :** Garantir performance sous charge.

**Vérification :** Test charge.

**Critère d’acceptation :** Seuils respectés pendant le scénario cible.
### REQ-00306 — N1 — Performance

**Exigence :** La solution doit supporter au minimum 500 utilisateurs simultanés et 10 000 appels API/minute.

**Justification :** Dimensionnement enterprise.

**Vérification :** Test charge distribué.

**Critère d’acceptation :** Aucune erreur critique ni saturation non contrôlée.
### REQ-00307 — N1 — Performance

**Exigence :** La solution doit importer 1 000 000 lignes en batch sans interrompre l’usage interactif.

**Justification :** Garantir coexistence traitements longs et UI.

**Vérification :** Test charge mixte.

**Critère d’acceptation :** Latence interactive reste dans le budget défini.
### REQ-00308 — N1 — Performance

**Exigence :** Les allocations IP concurrentes doivent rester sans conflit sous charge.

**Justification :** Intégrité IPAM critique.

**Vérification :** Test de concurrence.

**Critère d’acceptation :** Aucun doublon ni état incohérent.


## Critères de réception du volume

Le volume est recevable si :

1. toutes les exigences N1 liées au volume sont couvertes ;
2. chaque exigence possède un test ou une preuve ;
3. les APIs sont documentées ;
4. les règles métier sont implémentées côté domaine et contrôlées côté base lorsque nécessaire ;
5. les scénarios d’erreur sont testés ;
6. les journaux d’audit sont exploitables ;
7. les performances critiques respectent les budgets définis ;
8. l’intégration à la IT Ressources Management est effective ;
9. la documentation d’exploitation existe ;
10. les risques résiduels sont acceptés.
