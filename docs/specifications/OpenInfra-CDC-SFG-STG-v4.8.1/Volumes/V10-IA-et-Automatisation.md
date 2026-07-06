---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# V10 — IA & Automatisation

## Positionnement

Le volume **V10 — IA & Automatisation** décrit les spécifications applicables au domaine associé. Il est normatif pour la conception, le développement, les tests et la réception.

## Sections couvertes

| Section |
| --- |
| Détection d’anomalies |
| Capacity planning |
| Suggestions de placement |
| Optimisation des préfixes |
| Prévision de saturation |
| Recherche en langage naturel |
| Assistant RAG sur le référentiel |

## Principes transverses

- API-first : toute capacité métier importante doit être exposée par API versionnée.
- Sécurité by design : RBAC, ABAC, audit, chiffrement et séparation tenant doivent être natifs.
- Observabilité by design : métriques, logs structurés, traces et événements doivent être corrélables.
- Performance by design : pagination, indexation, partitionnement et bornage des traitements sont obligatoires.
- Résilience by design : reprise, retry, dead-letter queue et idempotence doivent être prévus.
- Exploitabilité : chaque capacité doit être supervisable, sauvegardable et documentée.


## Détection d’anomalies

### Finalité

Le volet **Détection d’anomalies** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Capacity planning

### Finalité

Le volet **Capacity planning** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Suggestions de placement

### Finalité

Le volet **Suggestions de placement** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Optimisation des préfixes

### Finalité

Le volet **Optimisation des préfixes** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Prévision de saturation

### Finalité

Le volet **Prévision de saturation** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Recherche en langage naturel

### Finalité

Le volet **Recherche en langage naturel** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

## Assistant RAG sur le référentiel

### Finalité

Le volet **Assistant RAG sur le référentiel** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la IT Ressources Management.

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

### REQ-00013 — N1 — Fonctionnelle

**Exigence :** Les fonctions IA doivent être optionnelles, gouvernées, auditables et ne jamais modifier la IT Ressources Management sans validation explicite.

**Justification :** Éviter les risques d’automatisation non maîtrisée.

**Vérification :** Tests gouvernance IA, logs décisions.

**Critère d’acceptation :** Toute suggestion IA est traçable et validée avant application.
### REQ-00235 — N2 — Automatisation

**Exigence :** Le périmètre Détection d’anomalies du volume IA & Automatisation doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Détection d’anomalies fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Détection d’anomalies, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00236 — N2 — Audit

**Exigence :** Le domaine Détection d’anomalies doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00237 — N2 — Performance

**Exigence :** Le domaine Détection d’anomalies doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00238 — N2 — Automatisation

**Exigence :** Le périmètre Capacity planning du volume IA & Automatisation doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Capacity planning fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Capacity planning, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00239 — N2 — Audit

**Exigence :** Le domaine Capacity planning doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00240 — N2 — Performance

**Exigence :** Le domaine Capacity planning doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00241 — N2 — Automatisation

**Exigence :** Le périmètre Suggestions de placement du volume IA & Automatisation doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Suggestions de placement fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Suggestions de placement, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00242 — N2 — Audit

**Exigence :** Le domaine Suggestions de placement doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00243 — N2 — Performance

**Exigence :** Le domaine Suggestions de placement doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00244 — N2 — Automatisation

**Exigence :** Le périmètre Optimisation des préfixes du volume IA & Automatisation doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Optimisation des préfixes fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Optimisation des préfixes, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00245 — N2 — Audit

**Exigence :** Le domaine Optimisation des préfixes doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00246 — N2 — Performance

**Exigence :** Le domaine Optimisation des préfixes doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00247 — N2 — Automatisation

**Exigence :** Le périmètre Prévision de saturation du volume IA & Automatisation doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Prévision de saturation fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Prévision de saturation, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00248 — N2 — Audit

**Exigence :** Le domaine Prévision de saturation doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00249 — N2 — Performance

**Exigence :** Le domaine Prévision de saturation doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00250 — N2 — Automatisation

**Exigence :** Le périmètre Recherche en langage naturel du volume IA & Automatisation doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Recherche en langage naturel fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Recherche en langage naturel, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00251 — N2 — Audit

**Exigence :** Le domaine Recherche en langage naturel doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00252 — N2 — Performance

**Exigence :** Le domaine Recherche en langage naturel doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00253 — N2 — Automatisation

**Exigence :** Le périmètre Assistant RAG sur le référentiel du volume IA & Automatisation doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Assistant RAG sur le référentiel fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Assistant RAG sur le référentiel, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00254 — N2 — Audit

**Exigence :** Le domaine Assistant RAG sur le référentiel doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00255 — N2 — Performance

**Exigence :** Le domaine Assistant RAG sur le référentiel doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.


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
