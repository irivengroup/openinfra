---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# V05 — DCIM

## Positionnement

Le volume **V05 — DCIM** décrit les spécifications applicables au domaine associé. Il est normatif pour la conception, le développement, les tests et la réception.

## Sections couvertes

| Section |
| --- |
| Plans 2D/3D |
| Coordonnées ligne/colonne/X/Y/Z |
| Racks |
| Patch panels |
| PDU |
| Énergie |
| Refroidissement |
| Capacité |
| Jumeau numérique |

## Principes transverses

- API-first : toute capacité métier importante doit être exposée par API versionnée.
- Sécurité by design : RBAC, ABAC, audit, chiffrement et séparation tenant doivent être natifs.
- Observabilité by design : métriques, logs structurés, traces et événements doivent être corrélables.
- Performance by design : pagination, indexation, partitionnement et bornage des traitements sont obligatoires.
- Résilience by design : reprise, retry, dead-letter queue et idempotence doivent être prévus.
- Exploitabilité : chaque capacité doit être supervisable, sauvegardable et documentée.


## Plans 2D/3D

### Finalité

Le volet **Plans 2D/3D** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Coordonnées ligne/colonne/X/Y/Z

### Finalité

Le volet **Coordonnées ligne/colonne/X/Y/Z** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Racks

### Finalité

Le volet **Racks** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Patch panels

### Finalité

Le volet **Patch panels** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## PDU

### Finalité

Le volet **PDU** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Énergie

### Finalité

Le volet **Énergie** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Refroidissement

### Finalité

Le volet **Refroidissement** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Capacité

### Finalité

Le volet **Capacité** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Jumeau numérique

### Finalité

Le volet **Jumeau numérique** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

### REQ-00009 — N1 — Fonctionnelle

**Exigence :** Le DCIM doit fournir plans 2D/3D, racks, patch panels, PDU, énergie, refroidissement, capacité et jumeau numérique.

**Justification :** Permettre exploitation datacenter complète.

**Vérification :** Tests UI/API et jeu de salle représentatif.

**Critère d’acceptation :** Le parcours site → salle → rack → équipement → câble → alimentation est navigable.
### REQ-00127 — N1 — Fonctionnelle

**Exigence :** Le périmètre Plans 2D/3D du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Plans 2D/3D fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Plans 2D/3D, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00128 — N2 — Audit

**Exigence :** Le domaine Plans 2D/3D doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00129 — N2 — Performance

**Exigence :** Le domaine Plans 2D/3D doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00130 — N1 — Fonctionnelle

**Exigence :** Le périmètre Coordonnées ligne/colonne/X/Y/Z du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Coordonnées ligne/colonne/X/Y/Z fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Coordonnées ligne/colonne/X/Y/Z, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00131 — N2 — Audit

**Exigence :** Le domaine Coordonnées ligne/colonne/X/Y/Z doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00132 — N2 — Performance

**Exigence :** Le domaine Coordonnées ligne/colonne/X/Y/Z doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00133 — N1 — Fonctionnelle

**Exigence :** Le périmètre Racks du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Racks fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Racks, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00134 — N2 — Audit

**Exigence :** Le domaine Racks doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00135 — N2 — Performance

**Exigence :** Le domaine Racks doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00136 — N1 — Fonctionnelle

**Exigence :** Le périmètre Patch panels du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Patch panels fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Patch panels, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00137 — N2 — Audit

**Exigence :** Le domaine Patch panels doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00138 — N2 — Performance

**Exigence :** Le domaine Patch panels doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00139 — N1 — Fonctionnelle

**Exigence :** Le périmètre PDU du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine PDU fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion PDU, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00140 — N2 — Audit

**Exigence :** Le domaine PDU doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00141 — N2 — Performance

**Exigence :** Le domaine PDU doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00142 — N1 — Fonctionnelle

**Exigence :** Le périmètre Énergie du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Énergie fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Énergie, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00143 — N2 — Audit

**Exigence :** Le domaine Énergie doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00144 — N2 — Performance

**Exigence :** Le domaine Énergie doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00145 — N1 — Fonctionnelle

**Exigence :** Le périmètre Refroidissement du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Refroidissement fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Refroidissement, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00146 — N2 — Audit

**Exigence :** Le domaine Refroidissement doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00147 — N2 — Performance

**Exigence :** Le domaine Refroidissement doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00148 — N1 — Fonctionnelle

**Exigence :** Le périmètre Capacité du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Capacité fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Capacité, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00149 — N2 — Audit

**Exigence :** Le domaine Capacité doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00150 — N2 — Performance

**Exigence :** Le domaine Capacité doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00151 — N1 — Fonctionnelle

**Exigence :** Le périmètre Jumeau numérique du volume DCIM doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Jumeau numérique fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Jumeau numérique, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00152 — N2 — Audit

**Exigence :** Le domaine Jumeau numérique doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00153 — N2 — Performance

**Exigence :** Le domaine Jumeau numérique doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

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
8. l’intégration à la RSOT (Ressource Source of Truth) est effective ;
9. la documentation d’exploitation existe ;
10. les risques résiduels sont acceptés.
