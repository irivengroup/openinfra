---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Stratégie de tests

## Objectif

La stratégie de test vise à démontrer que la solution est fonctionnelle, sûre, performante, résiliente et exploitable.

## Niveaux de test

- Tests unitaires domaine.
- Tests d’intégration PostgreSQL.
- Tests API REST/GraphQL.
- Tests sécurité RBAC/ABAC/secrets.
- Tests de concurrence.
- Tests de performance.
- Tests de charge.
- Tests chaos/failover.
- Tests de migration.
- Tests de restauration.
- Tests de non-régression.

## Couverture contractuelle

Chaque exigence N1 doit être liée à au moins un test ou une preuve de validation. La matrice `11-Matrices/Traceabilite.csv` matérialise ce lien.

## Tests dérivés

Le dossier contient 130 tests ou preuves de validation identifiés.

## Niveaux supplémentaires v4.9.0

- tests unitaires des politiques de dimensionnement ;
- intégration ASGI lifespan, backpressure et streaming ;
- intégration pool PostgreSQL avec épuisement/reprise ;
- charge Pro/Entreprise avec PostgreSQL et PgBouncer réels ;
- navigateur avec budgets de bundle, LCP et INP ;
- endurance et chaos sur perte de replica, BFF et worker.
