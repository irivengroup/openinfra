## v0.29.91 — Traçabilité conformité réseau

- Domaine : `network_config_compliance.py`.
- Application : `network_config_compliance_services.py`.
- Infrastructure : adaptateurs JSON/PostgreSQL et migration `0043_network_config_compliance.sql`.
- Interfaces : commandes `network-config`, six routes HTTP/OpenAPI et portail FR/EN.
- Roadmap : P15 / EPIC-1504 déjà planifié ; CDC et roadmap inchangés.

## v0.29.90 — Traçabilité certificats et PKI

- Roadmap existante : P15 / `EPIC-1503` — inventaire, chaînes, SAN, propriétaires, endpoints et alertes d'expiration.
- Domaine : `domain/certificate_pki.py` — matériau X.509, gouvernance, observations d'endpoints, hostname/SAN et états de santé.
- Application : `application/certificate_pki_services.py` — import, inventaire, retrait, observations idempotentes, évaluation bornée et audit.
- Infrastructure : `certificate_parser.py`, adaptateurs JSON/PostgreSQL et migration `0042_certificate_pki_inventory.sql`.
- Interfaces : sept commandes CLI, sept routes HTTP/OpenAPI et sept opérations web FR/EN.
- Sécurité : validation cryptographique des chaînes, refus des clés privées, permissions dédiées, isolation tenant et empreintes immuables.
- Tests : domaine, services, CLI, HTTP, portail, migration, row mapping PostgreSQL, CI, OpenAPI et packaging.
- CDC/roadmap : documents inchangés et non réémis ; l'epic et ses critères étaient déjà présents.

## v0.29.89 — Traçabilité matrice de flux

- Roadmap existante : P15 / `EPIC-1502` — matrice de flux déclarés et observés.
- Domaine : `domain/flow_matrix.py` — sélecteurs, protocoles, décisions, observations immuables et statuts de conformité.
- Application : `application/flow_matrix_services.py` — gouvernance, idempotence, comparaison bornée, pagination et audit.
- Persistance : adaptateurs JSON/PostgreSQL et migration `0041_flow_matrix.sql`, partitionnée et indexée par tenant.
- Interfaces : six commandes CLI, six routes HTTP/OpenAPI et six opérations web FR/EN.
- Sécurité : permissions `flow.read`/`flow.write`, rôles dédiés, isolation tenant et rejet des conflits d'idempotence.
- Tests : domaine, services, CLI, HTTP, portail, PostgreSQL, migration, OpenAPI, CI et packaging.
- CDC/roadmap : documents inchangés et non réémis ; l'epic et ses critères étaient déjà présents.

## v0.29.88 — Traçabilité accessibilité transversale

- CDC : `REQ-00789`, `REQ-00825`, `TST-WEB-090`, `TST-WEB-125`.
- Roadmap : P08 / `EPIC-0805`, `TST-P08-WEB-ACCESSIBLE-NAVIGATION`, `TST-P08-WEB-COMPACT-HEADER`.
- Code : portail React, runtime web packagé, moteur i18n partagé, feuille de style commune et workflow CI.
- Tests : lint JSX accessible, contrat DOM/CSS/ARIA Node.js, tests Python de parité, build Vite et validation frontend.
- Documentation : `docs/ui/WEB_ACCESSIBILITY.md`.

## v0.29.87 — Traçabilité ajustements header et mégamenu

- Exigences mises à jour : `REQ-00811` (mégamenu au survol/focus, clic de secours) et `REQ-00825` (hauteur initiale restaurée, recherche 50 % centrée, navigation compacte et états contrastés).
- Tests contractuels mis à jour : `TST-WEB-124`, `TST-WEB-125`, tests Node.js `responsive-navigation.test.mjs`, tests Python `test_responsive_navigation_contract.py` et `test_openinfra_web.py`.
- Roadmap réalignée sur `P08 / EPIC-0805` sans nouvel epic ni nouvelle migration.
- Parité stricte des assets `web/src/openinfra-theme.css` et `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`.

## v0.29.86 — Traçabilité navigation responsive web

- CDC : `REQ-00811` réalignée sur les trois modes de navigation et `REQ-00825` pour le header compact, les contrôles alignés et la hiérarchie des ombres.
- Roadmap : renforcement de `EPIC-0805` et ajout des validations `TST-P08-WEB-RESPONSIVE-NAVIGATION` et `TST-P08-WEB-COMPACT-HEADER`.
- Code : portail packagé `openinfra-web.js`, frontend React `main.jsx` et feuille de thème byte-identique.
- Garanties : sidebar uniquement sur écran large, mégamenu multicolonne intermédiaire, menu unique mobile, navigation complète, fermeture par `Échap`, backdrop et boutons, cibles tactiles de 44 px.
- Tests : Node.js, contrat Python, validation statique frontend et build Vite.

## v0.29.86 — Traçabilité graphe de dépendances RSOT

- Roadmap existante : P15 / `EPIC-1501` — graphe applications, services, réseau, stockage, DCIM et alimentation.
- Code : `domain/dependency.py`, `application/dependency_graph_services.py`, conteneur applicatif, CLI et API HTTP.
- Interfaces : commandes `graph traverse`, `graph impact`, `graph path`, routes `/api/v1/graph/*`, OpenAPI runtime et portail FR/EN.
- Garanties : lecture seule RSOT, isolation tenant, authentification `rsot.read`, parcours borné, cycles maîtrisés, historique `as_of`, résultats déterministes et audit.
- Tests : domaine, service, CLI, HTTP, portail, sécurité, OpenAPI et non-régression.
- Base de données : aucune migration ; réutilisation des objets et relations RSOT historisés.
- CDC/roadmap : EPIC-1501 était déjà planifié ; les documents sont néanmoins réémis en v0.29.86 pour la recommandation responsive distincte portée par `REQ-00811`, `REQ-00825` et `EPIC-0805`.

## v0.29.85 — Traçabilité nomenclature DCIM et i18n web

- `REQ-00820` → `TST-WEB-119` → `TST-P14-DCIM-GENERATED-BUILDING-FLOORS` → migration `0040_dcim_floor_nomenclature.sql`.
- `REQ-00824` → `TST-WEB-123` → `EPIC-0807` → `TST-P08-WEB-I18N-FR-EN`.
- Code : `FloorNomenclature`, migration JSON, dépôt PostgreSQL, CLI/API/OpenAPI et sélecteurs DCIM.
- UI : `web/src/i18n.js`, copie runtime byte-identique, tests Node.js, tests web Python, validateurs frontend et vérificateur d’artefact.
- Runtime web : priorité source/installé du portail packagé sur `web/dist`, avec test de non-régression après build React.

## v0.29.84 — Traçabilité correctif CI DCIM et GitHub Actions

- Incident CI historique : le smoke modèle physique utilisait `F01` après une ancienne normalisation concaténée, remplacée en v0.29.86 par les codes locaux `L-01`, `L00`, `L01`.
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
