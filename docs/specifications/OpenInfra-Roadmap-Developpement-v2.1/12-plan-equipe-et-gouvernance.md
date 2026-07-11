# OpenInfra — Plan équipe et gouvernance v2

## Organisation cible

| Rôle | Nombre cible | Responsabilités principales |
|---|---:|---|
| Directeur programme | 1 | Pilotage, budget, risques, arbitrages. |
| Product Owner | 1 | Backlog, priorisation, critères d’acceptation. |
| Architecte enterprise | 1 | Urbanisation, ADR/RFC, alignement CDC. |
| Architecte solution | 1 | Architecture technique et intégration. |
| DBA PostgreSQL senior | 1-2 | PGDATA, HA, partitionnement, performance, PITR. |
| SRE/Platform engineer | 2 | Installateurs, systemd, Kubernetes, monitoring, runbooks. |
| Backend engineers | 4-6 | Domain services, API, CLI, jobs, migrations. |
| Frontend engineers | 2-3 | React, Bootstrap 5, parité CLI/API/UI, UX. |
| Discovery/network engineers | 2-3 | Agents, protocoles, multisite, flux réseau. |
| Security engineer | 1-2 | LDAP/IPA, RBAC, Vault, audit, threat model. |
| QA automation engineers | 2-3 | Tests CI, intégration, perf, chaos, sécurité. |
| Technical writer | 1 | Docs install, runbooks, API, release notes. |

## Gouvernance de release

Chaque release doit produire trois vues :

1. **Vue produit** : capacités par édition, limites, compatibilité.
2. **Vue exploitation** : installateurs, services, stockage, backup, monitoring.
3. **Vue qualité** : tests, preuves, risques, go/no-go.

## Règles bloquantes

- Aucun livrable sans tests de conformité édition.
- Aucun installateur dans `src`.
- Aucun service `ancien service backend obsolète`.
- Aucun frontend connecté directement à PostgreSQL.
- Aucune migration exécutée par frontend ou agent.
- Aucun connecteur ITSM ne doit devenir un module ITSM intégré.
