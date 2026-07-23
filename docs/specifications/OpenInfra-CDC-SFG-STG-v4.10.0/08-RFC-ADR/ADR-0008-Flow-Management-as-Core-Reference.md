# ADR-0008-Flow-Management-as-Core-Reference — Matrice de flux comme référentiel de sécurité

## Statut

Accepté pour OpenInfra v4.0.0.

## Contexte

Les migrations, audits sécurité et segmentations exigent une vue déclarée et observée des flux réseau.

## Décision

Intégrer la matrice de flux comme domaine fonctionnel OpenInfra, corrélée avec IPAM, dépendances et policy engine.

## Conséquences

Les volumes de flux observés sont massifs et doivent être agrégés, partitionnés et historisés avec rétention contrôlée.

## Critères de validation

- Exigences associées présentes dans `11-Matrices/Exigences.csv`.
- Cas d’usage et tests associés présents dans les matrices.
- Audit, RBAC/ABAC, observabilité et performance couverts.
- Aucune capacité ITSM native introduite.
