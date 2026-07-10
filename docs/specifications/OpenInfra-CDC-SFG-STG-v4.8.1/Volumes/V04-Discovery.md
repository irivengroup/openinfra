---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# V04 — Discovery

## Positionnement

Le volume **V04 — Discovery** décrit les spécifications applicables au domaine associé. Il est normatif pour la conception, le développement, les tests et la réception.

## Sections couvertes

| Section |
| --- |
| SNMP |
| SSH |
| VMware |
| Proxmox |
| Hyper-V |
| Kubernetes |
| Cloud |
| LLDP/CDP |
| NetFlow/sFlow/IPFIX |
| Agents optionnels |
| Réconciliation |

## Principes transverses

- API-first : toute capacité métier importante doit être exposée par API versionnée.
- Sécurité by design : RBAC, ABAC, audit, chiffrement et séparation tenant doivent être natifs.
- Observabilité by design : métriques, logs structurés, traces et événements doivent être corrélables.
- Performance by design : pagination, indexation, partitionnement et bornage des traitements sont obligatoires.
- Résilience by design : reprise, retry, dead-letter queue et idempotence doivent être prévus.
- Exploitabilité : chaque capacité doit être supervisable, sauvegardable et documentée.


## SNMP

### Finalité

Le volet **SNMP** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## SSH

### Finalité

Le volet **SSH** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## VMware

### Finalité

Le volet **VMware** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Proxmox

### Finalité

Le volet **Proxmox** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Hyper-V

### Finalité

Le volet **Hyper-V** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

Le volet **Kubernetes** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Cloud

### Finalité

Le volet **Cloud** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## LLDP/CDP

### Finalité

Le volet **LLDP/CDP** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## NetFlow/sFlow/IPFIX

### Finalité

Le volet **NetFlow/sFlow/IPFIX** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Agents optionnels

### Finalité

Le volet **Agents optionnels** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

## Réconciliation

### Finalité

Le volet **Réconciliation** doit être traité comme une capacité d’enterprise, exploitable par interface utilisateur, API, import/export et automatisation lorsque le domaine le justifie. La capacité doit être observable, sécurisée par RBAC/ABAC, historisée et intégrée à la RSOT (Ressource Source of Truth).

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

### REQ-00008 — N1 — Fonctionnelle

**Exigence :** La découverte doit être distribuée, bornée, planifiable, auditée, relançable et non bloquante pour l’API.

**Justification :** Maintenir l’usage interactif pendant les scans.

**Vérification :** Tests workers, crash recovery, test charge.

**Critère d’acceptation :** Un crash worker ne perd aucun job validé et l’API reste disponible.
### REQ-00094 — N2 — Fonctionnelle

**Exigence :** Le périmètre SNMP du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine SNMP fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion SNMP, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00095 — N2 — Audit

**Exigence :** Le domaine SNMP doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00096 — N1 — Performance

**Exigence :** Le domaine SNMP doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00097 — N2 — Fonctionnelle

**Exigence :** Le périmètre SSH du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine SSH fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion SSH, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00098 — N2 — Audit

**Exigence :** Le domaine SSH doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00099 — N1 — Performance

**Exigence :** Le domaine SSH doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00100 — N2 — Fonctionnelle

**Exigence :** Le périmètre VMware du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine VMware fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion VMware, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00101 — N2 — Audit

**Exigence :** Le domaine VMware doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00102 — N1 — Performance

**Exigence :** Le domaine VMware doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00103 — N2 — Fonctionnelle

**Exigence :** Le périmètre Proxmox du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Proxmox fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Proxmox, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00104 — N2 — Audit

**Exigence :** Le domaine Proxmox doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00105 — N1 — Performance

**Exigence :** Le domaine Proxmox doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00106 — N2 — Fonctionnelle

**Exigence :** Le périmètre Hyper-V du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Hyper-V fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Hyper-V, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00107 — N2 — Audit

**Exigence :** Le domaine Hyper-V doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00108 — N1 — Performance

**Exigence :** Le domaine Hyper-V doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00109 — N2 — Fonctionnelle

**Exigence :** Le périmètre Kubernetes du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Kubernetes fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Kubernetes, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00110 — N2 — Audit

**Exigence :** Le domaine Kubernetes doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00111 — N1 — Performance

**Exigence :** Le domaine Kubernetes doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00112 — N2 — Fonctionnelle

**Exigence :** Le périmètre Cloud du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Cloud fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Cloud, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00113 — N2 — Audit

**Exigence :** Le domaine Cloud doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00114 — N1 — Performance

**Exigence :** Le domaine Cloud doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00115 — N2 — Fonctionnelle

**Exigence :** Le périmètre LLDP/CDP du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine LLDP/CDP fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion LLDP/CDP, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00116 — N2 — Audit

**Exigence :** Le domaine LLDP/CDP doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00117 — N1 — Performance

**Exigence :** Le domaine LLDP/CDP doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00118 — N2 — Fonctionnelle

**Exigence :** Le périmètre NetFlow/sFlow/IPFIX du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine NetFlow/sFlow/IPFIX fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion NetFlow/sFlow/IPFIX, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00119 — N2 — Audit

**Exigence :** Le domaine NetFlow/sFlow/IPFIX doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00120 — N1 — Performance

**Exigence :** Le domaine NetFlow/sFlow/IPFIX doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00121 — N2 — Fonctionnelle

**Exigence :** Le périmètre Agents optionnels du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Agents optionnels fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Agents optionnels, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00122 — N2 — Audit

**Exigence :** Le domaine Agents optionnels doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00123 — N1 — Performance

**Exigence :** Le domaine Agents optionnels doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Justification :** Les opérations longues ne doivent pas bloquer les APIs interactives.

**Vérification :** Test import/export, test file de messages et test reprise.

**Critère d’acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.
### REQ-00124 — N2 — Fonctionnelle

**Exigence :** Le périmètre Réconciliation du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Justification :** Le domaine Réconciliation fait partie du périmètre entreprise attendu pour OpenInfra.

**Vérification :** Revue documentaire, test API/UI, test d’intégration et matrice de conformité.

**Critère d’acceptation :** Le dossier contient les règles de gestion Réconciliation, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.
### REQ-00125 — N2 — Audit

**Exigence :** Le domaine Réconciliation doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Justification :** L’exploitation entreprise exige traçabilité et diagnostic fiable.

**Vérification :** Test audit et test de corrélation trace/log/event.

**Critère d’acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.
### REQ-00126 — N1 — Performance

**Exigence :** Le domaine Réconciliation doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

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

## v0.29.82 — Réconciliation Discovery multisource gouvernée

### REQ-00823 — Preuve, score, conflit et résolution

OpenInfra conserve chaque observation comme une preuve immuable, isolée par tenant et identifiée par une empreinte SHA-256 du payload canonique. Les payloads sont bornés à 1 MiB, strictement validés et refusent les clés susceptibles de transporter un secret.

Le rapprochement exige au moins deux identités de source et calcule des scores déterministes de confiance, fraîcheur, complétude et qualité globale. Les valeurs divergentes sont exposées par chemin d’attribut avec toutes leurs variantes ; aucun score ne provoque un écrasement silencieux.

La résolution exige une sélection valide pour chaque conflit et une justification auditée. Elle produit une décision de gouvernance avec `rsot_write_executed=false` ; l’application éventuelle au RSOT demeure une opération distincte, explicite et soumise à son propre contrôle d’impact.

**Acceptation :** service, CLI, API, OpenAPI et web offrent soumission, consultation, pagination, rapprochement et résolution ; les dépôts JSON/PostgreSQL garantissent immutabilité et idempotence ; PostgreSQL partitionne les preuves et cas par tenant ; les tests démontrent l’absence de mutation RSOT.

