## v0.29.82 — Traçabilité réconciliation Discovery multisource

- CDC : `REQ-00823`, `TST-WEB-122`.
- Roadmap : P14 / `EPIC-1405`, `TST-P14-DISCOVERY-MULTISOURCE-RECONCILIATION`.
- Migration : `0038_discovery_multisource_reconciliation.sql`.
- Code : domaine Discovery, ports applicatifs, services, dépôts JSON/PostgreSQL, CLI, API HTTP, OpenAPI et portail web.
- Garanties : preuve immuable, scoring déterministe, conflit explicite, résolution justifiée, audit et `rsot_write_executed=false`.
- Tests : domaine, service, persistance JSON, CLI, API, web, migration et non-régression RSOT.

## v0.29.79 — Traçabilité profils Discovery

- CDC : `REQ-00819`, `TST-WEB-118`.
- Roadmap : `TST-P14-DISCOVERY-PROTOCOL-PROFILES`.
- Migration : `0034_discovery_protocol_profiles.sql`.
- Tests : domaine Discovery, service, CLI, API HTTP, politiques migrations, Ruff et Bandit.
