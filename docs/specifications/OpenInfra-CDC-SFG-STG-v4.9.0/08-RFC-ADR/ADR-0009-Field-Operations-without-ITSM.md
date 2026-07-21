# ADR-0009-Field-Operations-without-ITSM — Opérations terrain sans ticketing

## Statut

Accepté pour OpenInfra v4.0.0.

## Contexte

Les techniciens doivent disposer d’une fiche terrain fiable sans transformer OpenInfra en outil ITSM.

## Décision

Créer Field Operations pour localisation, QR code, preuve, checklist et verrou logique, sans tickets natifs.

## Conséquences

Les interventions sont traçables dans l’actif mais restent intégrables avec un ITSM externe.

## Critères de validation

- Exigences associées présentes dans `11-Matrices/Exigences.csv`.
- Cas d’usage et tests associés présents dans les matrices.
- Audit, RBAC/ABAC, observabilité et performance couverts.
- Aucune capacité ITSM native introduite.
