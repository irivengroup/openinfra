---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Tests de performance

## Objectif

Valider les budgets p95/p99, les requêtes critiques, les indexes et les pipelines batch.

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

## Gate haute performance v4.9.0

La CI valide la configuration ASGI, les budgets de pools, le streaming et les protections de corps. Un environnement de performance dédié exécute les benchmarks PostgreSQL réels, PgBouncer, réplicas et navigateur. Toute régression supérieure à 10 % sur un indicateur p95/p99 stable bloque la promotion jusqu’à analyse et décision documentée.
