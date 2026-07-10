## v4.8.1 / OpenInfra 0.29.85 — Nomenclature étages et i18n web

- REQ-00820 réalignée sur les codes d’étage locaux `L-01`, `L00`, `L01` avec migration et alias historiques.
- Ajout de REQ-00824 pour l’internationalisation complète FR/EN du portail, la détection navigateur et le fallback anglais.
- Ajout de TST-WEB-123 et mise à jour de la traçabilité.

### Validation v0.29.82 — Réconciliation Discovery multisource gouvernée

Ajout de `REQ-00823` et `TST-WEB-122` : preuves immuables et hashées, scoring confiance/fraîcheur/complétude déterministe, conflits par chemin d’attribut, résolution complète justifiée, audit sans payload, pagination et migration PostgreSQL `0038_discovery_multisource_reconciliation.sql`, sans écriture RSOT directe.

## v0.29.72 — DCIM dépendances CRUD topologiques

- Ajout `REQ-00813` pour couvrir le cycle de vie CRUD des bâtiments, étages, salles et zones DCIM.
- Ajout `TST-WEB-112` pour valider services, CLI, API, OpenAPI, discovery, web et cascades non destructives.
- Mise à jour de la roadmap avec `TST-P10-DCIM-DEPENDENCY-CRUD`.

## v0.29.71 — compatibilité CLI/CI des commandes édition

- Ajout `REQ-00812` pour rendre homogènes les options backend des commandes CLI d'administration des éditions.
- Ajout `TST-CLI-111` afin de verrouiller `openinfra edition feature-check --data ...` dans les smoke tests CI.
- Mise à jour de la roadmap avec `TST-P08-CLI-EDITION-DATA-COMPAT`.
### Validation v0.29.81 — Profils Discovery virtualisation, Kubernetes et cloud

Ajout de `REQ-00822` et `TST-WEB-121` : OpenInfra référence les profils de découverte VMware, Proxmox, Hyper-V, Kubernetes, AWS, Azure, GCP et OpenStack avec secrets `vault://` masqués, endpoint HTTPS lorsque nécessaire, limites de débit/concurrence et migration `0037_discovery_integration_profiles.sql`.
