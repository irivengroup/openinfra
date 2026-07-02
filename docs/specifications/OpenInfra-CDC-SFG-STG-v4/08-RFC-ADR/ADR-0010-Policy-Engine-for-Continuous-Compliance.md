# ADR-0010-Policy-Engine-for-Continuous-Compliance — Policy Engine transversal

## Statut

Accepté pour OpenInfra v4.0.0.

## Contexte

Les règles de conformité doivent couvrir data, IPAM, sécurité, cloud, Kubernetes, FinOps et DCIM.

## Décision

Introduire un moteur de politiques déclaratif, versionné, simulable et auditable.

## Conséquences

La conformité devient continue et mesurable. Les exceptions sont gouvernées avec expiration.

## Critères de validation

- Exigences associées présentes dans `11-Matrices/Exigences.csv`.
- Cas d’usage et tests associés présents dans les matrices.
- Audit, RBAC/ABAC, observabilité et performance couverts.
- Aucune capacité ITSM native introduite.
