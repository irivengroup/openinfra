## v0.29.85 — Traçabilité nomenclature DCIM et i18n web

- `REQ-00820` → `TST-WEB-119` → `TST-P14-DCIM-GENERATED-BUILDING-FLOORS` → migration `0040_dcim_floor_nomenclature.sql`.
- `REQ-00824` → `TST-WEB-123` → `EPIC-0807` → `TST-P08-WEB-I18N-FR-EN`.
- Code : `FloorNomenclature`, migration JSON, dépôt PostgreSQL, CLI/API/OpenAPI et sélecteurs DCIM.
- UI : `web/src/i18n.js`, copie runtime byte-identique, tests Node.js, tests web Python, validateurs frontend et vérificateur d’artefact.
- Runtime web : priorité source/installé du portail packagé sur `web/dist`, avec test de non-régression après build React.

## v0.29.84 — Traçabilité correctif CI DCIM et GitHub Actions

- Incident CI historique : le smoke modèle physique utilisait `F01` après une ancienne normalisation concaténée, remplacée en v0.29.85 par les codes locaux `L-01`, `L00`, `L01`.
- Correction : extraction du champ `floor` dans la sortie JSON de `define-room`, puis réutilisation dans les commandes DCIM suivantes.
- Correction similaire : smoke câblage/énergie aligné sur le même contrat canonique.
- CI : `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, dependency review et CodeQL déjà compatibles Node.js 24.
- Prévention : tests des workflows et gate de sécurité interdisant les anciens majors Node.js 20.
- CDC/roadmap : non modifiés ; aucune nouvelle recommandation n’impacte l’existant.

## v0.29.83 — Traçabilité résilience workers et agents Discovery

- Roadmap existante : P14 / `EPIC-1406` — tests crash worker/agent, reprise jobs, DLQ, idempotence et non-perte.
- Migration : `0039_discovery_job_resilience.sql`.
- Code : domaine des jobs, port Discovery, dépôts JSON/PostgreSQL, service applicatif, CLI, API HTTP, OpenAPI et portail web.
- Garanties : bail expirant, fencing monotone, réservation concurrente atomique, retry borné, DLQ, rejeu audité et terminaison idempotente.
- Tests : domaine, service, concurrence, reprise après crash, interfaces CLI/HTTP, portail, migrations et authentification collector.
- CDC/roadmap : non modifiés ; aucune nouvelle recommandation n’impacte l’existant.

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
