### v0.29.47 — openinfra-web badge édition header principal

- Déplace l’affichage de l’édition runtime juste après le logo OpenInfra dans la première barre du header.
- Retire l’indication visible du mode d’authentification de la titlebar, sans modifier le contrat de configuration backend `/config.json`.
- Ajoute un style `openinfra-edition-badge` à fond fuchsia dégradé, sans modifier le padding, la taille de police ou le gabarit Bootstrap du badge.
- Étend le validateur frontend et les tests d’intégration web pour verrouiller ce comportement UI.

### v0.29.46 — openinfra-web accessibilité navigation/recherche

- Ajout d’un skip-link `Aller au contenu principal` vers `#openinfra-main-content` afin de permettre aux opérateurs clavier et lecteurs d’écran de contourner le double header fixe et la sidebar.
- Ajout des états `aria-current` sur la navigation header/sidebar, des régions accordéon `aria-controls`/`aria-labelledby` et d’un `main` focalisable après sélection depuis la recherche globale.
- La recherche globale expose désormais `role="combobox"`, `role="listbox"`, `role="option"`, `aria-live` et conserve le fallback backend/local sans erreur brute.
- Ajout de styles `focus-visible` homogènes sur header, sidebar, résultats de recherche et boutons Swagger/ReDoc.
- Tests d’intégration et validateur frontend étendus pour verrouiller ces contrats d’accessibilité.


## 0.29.45 - 2026-07-07

- ITAM devient un composant web de premier niveau visible comme les autres domaines dans le Dashboard, le header, le panneau latéral et la recherche globale.
- Ajout d’une icône SVG pleine `asset`, dédiée à ITAM, homogène avec les pictogrammes opaques des autres composants.
- La recherche globale backend agrège aussi ITAM via une recherche exacte de profil support par numéro d’actif, sans fuite de données entre tenants ni permissions.
- Les boutons `Swagger` et `ReDoc` du double header sont réduits de moitié et conservent leurs liens backend API réels.
- Conservation de la correction sidebar v0.29.44 : les accordéons restent dans le flux vertical, repoussent les composants inférieurs et scrollent sans masquer les entrées.

## 0.29.42 - 2026-07-07

- Le double header conserve sa position fixe mais porte maintenant une ombre `--openinfra-header-shadow` plus prononcée que les ombres de contenu allégées.
- Le scroll de la page démarre exactement sous le header sur toute la largeur via `scroll-padding-top`, `--openinfra-fixed-header-height` et le calcul runtime de hauteur.
- La barre de recherche ne porte plus une ombre concurrente : l’effet de séparation est appliqué au header complet pour éviter un chevauchement visuel.
- Les validations frontend et tests web verrouillent la hiérarchie d’ombres header/contenu et l’offset de scroll.

## 0.29.41 - 2026-07-07

- Les boutons `Swagger` et `ReDoc` du double header lisent désormais les liens `apiDocumentation` de `/config.json` et ouvrent les routes backend API réelles.
- `openinfra-web` proxyfie `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml` vers `openinfra-api`, avec CSP dédiée aux viewers Swagger/ReDoc.
- Ajout de `OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL` pour les déploiements où le portail web et l’API sont publiés sur des origines séparées.
- Les camemberts du Dashboard restaurent la palette initiale plus lisible : bleu action pour les lectures et vert pour les mutations.
- Le duo bleu nuit/fuchsia introduit en 0.29.39 est retiré du gradient et des légendes, conformément au retour UX signalant une fatigue visuelle.
- Les tests et validations frontend verrouillent la palette restaurée et empêchent le retour du fuchsia dans les camemberts.
- Le pictogramme ITRM abandonne l’icône tableau et utilise une icône de référentiel/référence pleine et opaque afin de rester homogène avec les autres composants.
- Le double header est désormais fixe en haut de page ; le scroll s’applique au contenu sous-jacent avec offset CSS/JS dynamique.

## 0.29.39 - 2026-07-07

- La recherche globale du double header n’expose plus l’erreur navigateur brute `Failed to fetch` : l’UI affiche un message fonctionnel générique et conserve le fallback local groupé par composant.
- Le frontend construit l’URL de recherche globale depuis `apiBaseUrl` afin de respecter `OPENINFRA_WEB_PUBLIC_API_BASE_URL` au lieu de figer `/api`.

## 0.29.38 - 2026-07-07

- Ajout d’un service applicatif `GlobalSearchService` agrégeant les résultats ITRM, IPAM et Discovery.
- Ajout de l’endpoint `GET /api/v1/search/global` avec résultats groupés par composant, limites validées et sécurité par jeton.
- Ajout de la commande `openinfra search global` pour utiliser la recherche globale hors UI.
- Le double header web utilise le backend quand il est disponible et conserve le fallback local de recherche d’opérations.
- Ajout de tests service/API/frontend et de garde-fous de validation frontend.

## 0.29.37 - 2026-07-07

- Added a themed second header bar dedicated to global search, centered on the page and sized to half of the available width on desktop.
- Added a magnifier SVG inside the global search field and grouped result rendering by OpenInfra component when matches span multiple modules.
- Added Swagger and ReDoc actions in the second header bar without reintroducing Login/Sign-up or the old local operations search.
- Removed the residual permanent typed-form guidance text that had previously been displayed inside default alert blocks.
- Extended frontend validation and web integration tests to lock global search grouping, documentation actions and the absence of permanent alert-derived messages.

## 0.29.36 - 2026-07-07

- Removed the default informational `alert-info` block from openinfra-web component pages.
- Kept the typed-form guidance as neutral muted text so operators still receive context without a false status/event signal.
- Preserved contextual alerts: warnings/errors remain visible for characterized problems and the success alert remains conditional on an executed form submission.
- Extended frontend validation and web integration tests to forbid `alert alert-info` and `role="note"` in runtime UI assets.

## 0.29.35 - 2026-07-07

- Reduced content block shadows in `openinfra-web` for a lighter, more fluid visual hierarchy.
- Added content-specific CSS variables `--openinfra-content-shadow` and `--openinfra-content-shadow-hover` so cards, titlebars, metrics and component summaries no longer reuse the stronger navigation shadow token.
- Preserved header and sidebar visual effects, as requested, to keep navigation emphasis unchanged.
- Extended frontend validation and web integration tests to lock the lighter content shadow contract.

## 0.29.34 - 2026-07-07

- Added `openinfra discovery proxy-enroll-verify` for Enterprise-only local validation of generated proxy enrollment configs.
- Added schema, backend result and POSIX permission checks for proxy enrollment config files.
- Added `--allow-partial` to report partial HA backend enrollment as a warning while preserving schema errors.
- Fixed duplicate JSON output from `openinfra discovery job-authorize`.
- Shortened the web home title to `Dashboard`.
- Scoped home metrics and component statistics to the Dashboard page only, keeping component pages focused on their selected operation form.

## 0.29.33 - 2026-07-07

- Added Enterprise-only direct proxy enrollment from CLI to one or more OpenInfra backends.
- Added `POST /api/v1/discovery/proxy-enrollments` for backend-side proxy enrollment with edition gate enforcement.
- Added `openinfra discovery proxy-enroll-local` for local backend-store enrollment.
- Added discovery collector kinds `site-proxy`, `network-proxy` and `datacenter-proxy` across domain, API, CLI and documentation.
- Added regression tests for Enterprise acceptance, Pro/Lite rejection, CLI remote enrollment, HTTP enrollment and proxy kind validation.
- Replaced the basic Bootstrap color layer in `openinfra-web` with a premium navy/blue/cyan theme applied through Bootstrap 5-compatible CSS overrides, preserving the existing page structure.
- Added frontend validator and web integration checks for the new theme variables, button states, focus rings and runtime CSS assets.

## 0.29.32 - 2026-07-07

- Added P11/IPAM operational topology through `GET /api/v1/ipam/topology` and `openinfra ipam topology`.
- Consolidated VRF, aggregates, prefixes, ranges, address records, reservations, VLAN groups, VLANs, VXLAN VNIs, ASNs, BGP peers, DNS observations and DHCP leases into a deterministic nodes/edges graph.
- Added topology integrity reporting to detect orphan graph edges before API/UI/automation consumption.
- Exposed the topology operation in the dashboard and API discovery/OpenAPI documentation.
- Updated CDC, roadmap, frontend validators and regression tests for P11 IPAM topology parity.

## 0.29.31 - 2026-07-07

- Added P11/IPAM Enterprise++ dashboard parity for VRF, aggregates, prefixes, ranges, address records, VLAN groups, VXLAN VNIs, VLANs, ASNs, BGP peers, DNS/DHCP observations, DDI preview, reservation wizard, allocation, capacity, network bindings and conflict detection.
- Added IPAM endpoints to the API discovery document so operators and automation can discover the REST contracts without reading OpenAPI manually.
- Extended frontend validation and web regression tests to prevent the IPAM dashboard from drifting away from real `/api/v1/ipam/*` backend contracts.
- Updated CDC, roadmap and UI documentation for P11 IPAM Enterprise++ operator workflows.

## 0.29.30 - 2026-07-07

- Added the initial DCIM room digital twin through `GET /api/v1/dcim/digital-twin` and `openinfra dcim digital-twin`.
- Consolidated room plan, racks, equipment, patch panels, ports, cables, power circuits, reservations, energy/cooling capacity, rack elevations and integrity checks in a single `dcim_digital_twin` payload.
- Added the `Jumeau numérique salle` dashboard operation and API discovery/OpenAPI documentation for the same backend contract.
- Reused existing DCIM services and repositories without introducing parallel storage or duplicating rack, cabling, energy or cooling invariants.
- Updated CDC, roadmap, frontend validators and regression tests for P10 digital twin parity.

## 0.29.29 - 2026-07-07

- Added DCIM power and cooling dashboard operations for power devices, power circuits, cooling zones, power reservations and rack energy/cooling capacity reports.
- Exposed the existing DCIM environment backend contracts in the API discovery document and OpenAPI specification.
- Extended frontend validation and web regression tests so energy/cooling UI parity cannot drift away from the HTTP API.
- Hardened ITRM category/type selectors so the dashboard displays human-readable labels while keeping normalized values internal to API payloads.
- Removed obsolete `physical-server` and `disk` resource types from the taxonomy; server defaults now start at `rack-server` and storage keeps explicit media types such as `hdd`, `ssd` and `nvme-drive`.
- Updated CDC, roadmap and documentation for P10 energy/cooling dashboard parity and ITRM taxonomy UX hardening.

## 0.29.28 - 2026-07-07

- Added DCIM cabling dashboard operations for patch panels, ports and cable connections using the existing `/api/v1/dcim/patch-panels`, `/api/v1/dcim/ports` and `/api/v1/dcim/cables` backend contracts.
- Added explicit operator fields for cable endpoint A/B, connector, medium, status, path segments, length and label, with select lists matching domain enumerations.
- Extended frontend validation and web regression tests so the cabling UI cannot drift away from the HTTP API.
- Updated CDC, roadmap and documentation for P10 cabling dashboard parity.

## 0.29.27 - 2026-07-07

- Added the `Élévation rack` dashboard operation for `GET /api/v1/dcim/rack-elevation`, including rack face and render format selection.
- Added render format selection to the `Plan de salle` dashboard operation so operators can request JSON, SVG or HTML wrappers from the existing DCIM visualization API.
- Tightened DCIM dashboard query fields for rack capacity, room plan, rack elevation and cable trace with required business inputs.
- Updated frontend validation, web regression tests, documentation, CDC and roadmap for P10 rack elevation UI parity.

## 0.29.26 - 2026-07-07

- Added `POST /api/v1/dcim/locations` to locate or relocate DCIM equipment through the existing location service.
- Added serialized equipment/location payloads including site, building, floor, room, row, column, zone, rack, face, U position, height and X/Y/Z coordinates.
- Added the `dcim.locations` API discovery contract and OpenAPI documentation.
- Added a dashboard form `Localiser un équipement` for the DCIM location contract, served by the runtime web assets and React source catalog.
- Updated CDC, roadmap, frontend validation and regression tests for DCIM equipment location API/UI parity.

## 0.29.25 - 2026-07-06

- Added a complete ITRM datacenter resource taxonomy with category-to-type mapping.
- Added `GET /api/v1/itrm/resource-taxonomy` and `openinfra itrm resource-taxonomy`.
- Added category/type validation to ITRM upsert and reconciliation commands.
- Persisted normalized `resource_category` and `resource_type` in ITRM object attributes and public payloads.
- Updated the web dashboard so selecting a category dynamically filters compatible resource types.
- Generalized dependent select fields through reusable `optionsByField` form metadata.
- Updated OpenAPI, CDC, roadmap, documentation and regression tests.

## 0.29.24 - 2026-07-06

- Added governed ITRM object reconciliation with deterministic dry-run and optional apply.
- Added `openinfra itrm reconcile-object` and `POST /api/v1/itrm/reconcile-object`.
- Reconciliation returns accepted/applied state, changed paths, conflicts, stale rules, planned version and resulting attributes.
- Rejected non-authoritative updates are not applied and are audit-traced through `itrm.reconciliation.plan`; accepted applied updates are traced through `itrm.reconciliation.apply`.
- Updated dashboard operation catalog, OpenAPI, CDC, roadmap and regression tests.

## 0.29.23 - 2026-07-06

- Added ITRM object time-travel retrieval through `get-object-as-of` and `/api/v1/itrm/object-as-of`.
- Added temporal relation filtering with `as_of` in CLI, API, JSON store and PostgreSQL repository.
- Added object-scoped audit retrieval through `list-object-audit`, `/api/v1/itrm/object-audit`, and `target_id` audit filtering.
- Added web dashboard operations for ITRM as-of retrieval and object audit.
- Updated OpenAPI, CDC, roadmap and regression tests.

## 0.29.22 - 2026-07-06

- Ajoute le endpoint `openinfra-web` `/status` pour diagnostiquer le trust BFF server-side, l’état des formulaires protégés et la configuration bearer backend sans exposer de secret.
- Assainit toute erreur backend brute `missing bearer token` propagée par l’API : le navigateur reçoit une erreur BFF explicite, sans message technique backend.
- Affiche dans le dashboard un indicateur discret `Formulaires protégés` alimenté par `/status`.
- Renforce `validate_frontend.py` et les tests d’intégration web sur `/status`, non-exposition du bearer et assainissement des erreurs d’authentification.
- Conserve l’aération responsive de la titlebar dashboard introduite en v0.29.21.

## 0.29.21 - 2026-07-06

- Aère la titlebar du dashboard `openinfra-web` avec un espacement vertical responsive autour du titre et du sous-titre.
- Synchronise les sources React, les assets runtime CSS et les validateurs frontend pour verrouiller le rendu servi.
- Ajoute une régression web empêchant le retour d’une titlebar trop compacte.
- Corrige le chaînage BFF authentifié : un `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` vide bascule sur `OPENINFRA_BOOTSTRAP_TOKEN`, et le navigateur ne reçoit plus d’erreur brute `missing bearer token`.

## 0.29.20 - 2026-07-06

- Fixed openinfra-web form submission contracts by aligning dashboard operations with backend `/api/v1/*` routes through the server-side proxy.
- Added optional server-side backend bearer token injection for openinfra-web so authenticated backend forms remain usable without exposing tokens in the browser.
- Increased dashboard pie charts with responsive sizing using CSS `clamp()` and viewport-aware layout.

## 0.29.19 - 2026-07-06

- Renommage transversal du composant public `ITRM` (`IT Ressources Management`) comme successeur du composant inventaire précédent.
- Promotion des contrats primaires `openinfra itrm *`, `/api/v1/itrm/*`, rôles `itrm:*` et permissions `itrm.*`.
- Conservation des alias compatibles `openinfra ri *`, `/api/v1/ri/*`, `openinfra sot *`, `/api/v1/sot/*`, `ri:*` et `sot:*`.
- Mise à jour du dashboard, des assets runtime, du catalogue frontend, des tests HTTP/CLI, du smoke runtime, de l’OpenAPI, du CDC et de la roadmap.
- Suppression de l’alerte permanente `Backend prêt` sur l’accueil : l’état runtime reste en sidebar, les alertes visibles sont réservées aux erreurs et aux soumissions de formulaire.

## 0.29.18 - 2026-07-06

- `openinfra-web` enrichit le dashboard d’accueil avec une vue statistiques par composant.
- Ajout de cartes ITRM, IPAM, DCIM, Discovery et Sécurité avec métriques opérations/champs/mutations et camemberts lecture/mutation.
- Renforcement du validateur frontend et des tests d’intégration sur les fragments `Statistiques des composants OpenInfra`, `openinfra-component-card` et `openinfra-pie-chart`.
- CDC v4.8.1 et roadmap v2 alignés avec l’exigence de statistiques d’accueil par composant.

## 0.29.17 - 2026-07-06

- `openinfra-web` retire le second bandeau Bootstrap de recherche/actions demandé.
- Suppression runtime de `openinfra-search`, `openinfra-login`, `openinfra-signup`, `Login` et `Sign-up` dans le header web.
- Conservation du header sombre principal Bootstrap 5 et de la navigation opérationnelle par accordéons latéraux.
- CDC v4.8.1 mis à jour avec `REQ-00748` et `TST-WEB-051`.

## 0.29.16 - 2026-07-05

- `openinfra-web` adopte le thème Bootstrap 5 Dashboard avec header principal unique adapté aux domaines OpenInfra.
- Ajout de `assets/bootstrap.min.css` dans le domaine présentation/rendering pour un runtime sans CDN.
- Validation frontend renforcée : header, sidebar, recherche, domaines ITRM/IPAM/DCIM/Discovery/Sécurité et non-exposition des secrets.
- CDC v4.8.1 mis à jour avec `REQ-00746` et `TST-WEB-049`.

## 0.29.13 - 2026-07-05

- Renomme le domaine public `Source of Truth/SOT` en `IT Ressources Management/ITRM` dans le CDC, la roadmap, OpenAPI, runbooks, CI, documentation, dashboard et smoke tests.
- Ajoute les contrats primaires `openinfra itrm *`, `/api/v1/itrm/*`, rôles `itrm:reader`, `itrm:operator`, `itrm:governance-admin` et permissions `itrm.*`.
- Conserve les alias de compatibilité `openinfra sot *`, `/api/v1/sot/*` et `sot:*` afin d'éviter toute régression opérationnelle.
- Corrige la sémantique Discovery : un agent est exclusivement un proxy collector Enterprise en topologie étoile ; Lite et Pro exécutent la collecte depuis leurs backends servers.
- Déplace les assets runtime web de `src/openinfra/web_static` vers `src/openinfra/interfaces/rendering/static`, domaine présentation/rendering.
- Transforme `openinfra-web` en dashboard de pilotage API-only couvrant ITRM, IPAM, DCIM, Discovery, sécurité/RBAC, audit, import/export et runtime.
- Met à jour tests, gates, validation frontend, installateur, CDC et roadmap pour verrouiller ces contrats.

## 0.29.11 - 2026-07-05

- Correction du modèle P07/P08 : LDAP/IPA opérateur est désormais porté par le frontend web Pro/Enterprise, pas par le backend server.
- Le backend conserve un contrat API-only : validation de jetons applicatifs, RBAC OpenInfra effectif et audit des permissions.
- Ajout de la configuration runtime canonique `/opt/openinfra/config/openinfra.conf`, accessible via `/etc/openinfra/openinfra.conf` grâce au symlink `/etc/openinfra -> /opt/openinfra/config`.
- Matérialisation post-installation des paramètres utiles issus de `install.ini` et `.env` dans `openinfra.conf`, sans exposer de secrets en clair.
- Ajout du verrou masqué `/opt/openinfra/config/.openinfra-installed.lock` pour empêcher les installations multiples non contrôlées.
- Déplacement du chemin runtime des migrations backend vers `/opt/openinfra/share/migrations/postgresql` ; le dossier `installers/` reste une source de bootstrap, pas une dépendance runtime.
- Durcissement des échanges frontend-backend, agent-backend et backend-backend : TLS 1.3 et mTLS obligatoires hors Lite.
- Mise à jour du CDC v4.8.1 : ADR, volumes, matrices exigences/tests/traçabilité, schéma install.ini, règles systemd, runbooks et templates install.ini.
- Déplacement des dépendances `ldap3` vers les scopes web Pro/Enterprise.
- Ajout de tests de non-régression sur runtime config, symlink `/etc/openinfra`, lock d'installation, politique backend API-only et sécurité `[security]`.

## 0.29.10 - 2026-07-05

- Livraison P07 avant reprise Discovery : authentification locale/LDAP/IPA, RBAC externe mappé OpenInfra et audit des permissions.
- Lite reste strictement en mode `standard` local ; LDAP/IPA est rejeté par le backend et par les validations installateur.
- Pro/Enterprise autorisent LDAP/IPA uniquement sur le scope backend `server`; `web` et `agent` passent exclusivement par le backend.
- Ajout du domaine `openinfra.domain.authentication` : modes d'authentification, configuration LDAP/IPA sécurisée, mappings groupes externes → rôles OpenInfra et identité authentifiée externe.
- Ajout du service applicatif `ExternalAuthenticationService` avec émission de token OpenInfra, création/mise à jour utilisateur, groupes RBAC et audit `auth.external.login`.
- Ajout de l'adaptateur LDAP/IPA optionnel, chargé dynamiquement via `ldap3`, avec `ldaps://`, TLS obligatoire, bind de service optionnel, recherche utilisateur, validation du mot de passe et résolution des groupes.
- Ajout de `openinfra auth policy` pour valider les politiques d'authentification par édition sans exposer de secret en clair.
- Ajout de la migration `0025_authentication_ldap_ipa_rbac.sql` pour configurations d'authentification, mappings de groupes et audit permissionnel partitionné.
- Ajout des requirements LDAP/IPA de production uniquement sur les scopes backend Pro/Enterprise et de l'extra Python `openinfra[ldap]`.
- Renforcement des tests de non-régression sur les secrets, LDAP/IPA, RBAC, installateurs et migrations.

## 0.29.9 - 2026-07-05

- Correctif runtime bloquant sur la migration `0024_postgresql_ha_backup_registry.sql`.
- Correction de la clé primaire de `postgresql_backup_runs`, partitionnée par `started_at` : la contrainte est désormais `PRIMARY KEY (tenant_id, started_at, id)`, conformément aux règles PostgreSQL sur les tables partitionnées.
- Durcissement du validateur de migrations : les contraintes `PRIMARY KEY` / `UNIQUE` et les index uniques sur tables partitionnées doivent inclure toutes les colonnes de partitionnement.
- Ajout de tests de non-régression pour empêcher la réintroduction de contraintes uniques incompatibles avec les partitions PostgreSQL.
- P07 est resté suspendu dans cette version : priorité donnée au correctif runtime de migration.

## 0.29.8 - 2026-07-05

- Livraison P06 avant reprise Discovery : PostgreSQL HA/PITR, synchronisation quasi temps réel et sauvegardes.
- Ajout du modèle interne `InstallerPostgreSQLHaPlan` pour les scopes backend/all-in-one.
- Activation automatique du mode cluster à synchronisation quasi temps réel lorsque `identity.peer_nodes` est renseigné.
- Ajout du rendu interne `/etc/openinfra/postgresql-ha.json` et de l'include PostgreSQL `/data/openinfra/conf.d/openinfra-ha.conf`.
- Préparation des répertoires `/data/openinfra/pitr` et `/data/openinfra/backups` avec ownership PostgreSQL.
- Ajout de la migration `0024_postgresql_ha_backup_registry.sql` pour noeuds HA, backups et événements de failover.
- Ajout de `openinfra database ha-plan` pour auditer le plan HA/PITR dérivé d'un installateur.
- Maintien des `install.ini` minimalistes : aucun port, secret de réplication ou paramètre bas niveau exposé.

## 0.29.6 - 2026-07-05

- P05 : ajout du plan LVM natif pour le filesystem applicatif `/opt/openinfra/` sur tous les scopes installés, y compris `enterprise/agent`.
- Ajout du plan LVM PostgreSQL `/data/openinfra/`, du symlink `/opt/openinfra/data`, de l'override PGDATA systemd et de la résolution/création du compte système PostgreSQL pour les scopes backend.
- Conservation de l'exclusion agent sur PostgreSQL, PGDATA, symlink data et migrations backend.
- Mise à jour des tests, gates, CDC et roadmap v2 pour supprimer l'ancienne exception FS applicatif agent.

## 0.29.5 - 2026-07-05

- Durcissement P03/P04 du moteur installateur autonome par scope.
- Ajout des prérequis OS-aware dans les plans d'installation.
- Ajout d'un rollback transactionnel automatique pour les fichiers et dossiers remplacés.
- Ajout des modes `--verify-only`, `--migrate-only` et `--rollback` aux installateurs `installers/setup/**/install.py`.
- Création du virtualenv applicatif `/opt/openinfra/venv` et installation des requirements de production par scope.
- Démarrage effectif des unités systemd par `systemctl restart` après installation réussie.

## 0.29.4 - 2026-07-05

- Transformation de `installers/` en point d’entrée autonome par scope avec un `install.py` exécutable pour Lite, Pro server/web et Enterprise server/web/agent.
- Réorganisation des configurations sous `installers/setup/...` et suppression/interdiction des anciens dossiers racine `installers/lite`, `installers/pro` et `installers/enterprise`.
- Déploiement autonome de `src/`, du `pyproject.toml`, des requirements de production et des unités systemd rendues par l’installateur.
- Déploiement des migrations PostgreSQL uniquement pour les scopes backend/all-in-one depuis `installers/migrations/postgresql`.
- Conservation de `enterprise` comme nom canonique du dossier Enterprise.
- Ajout de tests et gates anti-régression sur l’arborescence `installers/setup` et sur l’absence des anciens dossiers.

## 0.29.3 - 2026-07-05

- Clarification de la politique filesystem applicatif : `/opt/openinfra` reste géré par l’installateur pour les scopes applicatifs, conformément au CDC, mais pas pour l’agent Enterprise.
- Ajout du flag interne `managed_application_filesystem` dans les politiques installateur.
- `enterprise/agent` conserve maintenant le FS applicatif CDC `/opt/openinfra`, tout en restant sans stockage PostgreSQL, sans PGDATA et sans migration backend.
- Durcissement des tests et de la validation d’alignement pour bloquer toute réintroduction de FS/LVM sur le scope agent.
- Mise à jour CDC, runbooks, architecture et traçabilité.

## 0.29.2 - 2026-07-05

- Suppression définitive du dossier racine `migrations/` : la source unique des migrations backend est `installers/migrations/postgresql`.
- Correction du catalogue PostgreSQL : `PostgreSQLMigrationCatalog.from_project_root()` résout désormais `installers/migrations/postgresql`.
- Correction Docker : l’image runtime copie `installers/` au lieu de l’ancien dossier `migrations/`.
- Durcissement des unités systemd rendues par l’installateur : capacités Linux supprimées, `PrivateDevices`, protections noyau/cgroups, restriction SUID/temps réel et architecture syscall native.
- Ajout d’un plan de déploiement PostgreSQL OS-aware côté installateur backend/all-in-one : détection, installation paquetaire si absent, activation, démarrage, vérification readiness, PGDATA et migrations.
- Renforcement des quality gates : interdiction de `deploy/` et `migrations/` à la racine du projet.

## 0.29.1 - 2026-07-05

- Correctif d'alignement installateurs/CDC après v0.29.0, sans reprise Discovery.
- Suppression du dossier `deploy/` : les unités `openinfra.service`, `openinfra-web.service` et `openinfra-agent.service` sont rendues par l'installateur.
- Refonte des `install.ini` pour supprimer `edition`, `scope`, `service`, `operations`, `central_endpoint`, `network`, `mountpoint`, `owner`, `group` et ports internes.
- Lite `all-in-one` réduit à la seule section `[storage]`; Pro/Enterprise `server`, `web` et `agent` disposent uniquement des sections nécessaires.
- Ajout de `installers/migrations/postgresql` pour embarquer toutes les migrations backend avec les installateurs.
- Ajout de `installers/requirements` avec dépendances de production séparées par scope et sans outil dev/CI.
- Ajout de `openinfra installer render-systemd` et contrôle quality gate associé.
- Mise à jour CDC v4.8.1 : configuration `install.ini`, matrices sections/scopes/defaults et runbook exploitation.

## 0.29.0 - 2026-07-05

- Roadmap v2 : traitement prioritaire de la dette P02 avant reprise de Discovery.
- Ajout du domaine `openinfra.domain.editions` : éditions Lite, Pro, Enterprise, capabilities et quotas contractualisés.
- Ajout du service applicatif `EditionRuntimeGuard` et du service de requête `EditionQueryService` pour appliquer les gates et quotas côté backend.
- Ajout du port `RuntimeUsageRepository` et des adaptateurs JSON/PostgreSQL de comptage runtime.
- Verrouillage backend des collectors Discovery : la capability `distributed_discovery_agents` est réservée à Enterprise ; Lite/Pro rejettent register, heartbeat, job-authorize, disable et list avant persistance.
- Application des quotas Lite/Pro aux utilisateurs IAM, aux ressources IP/DNS, aux subnets/VLAN et aux équipements localisés.
- Ajout de `openinfra edition list`, `feature-check` et `quota-check`; ajout de `OPENINFRA_EDITION` et `openinfra-api --edition` pour l'API.
- Mise à jour des tests de non-régression P02 avec couverture globale `>= 98 %`.

## 0.28.1 - 2026-07-04

- Correctif de réalignement programme sur le CDC `OpenInfra-CDC-SFG-STG-v4.8.1` et la roadmap `OpenInfra-Roadmap-Developpement-v2`, sans nouveau jalon Discovery.
- Intégration des nouveaux référentiels contractuels dans `docs/specifications/` et bascule des validations vers le CDC v4.8.1.
- Ajout du validateur installateurs `InstallerConfigValidator`, des commandes `openinfra installer validate` et `openinfra installer dry-run`, et des scripts `validate_autonomous_installer.py` / `validate_enterprise_alignment.py`.
- Ajout des configurations `installers/<edition>/<scope>/config/install.ini` pour Lite all-in-one, Pro server/web et Enterprise server/web/agent.
- Alignement des services systemd sur le contrat v4.8.1 : service backend canonique `openinfra.service`, rejet de l'ancien `openinfra-api.service`, préparation `openinfra-web.service` et `openinfra-agent.service` via les profils installateurs.
- Alignement stockage installateur : application `/opt/openinfra/`, données PostgreSQL `/data/openinfra/`, symlink `/opt/openinfra/data`, tailles LVM Lite `2GB`, Pro `100GB`, Enterprise `1TB`, propriétaire logique `openinfra`.
- Renforcement de `security_gate.py` pour accepter uniquement les références de secrets (`env:`, `vault://`, `sops://`, `file://`, `kms://`) dans les fichiers `install.ini`; aucun secret en clair n'est accepté.
- Ajout de tests de non-régression sur l'alignement CDC/roadmap, les installateurs, la CLI installateur et les guards CI.

## 0.28.0 - 2026-07-04

- Roadmap : P07 / EPIC-0701 — Registry collectors et identité forte.
- Ajout du domaine Discovery : `CollectorIdentity`, `DiscoveryCollector`, `DiscoveryScope`, `CollectorKind`, `CollectorStatus` et `DiscoveryJobAuthorization`.
- Ajout d'une identité forte basée sur l'empreinte SHA-256 du certificat mTLS, avec normalisation stricte et rejet des empreintes invalides.
- Ajout des références Vault `vault://...` pour les secrets collectors ; aucun secret collector n'est stocké en clair dans l'état JSON ou PostgreSQL.
- Ajout du service applicatif `DiscoveryCollectorService` : enregistrement, heartbeat, liste, désactivation et autorisation/rejet de jobs.
- Ajout des ports et adaptateurs `DiscoveryRepository`, `JsonDiscoveryRepository` et `PostgreSQLDiscoveryRepository`.
- Ajout de la migration PostgreSQL `0023_discovery_collector_registry.sql`, partitionnée par hash du tenant, avec contraintes d'identité, scopes JSONB et index opérationnels.
- Ajout des commandes `openinfra discovery collector-register`, `collector-heartbeat`, `job-authorize`, `collector-disable` et `collector-list`.
- Ajout des endpoints `POST /api/v1/discovery/collectors`, `GET /api/v1/discovery/collectors`, `POST /api/v1/discovery/collectors/heartbeat`, `POST /api/v1/discovery/jobs/authorize` et `POST /api/v1/discovery/collectors/disable`.
- Acceptation sécurité : un collector inconnu, désactivé, présenté avec une empreinte différente ou hors scope ne peut recevoir aucun job Discovery.
- Mise à jour OpenAPI, README, architecture, validation, traçabilité et tests de non-régression avec couverture globale `>= 98 %`.
- Conservation des garanties précédentes : exports signés, migration legacy dry-run, imports génériques/bulk, Swagger/ReDoc/OpenAPI, séparation requirements runtime/dev/CI, pgAdmin `admin@openinfra.tld` et Docker limité au lab/smoke/test.

## 0.27.1 - 2026-07-04

### Fixed

- Corrected a Bandit CI failure caused by the JSON backend default state containing an empty `export_signing_secret` placeholder.
- Removed the persisted export signing key from the initial empty JSON state; the key remains generated lazily, stored only when first required, and reused afterwards.
- Audited similar production default-state entries to avoid hardcoded secret/password/token placeholders without using `#nosec`.
- Preserved the v0.27.0 legacy migration framework and all prior Docker, Swagger/ReDoc, import, bulk import and signed export features.

### Validation

- Ruff format/check, MyPy, Bandit, security gate, pip-audit dry-run, tests, coverage, quality gate, compileall, CLI/spec/migration/API/packaging checks were rerun for the corrective release.

## 0.27.0 - 2026-07-04

- Roadmap : P06 / EPIC-0604 — Migration depuis référentiels existants.
- Ajout des templates de migration Device42, NetBox, Nautobot, GLPI et CSV générique vers la IT Ressources Management.
- Ajout du domaine de planification `LegacyMigrationSource`, `MigrationTemplate`, `MigrationGap` et `MigrationPlanReport` avec statut, gaps, rapport dry-run et stratégie de reprise.
- Ajout du service applicatif de migration : sélection de template, mapping contrôlé, simulation sans écriture, rapport d’écarts, audit et persistance du rapport.
- Ajout du support de mappings littéraux `literal:<valeur>` pour normaliser les champs `kind` et `source` sans exiger de colonnes artificielles dans les exports legacy.
- Ajout de la migration PostgreSQL `0022_legacy_migration_framework.sql` avec `migration_plan_reports` partitionnée par hash du tenant et index de consultation.
- Ajout des commandes `openinfra import migration-template`, `openinfra import migration-plan` et `openinfra import migration-report`.
- Ajout des endpoints `GET /api/v1/imports/migration-template`, `POST /api/v1/imports/migration-plans` et `GET /api/v1/imports/migration-report`.
- Mise à jour OpenAPI, README, architecture, validation, traçabilité et tests de non-régression.
- Conservation des garanties précédentes : imports génériques et bulk, exports signés, Swagger/ReDoc/OpenAPI, séparation requirements runtime/dev, pgAdmin `admin@openinfra.tld`, Docker limité au lab/smoke/test et couverture globale `>= 98 %`.

## 0.26.0 - 2026-07-04

- Roadmap : P06 / EPIC-0603 — Exports asynchrones et signés.
- Ajout du domaine `data_export` : formats CSV/JSON/XLSX, ressource `source_objects`, filtres, jobs, statuts et métadonnées d’artefact.
- Ajout du service applicatif `ExportService` : création de job non bloquante, exécution worker séparée, pagination bornée, production d’artefact, SHA-256, signature HMAC-SHA256, audit de succès/échec et vérification d’intégrité avant téléchargement.
- Ajout des ports et adaptateurs JSON/PostgreSQL `ExportRepository`, avec stockage des jobs, artefacts et clé de signature managée par le backend.
- Ajout de la migration PostgreSQL `0021_export_framework.sql` avec `export_jobs` et `export_artifacts` partitionnées par hash du tenant, index de queue et index d’audit exports.
- Ajout des commandes `openinfra export request`, `openinfra export run`, `openinfra export report` et `openinfra export artifact`.
- Ajout des endpoints `POST /api/v1/exports/jobs`, `GET /api/v1/exports/jobs`, `POST /api/v1/exports/run` et `GET /api/v1/exports/artifact`.
- Mise à jour OpenAPI, README, architecture, validation, traçabilité et tests de non-régression.
- Conservation des garanties précédentes : séparation requirements runtime/dev, Swagger/ReDoc/OpenAPI, pgAdmin `admin@openinfra.tld`, Docker limité au lab/smoke/test et couverture globale `>= 98 %`.

## 0.25.1 - 2026-07-04

- Correctif CI/DevSecOps sans nouveau jalon fonctionnel : conservation intégrale du jalon P06 / EPIC-0602 livré en `0.25.0`.
- Correction du formatage Ruff sur les fichiers modifiés par le jalon import massif.
- Sécurisation du parsing XLSX : remplacement de `xml.etree.ElementTree` par `defusedxml.ElementTree`, ajout de la dépendance runtime `defusedxml>=0.7.1` et test de non-régression contre les payloads XML à entités externes.
- Correction des alertes Bandit `B405` et `B314` sur `src/openinfra/infrastructure/import_parsers.py`.
- Correction des alertes Ruff similaires détectées après formatage : imports, arguments de protocole, `isinstance` moderne, méthodes HTTP héritées `do_GET`/`do_POST` et smoke subprocess contrôlé.
- Correction des erreurs MyPy introduites autour des rapports bulk, des mappings JSON/PostgreSQL et du typage `DdiChange.compensating`.
- Maintien des garanties existantes : couverture globale supérieure à 98 %, Swagger/ReDoc/OpenAPI, pgAdmin `admin@openinfra.tld`, migrations PostgreSQL `0001` à `0020` et lab Docker.

## 0.25.0 - 2026-07-04

- Roadmap : P06 / EPIC-0602 — Import massif scalable.
- Ajout du mode `BulkImportDatasetCommand` sans régression de l’import générique atomique `0.24.0`.
- Ajout du streaming CSV via `ImportDatasetParser.iter_rows`, avec fallback de parsing complet pour CSV/JSON/XLSX existants.
- Ajout du traitement par batches bornés, checkpoints persistés, reprise par `resume_job_id`, métriques d’exécution, DLQ échantillonnée et rapport bulk consultable.
- Ajout des modèles de domaine `BulkImportReport`, `BulkImportCheckpoint` et `BulkImportMetrics`.
- Ajout de la migration PostgreSQL `0020_bulk_import_framework.sql` avec `bulk_import_jobs` et `bulk_import_checkpoints` partitionnées par tenant et index opérationnels.
- Extension des backends JSON et PostgreSQL avec persistance des rapports/checkpoints bulk.
- Ajout des commandes `openinfra import bulk-dataset`, `openinfra import bulk-report` et `openinfra import bulk-checkpoint`.
- Ajout des endpoints `/api/v1/imports/bulk-datasets`, `/api/v1/imports/bulk-report` et `/api/v1/imports/bulk-checkpoint`.
- Renforcement des tests domaine, parseurs, service, CLI, API et migrations PostgreSQL `0001` à `0020`.
- Conservation des correctifs v0.22.3/v0.23.1/v0.24.0 : migrations PostgreSQL IPAM, pgAdmin `admin@openinfra.tld`, route racine API, logs runtime, Swagger UI, ReDoc et OpenAPI YAML.

## 0.23.1 - 2026-07-04

- Correctif API runtime : `GET /` ne retourne plus `{"error": "not_found"}` mais un document JSON de découverte du service.
- Ajout de `GET /api/v1` pour exposer le point d’entrée canonique de l’API versionnée, ses liens opérationnels et les URLs de santé/préparation.
- Ajout d’un log de démarrage JSON sur stdout au lancement de `openinfra-api`, afin que `docker logs openinfra-api` confirme explicitement le backend, le port et les endpoints utiles.
- Mise à jour OpenAPI, tests de non-régression HTTP et documentation runtime.
- Aucun changement fonctionnel DDI ; le jalon P05 / EPIC-0506 livré en `0.23.0` est conservé intégralement.

## 0.23.0 - 2026-07-04

- Roadmap : P05 / EPIC-0506 — DDI intégration baseline.
- Ajout du domaine DDI IPAM : providers BIND, PowerDNS et Kea, changements DNS/DHCP typés, divergences et plan de rollback compensatoire.
- Ajout du service `IpamDdiService` pour générer une prévisualisation DNS/DHCP depuis une réservation IPAM existante, avec dry-run par défaut et audit.
- Ajout des connecteurs baseline `BindDdiConnector`, `PowerDnsDdiConnector` et `KeaDdiConnector` sans dépendance externe ni appel réseau implicite.
- Détection explicite des divergences DNS forward/PTR et des conflits DHCP actifs avant application, afin d’éviter toute divergence silencieuse.
- Ajout de la commande `openinfra ipam ddi-preview` et de l’endpoint `POST /api/v1/ipam/ddi-preview`.
- Mise à jour README, OpenAPI, architecture, traçabilité et tests avec couverture globale maintenue à `>= 98 %`.

## 0.22.3 - 2026-07-04

- Correctif PostgreSQL runtime : la migration `0015_ipam_enterprise_foundation.sql` ajoute, alimente et contraint désormais `prefixes.family` avant la création de l’index `idx_prefixes_vrf_family`.
- Correction de l’échec Docker `openinfra-migrate` : `psycopg.errors.UndefinedColumn: column "family" does not exist` sur une base PostgreSQL fraîche.
- Renforcement de `scripts/quality_gate.py` et ajout d’un test de non-régression pour empêcher toute référence indexée à `prefixes.family` sans backfill préalable.
- Correctif pgAdmin4 Docker : l’email par défaut est désormais `admin@openinfra.tld`, afin d’éviter le rejet de `admin@openinfra.local` par la validation pgAdmin4 des domaines réservés.
- Aucun nouveau jalon fonctionnel ; la version reste une corrective runtime Docker/PostgreSQL.

## 0.22.2 - 2026-07-04

- Ajout du service Docker Compose `pgadmin` pour administrer la base PostgreSQL du lab OpenInfra.
- Ajout des variables `.env.example` et génération automatique dans `scripts/docker_environment.py` : email, mot de passe, bind, port et image pgAdmin4.
- Ajout d’un volume persistant `openinfra-pgadmin-data` et d’un fichier `docker/pgadmin/servers.json` préconfigurant le serveur PostgreSQL Compose `postgres`.
- Mise à jour du démarrage Docker assisté : `python scripts/docker_environment.py up` lance désormais `postgres`, `migrate`, `auth-bootstrap`, `api` et `pgadmin`.
- Ajout de garde-fous qualité et tests pour empêcher une régression du lab pgAdmin4.

## 0.22.1 - 2026-07-04

- Correctif Docker/PostgreSQL : remplacement des index d’audit `occurred_at` par `created_at` dans les migrations `0012`, `0013` et `0014`, afin que `openinfra database apply-migrations` réussisse sur une base PostgreSQL neuve.
- Correctif Docker Compose : suppression du `HEALTHCHECK` API global du `Dockerfile`, qui était hérité à tort par les conteneurs one-shot `migrate`, `auth-bootstrap` et `smoke`. Le healthcheck applicatif reste défini uniquement sur le service `api`.
- Correction des tags Docker par défaut : `.env.example`, `compose.yaml` et `scripts/docker_environment.py` utilisent maintenant `0.22.1`.
- Ajout de garde-fous qualité contre les références à `audit_events.occurred_at`, les healthchecks API hérités et les vieux tags Docker par défaut.

## 0.22.0 - 2026-07-03

- Ajout de l’UI IPAM opérationnelle P05/EPIC-0505 sous forme de view model applicatif, rendu HTML serveur et workflows CLI/API.
- Ajout du service `IpamUiService` : dashboard VRF/préfixes/capacité/conflits, recherche IP/hostname/DNS/DHCP et assistant de réservation.
- Ajout des commandes `openinfra ipam ui-dashboard`, `openinfra ipam ui-search` et `openinfra ipam reservation-wizard`.
- Ajout des endpoints `/api/v1/ipam/ui-dashboard`, `/api/v1/ipam/ui-search`, `/api/v1/ipam/reservation-wizard` et `/ui/ipam`.
- Extension des smoke tests CI avec un parcours UI IPAM JSON/HTML.
- Mise à jour README, OpenAPI, architecture, validation, traçabilité et rapport de validation.

## 0.21.0 - 2026-07-03

- Ajout du jalon P05 / EPIC-0504 : moteur de détection conflits IPAM.
- Détection des overlaps de préfixes, overlaps de ranges, doublons d'adresses, leases DHCP conflictuels, adresses observées hors préfixe et divergences DNS/PTR.
- Ajout des observations DNS/DHCP dans les backends JSON et PostgreSQL.
- Ajout de la migration PostgreSQL `0018_ipam_conflict_detection.sql`.
- Ajout des commandes `observe-dns`, `observe-dhcp-lease` et `detect-conflicts`.
- Ajout des endpoints API `/api/v1/ipam/dns-observations`, `/api/v1/ipam/dhcp-leases` et `/api/v1/ipam/conflicts`.
- CI mise à jour avec rendu migration `0018`, smoke IPAM conflits et correction d'une étape security smoke dupliquée.

## 0.20.0 - 2026-07-03

- Roadmap : P05 / EPIC-0503 — VLAN/VXLAN/ASN/BGP fondation.
- Ajout du domaine IPAM réseau : `VlanGroup`, `Vlan`, `VxlanVni`, `AutonomousSystem`, `BgpPeer` et politique de validation `NetworkIdentifierPolicy`.
- Ajout du service applicatif `IpamModelService` pour définir VLAN groups, VNI/VXLAN, VLAN attachés à VRF/VNI, ASN et pairs BGP.
- Cohérence métier : VLAN attaché à un VNI doit référencer le même VRF ; VNI unique par tenant ; ASN local et distant distincts ; route targets validées au format `ASN:NUMBER`.
- Ajout des commandes `openinfra ipam define-vlan-group`, `define-vxlan-vni`, `define-vlan`, `define-asn`, `define-bgp-peer` et `network-bindings`.
- Ajout des endpoints `POST /api/v1/ipam/vlan-groups`, `POST /api/v1/ipam/vxlan-vnis`, `POST /api/v1/ipam/vlans`, `POST /api/v1/ipam/asns`, `POST /api/v1/ipam/bgp-peers` et `GET /api/v1/ipam/network-bindings`.
- Ajout de la migration PostgreSQL `0017_ipam_networking_foundation.sql` avec contraintes VRF/VLAN/VNI/ASN et index d’audit opérationnel.
- CI, OpenAPI, README, runbooks, traçabilité et tests mis à jour avec couverture globale `>= 98 %`.

## 0.19.0 - 2026-07-03

- Roadmap : P05 / EPIC-0502 — Allocation IP transactionnelle.
- Allocation `openinfra ipam allocate` durcie : sélection next-available tenant/VRF/prefixe, idempotence par clé métier, prise en compte des adresses suivies, plages d’allocation, réservations et exclusions.
- Verrou fin côté PostgreSQL via `pg_advisory_xact_lock` par tenant/VRF/prefixe afin d’éviter les collisions inter-processus pendant le calcul + insertion.
- Backend JSON protégé par transaction atomique et test de concurrence 100 allocations sans collision.
- Migration PostgreSQL `0016_ipam_transactional_allocation.sql` ajoutant les index transactionnels de scan allocation/ranges/adresses.
- CI, OpenAPI, documentation, runbooks et validation mis à jour.

## 0.18.0 - 2026-07-03

- Roadmap : P05 / EPIC-0501 — Modèle IPAM IPv4/IPv6/VRF.
- Ajout du domaine `IpAggregate`, `IpRange`, `IpAddressRecord`, `IpRangePurpose` et `IpAddressStatus`.
- Ajout du service applicatif `IpamModelService` pour définir VRF, agrégats, préfixes, plages IP, adresses suivies et capacité de préfixe.
- Ajout des commandes `openinfra ipam define-vrf`, `define-aggregate`, `define-prefix`, `define-range`, `register-address`, `list-prefixes` et `capacity`.
- Ajout des endpoints `POST /api/v1/ipam/vrfs`, `POST /api/v1/ipam/aggregates`, `POST /api/v1/ipam/prefixes`, `POST /api/v1/ipam/ranges`, `POST /api/v1/ipam/addresses`, `GET /api/v1/ipam/prefixes` et `GET /api/v1/ipam/capacity`.
- Ajout de la migration PostgreSQL `0015_ipam_enterprise_foundation.sql` avec tables partitionnées pour agrégats, ranges et adresses suivies, index par tenant/VRF/prefixe/adresse et contraintes IPv4/IPv6.
- Règle métier EPIC-0501 : les chevauchements de préfixes et agrégats sont refusés dans un même VRF et autorisés entre VRF distincts.
- CI, OpenAPI, README, architecture, runbook et tests mis à jour avec couverture globale `>= 98 %`.

## 0.17.6 - 2026-07-03

- Correctif CI Python 3.13 : les jetons générés dans les smoke tests GitHub Actions sont désormais préfixés par `ci_` afin qu'aucune valeur aléatoire commençant par `-` ne soit interprétée par `argparse` comme une option au lieu d'un argument de `--token`.
- Durcissement de la génération applicative des jetons API : `TokenGenerator` produit désormais des jetons préfixés par `oi_`, sans casser la validation ni l'authentification des jetons existants.
- Alignement des scripts optionnels Docker/lab : `docker/openinfra-runtime-smoke.py` et `scripts/docker_environment.py` génèrent aussi des jetons préfixés sûrs.
- Ajout d'un garde-fou dans `scripts/security_gate.py` contre le retour de `print(secrets.token_urlsafe(48))` dans le workflow CI.
- Ajout de tests de non-régression sur le gate CI et la génération de jetons applicatifs.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif.

## 0.17.5 - 2026-07-03

- Correctif GitHub Actions : suppression du job PR-only `dependency-review` du workflow de push pour éviter le statut `Skipped` après `push`.
- Ajout du workflow séparé `.github/workflows/dependency-review.yml`, déclenché uniquement par `pull_request`.
- Renommage explicite du job sécurité en `Blocking push vulnerability gate / Python ...` pour matérialiser le blocage vulnérabilités sur `push`.
- Renforcement de `scripts/security_gate.py` : rejet de `actions/dependency-review-action` et de `if: github.event_name == 'pull_request'` dans le workflow de push, et vérification du workflow PR dédié.
- Ajout de tests de non-régression sur la séparation workflow push / workflow PR.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif.

## 0.17.4 - 2026-07-03

- Correctif CI sécurité : remplacement de l'audit d'environnement par un audit explicite du fichier `requirements/security-audit.txt`.
- Ajout d'un garde-fou bloquant dans `scripts/security_gate.py` contre le retour d'un audit `pip-audit` de l'environnement editable.
- Ajout du fichier `requirements/security-audit.txt` pour auditer uniquement les dépendances tierces.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif.

## 0.17.3 - 2026-07-03

- Correctif CI sécurité initial sur l'audit du package projet installé en editable ; correction finalisée en v0.17.4 avec une entrée d'audit dédiée aux dépendances tierces.
- Correction PostgreSQL runtime : `PostgreSQLDriver.connect()` encapsule les erreurs de connexion `psycopg` en `OpenInfraError`, afin que les erreurs DNS/réseau/serveur manquant soient reportées proprement par OpenInfra au lieu de faire échouer les tests avec une exception tierce.
- Mise à jour tests de sécurité CI pour valider la présence de `requirements/security-audit.txt`.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif livré en v0.17.0.
- Couverture globale conservée au-dessus du seuil obligatoire `>= 98 %`.

## 0.17.2 - 2026-07-03

- Correctif CI bloquant : ajout d'un job `blocking-security` exécuté sur `push`, pull request et lancement manuel.
- Prise en charge CI de Python `3.13` et `3.14`, en plus de `3.11` et `3.12`.
- Ajout de contrôles sécurité bloquants : `bandit` SAST, `pip-audit` pour vulnérabilités de dépendances, `scripts/security_gate.py` pour secrets committés et durcissement workflow.
- Ajout de CodeQL avec suites `security-extended` et `security-and-quality`.
- Ajout du `dependency-review-action` sur pull requests et d'une politique Dependabot pour `pip` et `github-actions`.
- Correction du smoke CI `security list-tokens` / `security revoke-token` : les opérations d'administration des tokens utilisent désormais un jeton `security:admin`, et non un jeton `ipam:operator`.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif livré en v0.17.0.
- Couverture globale conservée au-dessus du seuil obligatoire `>= 98 %`.

## 0.17.0 - 2026-07-03

- Roadmap : P04 / EPIC-0406 — Énergie et refroidissement fondation.
- Ajout du domaine `PowerDevice`, `PowerCircuit`, `CoolingZone`, `RackPowerReservation` et `RackEnergyCoolingReport`.
- Ajout du service applicatif `DcimEnvironmentService` avec contrôle des capacités source, circuit, rack et zone de refroidissement.
- Ajout des commandes `openinfra dcim define-power-device`, `define-power-circuit`, `define-cooling-zone`, `reserve-power` et `energy-cooling-capacity`.
- Ajout des endpoints `POST /api/v1/dcim/power-devices`, `POST /api/v1/dcim/power-circuits`, `POST /api/v1/dcim/cooling-zones`, `POST /api/v1/dcim/power-reservations` et `GET /api/v1/dcim/energy-cooling-capacity`.
- Ajout de la migration PostgreSQL `0014_dcim_energy_cooling_foundation.sql` avec tables partitionnées et index par source, rack, circuit et zone.
- Correction du déclenchement GitHub Actions : le workflow n’est plus limité à `main`, il se lance sur tous les `push`, toutes les pull requests et peut être lancé manuellement via `workflow_dispatch`.
- Confirmation production : OpenInfra reste indépendant de Docker en production ; Docker demeure un lab facultatif de test/smoke.
- CI, OpenAPI, runbooks, architecture, tests et quality gate mis à jour avec couverture globale `>= 98 %`.

## 0.16.0 - 2026-07-03

- Roadmap : P04 / EPIC-0405 — Câblage DCIM fondation.
- Ajout du domaine `PatchPanel`, `DcimPortEndpoint`, `DcimPort`, `DcimCablePathSegment` et `DcimCable`.
- Ajout du service applicatif `DcimCablingService` avec génération de ports, connexion de câbles, prévention des conflits d’endpoint actif et trace humaine.
- Ajout des commandes `openinfra dcim define-patch-panel`, `define-port`, `connect-cable` et `cable-trace`.
- Ajout des endpoints `POST /api/v1/dcim/patch-panels`, `POST /api/v1/dcim/ports`, `POST /api/v1/dcim/cables` et `GET /api/v1/dcim/cable-trace`.
- Ajout de la migration PostgreSQL `0013_dcim_cabling_foundation.sql` avec tables partitionnées et index par endpoint.
- Production clarifiée : runtime serveur natif `systemd` + virtualenv + PostgreSQL ; Docker reste uniquement un lab optionnel.
- CI, OpenAPI, runbooks, architecture, tests et quality gate mis à jour avec couverture globale `>= 98 %`.

## 0.15.0 - 2026-07-03

- Roadmap : P04 / EPIC-0404 — Plans 2D salle et rack elevation.
- Ajout des objets domaine `RoomPlan2D`, `RoomPlanCell`, `RackElevation` et `RackElevationUnit`.
- Ajout du service applicatif `DcimVisualizationService` et des lectures repository `list_racks_in_room` / `list_equipment_in_room`.
- Ajout des commandes `openinfra dcim room-plan` et `openinfra dcim rack-elevation` avec sorties JSON, SVG et HTML.
- Ajout des endpoints `GET /api/v1/dcim/room-plan` et `GET /api/v1/dcim/rack-elevation`.
- Ajout de la migration PostgreSQL `0012_dcim_visualization_indexes.sql` pour les chemins de lecture visualisation.
- Extension de l’OpenAPI, de la CI, du smoke Docker, de la documentation et des tests pour conserver une couverture globale `>= 98 %`.

## 0.14.0 - 2026-07-03

- Roadmap : P04 / EPIC-0403 — QR codes, fiches de localisation et chemins d’intervention terrain.
- Ajout du domaine `EquipmentLocatorPayload`, `QrCodeSvgDocument`, `EquipmentLocatorSheet`, `EquipmentScanProof` et `InterventionRouteStep`.
- Ajout du service `DcimFieldOperationService` pour générer une fiche terrain JSON/HTML et vérifier une preuve de scan QR.
- Ajout de la permission `dcim.identify` au rôle `dcim:operator`.
- Ajout des commandes `openinfra dcim locator-sheet` et `openinfra dcim verify-scan`.
- Ajout des endpoints `GET /api/v1/dcim/locator-sheet` et `POST /api/v1/dcim/verify-scan`.
- Ajout de la migration PostgreSQL `0011_dcim_field_operations.sql` préparant l’historique partitionné des preuves terrain.
- Extension du runtime Docker smoke avec génération de fiche, QR compact et validation de scan.
- Relèvement du seuil de couverture globale à `>= 98 %` avec tests unitaires, intégration, CLI et API supplémentaires.

# Changelog

## 0.13.0 - 2026-07-03

- Roadmap : P04 / EPIC-0402 — Racks, unités U, faces, capacité et occupation.
- Ajout du domaine `RackFace` et `RackCapacityReport`.
- Extension de `Rack` avec faces utilisables, capacité U, poids maximal et capacité électrique.
- Extension de `EquipmentLocation` avec `rack_face`, `u_height`, calcul des unités U occupées et contrôle de chevauchement.
- Ajout du service `DcimRackService` et extension de `DcimLocationService`.
- Ajout de la commande `openinfra dcim define-rack` et `openinfra dcim rack-capacity`.
- Extension de `openinfra dcim locate` avec `--rack-face` et `--u-height`.
- Ajout des endpoints `POST /api/v1/dcim/racks` et `GET /api/v1/dcim/rack-capacity`.
- Ajout de la migration PostgreSQL `0010_dcim_rack_capacity.sql`.
- Extension du runtime Docker smoke avec scénario rack complet.

## 0.12.0 - 2026-07-03

- Réalignement maintenu sur la roadmap avec P04 / EPIC-0401 Modèle physique DCIM.
- Ajout du modèle pays, région, ville, site, bâtiment, étage, salle et zone de salle.
- Extension de la localisation équipement avec étage, zone et coordonnées X/Y/Z.
- Ajout de validations de grille ligne/colonne, zone incluse dans salle, conflits rack/U, cohérence étage et zone.
- Ajout du service `DcimTopologyService` pour définir une salle physique idempotente et auditée.
- Ajout de la commande `openinfra dcim define-room` et extension de `openinfra dcim locate` avec `--floor` et `--zone`.
- Ajout de l’endpoint `POST /api/v1/dcim/rooms` avec contrôle `dcim.write` en mode API authentifié.
- Ajout de la migration PostgreSQL `0009_dcim_physical_model.sql` avec tables et index DCIM physiques.
- Extension du runtime Docker smoke, OpenAPI, README, architecture, runbooks, CI et tests.

## 0.11.0 - 2026-07-03

- Réalignement maintenu sur REL-01/P03 avec EPIC-0306 Gouvernance minimale des sources.
- Ajout du domaine `SourceGovernanceRule`, `SourceGovernanceEvaluation` et `SourceGovernanceEvaluator`.
- Ajout du service applicatif `SourceGovernanceService` : création, inventaire paginé, évaluation et désactivation des règles.
- Intégration de la gouvernance dans `SourceOfTruthService` pour refuser les écrasements non autoritatifs selon la stratégie `reject`.
- Ajout du rôle `itrm:governance-admin` et des permissions `itrm.governance.read` / `itrm.governance.write`.
- Ajout des référentiels JSON et PostgreSQL `SourceGovernanceRepository`.
- Ajout de la migration PostgreSQL `0008_source_governance.sql` avec table partitionnée, contraintes et index métier.
- Ajout des commandes `openinfra itrm create-governance-rule`, `list-governance-rules`, `evaluate-governance` et `deactivate-governance-rule`.
- Ajout des endpoints `/api/v1/itrm/governance-rules`, `/api/v1/itrm/governance/evaluate` et `/api/v1/itrm/governance/deactivate-rule`.
- Extension du runtime Docker smoke, OpenAPI, README, architecture, runbooks, CI et tests de non-régression.

## 0.10.0 - 2026-07-03

- Réalignement roadmap sur REL-01/P03 IT Ressources Management avant poursuite des briques P14.
- Ajout du domaine ITRM : objets typés, clés sûres, tags, attributs JSON contrôlés, source déclarée, version et statut.
- Ajout des relations typées transactionnelles entre objets ITRM avec provenance et validité temporelle.
- Ajout des snapshots `SourceObjectSnapshot` pour restitution time-travel initiale par version.
- Ajout du service applicatif `SourceOfTruthService` avec contrôle `itrm.read` / `itrm.write` et audit.
- Ajout des référentiels JSON et PostgreSQL `SourceOfTruthRepository`.
- Ajout de la migration PostgreSQL `0007_source_of_truth_core.sql` avec tables partitionnées et index type/tags/JSONB/relations.
- Ajout des commandes `openinfra itrm upsert-object`, `get-object`, `list-objects`, `get-object-version`, `create-relation`, `list-relations`.
- Ajout des endpoints `/api/v1/itrm/objects`, `/api/v1/itrm/object-versions` et `/api/v1/itrm/relations`.
- Extension du runtime Docker smoke, OpenAPI, README, architecture, runbooks, CI et tests de non-régression.

## 0.9.0 - 2026-07-03

- Ajout du domaine d’audit exploitable : filtres sûrs, export JSON/JSONL, page d’événements et rapport d’intégrité.
- Ajout du chaînage d’intégrité `previous_hash` / `record_hash` calculé en SHA-256 sur les événements d’audit.
- Ajout du service applicatif `AuditTrailService` : liste, export et vérification d’intégrité avec contrôle `audit.read`.
- Ajout du rôle intégré `audit:reader` et extension de `security:admin` avec la permission `audit.read`.
- Ajout de la migration PostgreSQL `0006_audit_trail_integrity.sql` avec colonnes, contraintes et index d’intégrité.
- Ajout des commandes `openinfra audit list`, `openinfra audit export` et `openinfra audit verify-integrity`.
- Ajout des endpoints `/api/v1/audit/events`, `/api/v1/audit/export` et `/api/v1/audit/integrity`.
- Extension des smoke tests Docker et CI pour couvrir l’audit trail.
- Mise à jour README, OpenAPI, runbooks, architecture, CI et tests de non-régression.

## 0.8.0 - 2026-07-02

- Ajout du socle ABAC contextuel tenant/site/environnement comme contrôle complémentaire à RBAC.
- Ajout du domaine `AccessPolicyRule`, `AccessRequestContext` et des effets `allow` / `deny` avec priorité explicite aux règles de refus.
- Ajout du service applicatif `AccessPolicyService` : création, inventaire paginé, désactivation et évaluation des règles.
- Ajout des référentiels JSON et PostgreSQL `AccessPolicyRepository`.
- Ajout de la migration PostgreSQL `0005_access_policy_abac.sql` avec table partitionnée, index GIN sujets/rôles/sites/environnements et index d’audit `access.policy.%`.
- Ajout des commandes `openinfra access create-rule`, `list-rules`, `evaluate` et `deactivate-rule`.
- Extension de `openinfra ipam allocate` avec `--auth-token`, `--site-code` et `--environment` pour valider RBAC + ABAC côté CLI.
- Ajout des endpoints `/api/v1/access/rules`, `/api/v1/access/evaluate`, `/api/v1/access/deactivate-rule` et enforcement ABAC sur `/api/v1/ipam/allocate` lorsque l’API authentifiée est activée.
- Extension des smoke tests Docker et CI pour couvrir la migration `0005` et le scénario ABAC runtime.
- Mise à jour README, OpenAPI, runbooks, architecture, CI et tests de non-régression.

## 0.6.0 - 2026-07-02

- Ajout du cycle de vie complet des jetons API : expiration optionnelle, révocation, rotation, compteur d’usage et inventaire paginé sans exposition des hashes.
- Ajout de la migration PostgreSQL `0003_security_token_lifecycle.sql` avec colonnes de cycle de vie et index opérationnels.
- Ajout des commandes `openinfra security list-tokens`, `openinfra security revoke-token` et `openinfra security rotate-token`.
- Ajout des endpoints `/api/v1/security/tokens`, `/api/v1/security/revoke-token` et `/api/v1/security/rotate-token`.
- Extension des smoke tests Docker et CI pour couvrir la migration `0003` et le cycle de vie sécurité.
- Mise à jour README, OpenAPI, runbooks, architecture, CI et tests de non-régression.

## 0.5.0 - 2026-07-02

- Ajout du moteur applicatif de migrations PostgreSQL avec historique `openinfra_schema_migrations`, checksum SHA-256, dry-run, statut et application idempotente.
- Ajout des commandes `openinfra database status` et `openinfra database apply-migrations`.
- Renforcement de `/ready` en backend PostgreSQL avec contrôle du schéma appliqué.
- Ajout de l'endpoint `/api/v1/database/schema` pour exposer le statut opérationnel du schéma.
- Mise à jour du runtime Docker : le service `migrate` utilise désormais l'image applicative OpenInfra et non un appel direct `psql`.
- Extension des smoke tests Docker pour vérifier le statut de schéma.
- Suppression des marqueurs de code incomplet dans `src`, `tests`, `scripts`, `docker` et runbooks.
- Mise à jour README, OpenAPI, runbooks PostgreSQL/Docker/validation, architecture, CI et tests.

## 0.3.0 - 2026-07-02

- Ajout d’un environnement d’exécution Docker complet pour valider OpenInfra avec PostgreSQL réel, migration, API et CLI.
- Ajout du `Dockerfile` applicatif non-root et du `compose.yaml` avec services `postgres`, `migrate`, `api` et `smoke`.
- Ajout du script `scripts/docker_environment.py` pour générer un `.env` local sécurisé, démarrer, valider, superviser et réinitialiser le runtime.
- Ajout du scénario `docker/openinfra-runtime-smoke.py` validant `/ready`, `/health`, `/api/v1/version`, allocation IPAM API idempotente et allocation IPAM CLI en backend PostgreSQL.
- Ajout de la sonde applicative `/ready` connectée au backend de persistance via `ReadinessProbe`.
- Mise à jour OpenAPI, README, runbook Docker, CI GitHub Actions et tests d’intégration.

## 0.2.0 - 2026-07-02

- Ajout de la persistance PostgreSQL runtime via adaptateur optionnel `psycopg`.
- Ajout des référentiels PostgreSQL DCIM, IPAM et audit alignés sur la migration partitionnée `0001_bootstrap.sql`.
- Ajout d’un gestionnaire transactionnel PostgreSQL avec registre de session par thread et fermeture systématique des connexions.
- Extension CLI/API pour sélectionner le backend `json` ou `postgresql` avec DSN explicite ou variable `OPENINFRA_DATABASE_DSN`.
- Correction transactionnelle IPAM : création de préfixe, idempotence, allocation, réservation et audit sont exécutés dans la même unité de travail.
- Ajout de tests d’intégration PostgreSQL sans base externe via connecteur simulé et vérification des erreurs opérationnelles.
- Mise à jour documentation, CI smoke tests et rapport de validation.

## 0.1.0 - 2026-07-02

- Création du socle Python POO OpenInfra.
- Ajout des domaines DCIM, IPAM, ITAM, Discovery et Dependency Mapping.
- Ajout des services applicatifs pour localisation DCIM et allocation IPAM idempotente.
- Ajout de la persistance JSON atomique pour développement et tests.
- Ajout de la migration PostgreSQL initiale partitionnée et indexée.
- Ajout de la CLI, de l'API HTTP, de la documentation, des tests et de la CI GitHub Actions.
- Intégration documentaire du CDC/SFG/STG v4 et de la roadmap v1 comme sources contractuelles.

## 0.29.14

- Ajout P09 initial : ITRM Quality & Certification.
- Ajout du service applicatif `ITResourcesManagementQualityService` pour scorer les objets ITRM.
- Ajout des commandes `openinfra itrm quality-object` et `openinfra itrm quality-summary` avec alias `openinfra sot ...` conservés.
- Ajout des endpoints API `/api/v1/itrm/quality/object` et `/api/v1/itrm/quality/summary` avec alias `/api/v1/sot/...` via compatibilité existante.
- Dashboard web enrichi avec les opérations de qualité/certification ITRM.
- RBAC enrichi avec la permission `itrm.quality.read`, incluse dans les rôles ITRM de lecture/opération/gouvernance.
