# OpenInfra — Plan équipe et gouvernance

## Organisation cible

| Rôle | Charge recommandée | Responsabilités |
|---|---:|---|
| Directeur programme | 0,5 à 1 ETP | Arbitrage, budget, risques, comités, trajectoire. |
| Product Owner | 1 ETP | Backlog, priorisation, critères métier, acceptation fonctionnelle. |
| Architecte entreprise | 0,5 à 1 ETP | Urbanisation, CCTP/CdCF, conformité SI, trajectoire cible. |
| Architecte solution | 1 ETP | Architecture applicative, ADR/RFC, découpage modules, revues. |
| DBA PostgreSQL senior | 1 ETP dès P01 | HA, partitionnement, migrations, index, performance, PITR. |
| SRE/Platform engineer | 1 à 2 ETP | Kubernetes, Helm, CI/CD, observabilité, PRA/PCA. |
| Backend engineers | 3 à 5 ETP | Domain services, APIs, jobs, intégrations, sécurité applicative. |
| Frontend engineers | 2 ETP | UI, design system, DCIM/IPAM/graphes, accessibilité. |
| Discovery/network engineers | 2 ETP | SNMP, SSH, NetFlow, cloud, virtualisation, réconciliation. |
| Security engineer | 1 ETP | IAM, RBAC/ABAC, Vault, threat modeling, scans, audit. |
| QA automation engineers | 2 ETP | Tests unitaires, intégration, API, performance, chaos, e2e. |
| Technical writer | 0,5 à 1 ETP | Documentation, runbooks, guides API, formation. |

## Comités

| Comité | Fréquence | Objectif |
|---|---|---|
| Comité programme | Mensuel | Budget, risques, jalons, décisions majeures. |
| Comité architecture | Hebdomadaire | ADR, standards, revues de conception, dette technique. |
| Comité produit | Hebdomadaire | Priorisation, arbitrage fonctionnel, retours utilisateurs. |
| Comité sécurité | Bimensuel | Menaces, vulnérabilités, IAM, secrets, audit. |
| Comité exploitation | Bimensuel | Déploiement, observabilité, PRA/PCA, runbooks. |
| Revue sprint | Toutes les deux semaines | Démonstration, acceptation, dette, métriques. |

## Règles de décision

- Toute décision structurante est documentée par ADR.
- Toute exigence N1 non respectée bloque la release ou exige une dérogation formelle.
- Tout changement de périmètre est évalué par impact fonctionnel, technique, sécurité, performance et exploitation.
- Toute suppression de fonctionnalité exige remplacement compatible et tests de non-régression.
- Toute intégration externe passe par contrat API, tests contractuels et modèle d’erreur.

## Indicateurs de pilotage

- Avancement exigences N1.
- Couverture tests.
- Taux de réussite CI.
- Dette technique ouverte.
- Bugs bloquants.
- Vulnérabilités critiques/hautes.
- Performance p95/p99.
- Nombre de requêtes SQL lentes.
- État des risques.
- Avancement documentation.
- État des gates Go/No-Go.
