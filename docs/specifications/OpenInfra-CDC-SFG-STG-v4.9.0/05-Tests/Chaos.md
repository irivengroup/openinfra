---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Tests chaos et résilience

## Objectif

Valider panne worker, panne primaire PostgreSQL, perte collector, saturation file et restauration.

## Scénarios obligatoires

- Démarrage cluster applicatif multi-réplicas.
- Test PostgreSQL primary/replica.
- Simulation de latence base et dépendances externes.
- Exécution import massif pendant consultations UI/API.
- Allocation IP concurrente.
- Recherche profonde avec pagination cursor-based.
- Purge et archivage partitionné.
- Restauration d’une partition.
- Bascule PostgreSQL sous charge.
- Vérification des dashboards et alertes.

## Critères d’acceptation

Les tests sont acceptés si les seuils définis dans les exigences N1 sont mesurés, reproductibles et historisés dans un rapport de validation.
