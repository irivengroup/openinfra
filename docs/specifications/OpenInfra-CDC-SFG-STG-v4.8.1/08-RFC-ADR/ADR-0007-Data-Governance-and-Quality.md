# ADR-0007-Data-Governance-and-Quality — Data Governance et Data Quality Center

## Statut

Accepté pour OpenInfra v4.0.0.

## Contexte

OpenInfra doit éviter de devenir un inventaire automatiquement alimenté mais non fiable. Les sources autoritatives, scores, certifications et règles qualité deviennent des capacités de niveau enterprise.

## Décision

Adopter un module de gouvernance et un module qualité séparés, alimentant tous les domaines sans écraser silencieusement la IT Ressources Management.

## Conséquences

Les opérations de réconciliation sont plus explicites, auditables et gouvernées. Les workflows restent internes au référentiel et ne créent pas d’ITSM intégré.

## Critères de validation

- Exigences associées présentes dans `11-Matrices/Exigences.csv`.
- Cas d’usage et tests associés présents dans les matrices.
- Audit, RBAC/ABAC, observabilité et performance couverts.
- Aucune capacité ITSM native introduite.
