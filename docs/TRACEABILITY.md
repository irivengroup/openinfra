## v0.29.61 — discovery locale Lite/Pro sans agent

`REQ-00804` est couvert par les tests domaine, service, CLI, API HTTP, OpenAPI, discovery document, validation frontend et portail web. Le contrat vérifie `dry_run=true`, `agent_required=false`, `network_scan_executed=false`, `rsot_write_enabled=false` et le refus Enterprise.

## v0.29.60 — guides opérables de migration données

| Élément | Couverture |
| --- | --- |
| CDC | `REQ-00803` |
| Roadmap | P13 / EPIC-1306 / `TST-P13-DATA-MIGRATION-GUIDES` |
| Domaine | `MigrationGuide`, `MigrationGuideStep` |
| Application | `GenericImportService.get_migration_guide` |
| CLI | `openinfra import migration-guide` |
| API | `GET /api/v1/imports/migration-guide` |
| Web | `Imports / Exports > Guide migration données` |
| Garde-fou | Aucune mutation RSOT ; `native_ticketing_enabled=false` ; RSOT canonique. |

### v0.29.58 — préparation OpenService autonome

OpenInfra prépare le raccordement futur d’OpenService comme ITSM/CMDB externe autonome : fournisseur domaine `openservice`, validation de profil, plan de synchronisation CMDB depuis RSOT, CLI, API, OpenAPI et discovery. OpenService n’est pas développé dans OpenInfra et garde sa propre interface web ; aucun écran OpenService n’est ajouté à `openinfra-web`. Les exigences couvertes sont `REQ-00801` / `TST-WEB-102` et `TST-P25-ITSM-OPENSERVICE-FUTURE-CMDB-CONNECTOR`.

### v0.29.57 — intégrations externes GLPI Inventory et Freshservice Assets

OpenInfra publie GLPI Inventory et Freshservice Assets comme connecteurs ITSM externes de contexte : validation de profil, plans de synchronisation d’assets RSOT, API, CLI, portail web, OpenAPI et discovery. Aucun ticketing natif n’est introduit ; les secrets restent des références et les endpoints sont protégés par `security:admin` quand l’authentification API est active.

### v0.29.56 — intégration externe Jira Service Management Assets

OpenInfra publie Jira Service Management Assets comme connecteur ITSM externe de contexte : validation de profil, plan de synchronisation d’assets RSOT, API, CLI, portail web, OpenAPI et discovery. Aucun ticketing natif n’est introduit ; les secrets restent des références et les endpoints sont protégés par `security:admin` quand l’authentification API est active.

### v0.29.56 — intégrations ITSM externes ServiceNow et thème UI corrigé

- Ajout d'un composant web **Intégrations externes** exposant les politiques ITSM externes, la validation de connecteur ServiceNow et le plan de synchronisation CI.
- Les connecteurs ITSM restent strictement externes : aucun ticket, incident, demande ou changement natif n'est créé dans OpenInfra.
- Les formulaires utilisent à nouveau la classe Bootstrap 5 standard `btn btn-primary`; le turquoise `#24d8ab` est porté par la surcharge de thème.
- Le bloc `openinfra-runtime-status` est distingué uniquement par la couleur de texte `#003D8F`, sans fond, bordure ni padding supplémentaire.

### v0.29.54 — exports massifs streaming par chunks signés

- Ajout `openinfra export artifact-chunk` pour lire un artefact exporté signé par offset/taille bornée.
- Ajout `GET /api/v1/exports/artifact-chunk` retournant `content_base64`, `chunk_sha256`, `next_offset`, `final_chunk` et métadonnées d’artefact après vérification SHA-256 + HMAC-SHA256 complète.
- Ajout de l’opération portail `Imports / Exports > Chunk export signé`.
- OpenAPI, discovery, CDC et roadmap alignés sur P13 / EPIC-1302.
- Non-régression : le téléchargement complet `/api/v1/exports/artifact` et `openinfra export artifact` restent inchangés.

## v0.29.52 — P13 / EPIC-1301 progression imports massifs

| Élément | Alignement |
|---|---|
| CDC | `REQ-00795` / `TST-WEB-096` |
| Roadmap | P13 / EPIC-1301 / `TST-P13-BULK-IMPORT-PROGRESS` |
| Domaine | `BulkImportProgress` |
| Application | `GenericImportService.get_bulk_progress` |
| CLI | `openinfra import bulk-progress` |
| API | `GET /api/v1/imports/bulk-progress` |
| Web | composant **Imports / Exports**, opération **Progression import massif** |
| OpenAPI / Discovery | chemin `/api/v1/imports/bulk-progress` et entrée `imports.bulk_progress` |
| CI | smoke JSON bulk import progress dans `.github/workflows/ci.yml` |
| Tests | `tests/integration/test_import_services.py`, `test_cli_import.py`, `test_http_api.py`, `test_openinfra_web.py` |

## v0.29.13 — RSOT, agents proxy Enterprise et dashboard web

| Élément | Alignement |
|---|---|
| Roadmap | P08 consolidé : `openinfra-web` devient dashboard de pilotage API-only couvrant les domaines CLI. |
| RSOT (Ressource Source of Truth) | `Source of Truth/SOT` est renommé en `RSOT (Ressource Source of Truth)/RSOT`; `/api/v1/rsot/*`, `openinfra rsot` et `itrm:*` sont primaires, les alias `ri` et `sot` restent compatibles uniquement pour migration et sont dépréciés. |
| Discovery | `agent` est réservé aux proxy collectors Enterprise en topologie étoile ; Lite/Pro collectent via backends servers. |
| Backend | Le backend reste API-only : aucune authentification opérateur LDAP/IPA directe. |
| Frontend | `web/src/main.jsx` et les assets `interfaces/rendering/static` consomment `/api`, `/config.json` et exposent les opérations RSOT/IPAM/DCIM/Discovery/sécurité/audit sans secret backend. |
| Docker Compose | Service `web` ajouté avec healthcheck, dépendance sur `api`, port local `2006` et proxy `/api/*` vers `api:8080`. |
| Installateur | Scope web rendu en `openinfra-web.service` et configuration runtime matérialisée dans `/opt/openinfra/config/openinfra.conf`. |
| Tests | `tests/integration/test_openinfra_web.py`, `tests/integration/test_runtime_docker_environment.py`, `scripts/validate_frontend.py` et smoke Docker frontend. |

## v0.29.10 — P07 authentification LDAP/IPA et RBAC groupes

- Lite reste strictement limité à l'authentification locale `standard`.
- Pro et Enterprise acceptent LDAP/IPA uniquement côté frontend/web pour l'authentification opérateur.
- Le backend ne réalise pas de login LDAP/IPA opérateur direct ; il valide des jetons applicatifs, applique RBAC et audit.
- Les secrets de bind LDAP/IPA restent des références `env:`, `vault://`, `sops://`, `file://` ou `kms://`.
- Les groupes externes sont mappés explicitement vers des rôles OpenInfra ; l'annuaire authentifie l'identité mais n'autorise jamais les actions applicatives.
- L'émission des tokens applicatifs est basée sur les rôles OpenInfra effectifs.
- Les connexions externes réussies sont auditées sans journaliser les mots de passe, DN utilisateur en clair dans les payloads publics ou secrets de bind.

## v0.29.10 — Dette P06 PostgreSQL HA/PITR

| Élément | Alignement |
|---|---|
| Roadmap v2 | P06 PostgreSQL HA, synchronisation quasi temps réel et sauvegardes traité avant Discovery. |
| Installateurs | `installers/setup/**/install.py` rend le plan HA/PITR depuis les scopes backend/all-in-one. |
| Configuration | `install.ini` reste succinct ; `identity.peer_nodes` suffit à activer la topologie cluster. |
| Stockage | `/data/openinfra/pitr` et `/data/openinfra/backups` sont internes, non exposés dans `install.ini`. |
| Migrations | `0024_postgresql_ha_backup_registry.sql` ajoute registres HA, backups et failover auditables ; `postgresql_backup_runs` utilise `PRIMARY KEY (tenant_id, started_at, id)` pour respecter le partitionnement range PostgreSQL. |
| Sécurité | Failover contrôlé opérateur, pas de secret en clair, pas de port exposé dans `install.ini`. |
| CLI | `openinfra database ha-plan` expose le plan dérivé pour audit. |

## v0.29.6 — Dette P05 LVM/PGDATA native

- P03/P04 : moteur d'installation autonome par scope enrichi avec prérequis, rollback transactionnel, runtime Python, installation de requirements production et démarrage systemd effectif.
- P05 traité : orchestration LVM/PGDATA native avec compte `openinfra`, FS applicatif CDC, compte système PostgreSQL, FS PostgreSQL, PGDATA, symlink data, override systemd et migrations backend.

## v0.29.3 — FS applicatif interne et exception agent

| Domaine | Alignement |
|---|---|
| Installateurs | `managed_application_filesystem` est interne : actif pour all-in-one/server/web/agent. |
| Agent | FS applicatif `/opt/openinfra` géré comme les autres scopes, sans PostgreSQL, PGDATA, symlink data ou migrations. |
| CDC | Les dispositions LVM applicatives sont conservées pour les scopes applicatifs, car elles restent compatibles avec une pratique enterprise de cloisonnement, sauvegarde et quota. |

## v0.29.2 — Correctif installateurs minimaux, systemd rendu et migrations embarquées

| Axe | Alignement effectif |
|---|---|
| Installateurs | `install.ini` ne contient plus édition, scope, service, opérations, réseau, mountpoint, owner/group ni ports internes. |
| Systemd | `deploy/` est supprimé ; `InstallerSystemdUnitRenderer` rend les unités selon le scope. |
| Base de données | Les migrations backend sont embarquées sous `installers/migrations/postgresql`. |
| Requirements | `installers/requirements` contient uniquement les dépendances de production par scope. |
| CDC | Matrices `install.ini` et pages technique/exploitation mises à jour. |


## v0.29.51 — API/UI administration éditions et quotas

| Axe | Alignement réalisé |
| --- | --- |
| Roadmap v2 | P08 enrichit le portail web avec les contrôles d'édition déjà livrés en P02. |
| Domaine/Application | Réutilisation stricte de `EditionQueryService`, `CheckFeatureCommand` et `CheckQuotaCommand`. |
| API | Ajout de `/api/v1/editions/policies`, `/feature-check` et `/quota-check`, publiés dans discovery et OpenAPI. |
| Sécurité | Routes protégées par `security:admin` lorsque l'authentification API est active. |
| UI | Opérations ajoutées au composant Sécurité/RBAC/Audit dans React et runtime statique. |
| Tests | Non-régression API, OpenAPI, discovery, frontend et validateur. |


## v0.29.0 — P02 Éditions, feature gates et quotas runtime

| Axe | Alignement réalisé |
| --- | --- |
| Roadmap v2 | Dette P02 traitée avant reprise de Discovery. |
| Domaine | `OpenInfraEdition`, `FeatureCapability`, `QuotaResource`, `EditionPolicyCatalog`. |
| Application | `EditionRuntimeGuard`, `EditionQueryService`, injection dans Discovery, IAM, IPAM et DCIM. |
| Infrastructure | `RuntimeUsageRepository`, `JsonRuntimeUsageRepository`, `PostgreSQLRuntimeUsageRepository`. |
| Interfaces | `openinfra edition list`, `feature-check`, `quota-check`, `OPENINFRA_EDITION`, `openinfra-api --edition`. |
| Acceptation | Lite/Pro ne peuvent pas enregistrer ni utiliser d'agents collectors Discovery ; les quotas Lite/Pro sont vérifiés avant persistance. |
| Tests | `tests/integration/test_editions_feature_gates.py` et non-régressions existantes PostgreSQL/IPAM/Discovery. |

## v0.28.1 — Réalignement CDC v4.8.1 / roadmap v2

- Source contractuelle active : `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1`.
- Roadmap active : `docs/specifications/OpenInfra-Roadmap-Developpement-v2`.
- Dette prioritaire traitée : les gates, la documentation, les installateurs et le runtime natif ne référencent plus l'ancien contrat v4/v1.
- Nouveaux contrôles : `scripts/validate_autonomous_installer.py`, `scripts/validate_enterprise_alignment.py`, `openinfra installer validate`, `openinfra installer dry-run`.
- Installateurs contrôlés : Lite all-in-one, Pro server/web, Enterprise server/web/agent.
- Systemd canonique : unités rendues par l'installateur ; le dossier `deploy/` est explicitement rejeté par la quality gate.


## v0.28.1 — P07 / EPIC-0701 Registry collectors et identité forte

| Élément | Traçabilité |
| --- | --- |
| Roadmap | P07 / EPIC-0701 — Registry collectors et identité forte. |
| Domaine | `CollectorIdentity`, `DiscoveryCollector`, `DiscoveryScope`, `DiscoveryJobAuthorization`. |
| Application | `DiscoveryCollectorService` avec enregistrement, heartbeat, liste, désactivation et autorisation/rejet de jobs. |
| Infrastructure | `JsonDiscoveryRepository`, `PostgreSQLDiscoveryRepository`, persistance des scopes, empreintes et références Vault. |
| PostgreSQL | `0023_discovery_collector_registry.sql`, table `discovery_collectors` partitionnée par hash tenant, contraintes fingerprint/Vault/status et index GIN scopes. |
| Interfaces | CLI `openinfra discovery *`, API `/api/v1/discovery/collectors`, `/heartbeat`, `/jobs/authorize`, OpenAPI YAML. |
| Sécurité | Aucun secret collector en clair ; seules les références `vault://...` sont persistées ; l'empreinte certificat SHA-256 sert d'identité mTLS. |
| Acceptation | Un collector non enregistré, désactivé, présenté avec une empreinte différente ou hors scope ne peut recevoir aucun job. |
| Tests | `tests/unit/test_discovery_domain.py`, `tests/integration/test_discovery_collector_services.py`, `tests/integration/test_cli_discovery.py`, `tests/integration/test_http_api.py`, `tests/integration/test_postgresql_migration.py`. |

## v0.25.2 — Correctif CI requirements séparés

- Corrige le formatage Ruff restant sur deux tests d'intégration.
- Ajoute la séparation requirements production/dev/CI et les garde-fous `security_gate.py` associés.
- Conserve sans modification fonctionnelle le jalon P06 / EPIC-0602.

## v0.25.1 — Correctif CI/DevSecOps import XLSX sécurisé

- Trace `CI-FIX-0251-RUFF` : Ruff format/check validés sur `src`, `tests`, `scripts`, `docker`.
- Trace `CI-FIX-0251-BANDIT` : parsing XML XLSX migré vers `defusedxml`, alertes Bandit `B405/B314` corrigées sans `# nosec`.
- Trace `CI-FIX-0251-MYPY` : typage strict restauré sur services import, stockage JSON/PostgreSQL et API HTTP bulk.
- Trace `CI-FIX-0251-REGRESSION` : test de rejet des payloads XML à entités externes dans les fichiers XLSX.

## v0.25.0 — P06 / EPIC-0602 Import massif scalable

| Élément | Traçabilité |
| --- | --- |
| Roadmap | P06 / EPIC-0602 — Import massif scalable. |
| Domaine | `BulkImportReport`, `BulkImportCheckpoint`, `BulkImportMetrics`, `ImportReport`, `ImportRowIssue`, `ImportRowImpact`. |
| Application | `GenericImportService.bulk_import_dataset`, reprise par checkpoint, batches bornés et rapport persisté. |
| Infrastructure | `ImportDatasetParser.iter_rows`, streaming CSV, `JsonImportRepository`, `PostgreSQLImportRepository`. |
| PostgreSQL | `0020_bulk_import_framework.sql`, tables `bulk_import_jobs` et `bulk_import_checkpoints` partitionnées par hash tenant. |
| Interfaces | `openinfra import bulk-dataset`, `bulk-report`, `bulk-checkpoint`, `POST /api/v1/imports/bulk-datasets`, `GET /api/v1/imports/bulk-report`, `GET /api/v1/imports/bulk-checkpoint`. |
| Acceptation | Le mode bulk ne charge pas tout le CSV en mémoire, persiste un checkpoint et permet la reprise contrôlée. |
| Tests | `tests/unit/test_data_import_domain.py`, `tests/unit/test_import_parsers.py`, `tests/integration/test_import_services.py`, `tests/integration/test_cli_import.py`, `tests/integration/test_http_api.py`, `tests/integration/test_postgresql_migration.py`. |

## v0.21.0 — P05 / EPIC-0504 Détection conflits IPAM

- Roadmap : P05 / EPIC-0504.
- Domaine : `IpamConflict`, `ObservedDnsRecord`, `ObservedDhcpLease`.
- Service : `IpamConflictService`.
- Ports : observations DNS/DHCP et lecture des faits observés.
- Backends : JSON et PostgreSQL.
- Migration : `installers/migrations/postgresql/0018_ipam_conflict_detection.sql`.
- CLI : `observe-dns`, `observe-dhcp-lease`, `detect-conflicts`.
- API : `/api/v1/ipam/dns-observations`, `/api/v1/ipam/dhcp-leases`, `/api/v1/ipam/conflicts`.
- Tests : `tests/integration/test_ipam_conflict_services.py`, routes HTTP IPAM conflits, validations domaine IPAM conflits.

## v0.20.0 — P05 / EPIC-0503 VLAN/VXLAN/ASN/BGP fondation

- Roadmap : P05 / EPIC-0503.
- Domaine : `VlanGroup`, `Vlan`, `VxlanVni`, `AutonomousSystem`, `BgpPeer`, `NetworkIdentifierPolicy`.
- Application : `IpamModelService.define_vlan_group`, `define_vxlan_vni`, `define_vlan`, `define_asn`, `define_bgp_peer`, `network_bindings`.
- Ports : extension `IpamRepository` pour inventaire VLAN/VXLAN/ASN/BGP.
- Infrastructure : `JsonIpamRepository`, `PostgreSQLIpamRepository`.
- Interfaces : commandes `openinfra ipam define-vlan-group`, `define-vxlan-vni`, `define-vlan`, `define-asn`, `define-bgp-peer`, `network-bindings`.
- API : `/api/v1/ipam/vlan-groups`, `/vxlan-vnis`, `/vlans`, `/asns`, `/bgp-peers`, `/network-bindings`.
- Migration : `installers/migrations/postgresql/0017_ipam_networking_foundation.sql`.
- Tests : domaine réseau IPAM, cohérence VRF/VLAN/VNI/ASN, persistance JSON, mapping PostgreSQL, CLI/API et non-régression CI.
- Production : runtime serveur natif inchangé ; Docker reste facultatif pour smoke local.

## v0.19.0 — P05 / EPIC-0502 Allocation IP transactionnelle

- Roadmap : P05 / EPIC-0502.
- Domaine : `IpAllocationPolicy`, `IpRange`, `IpReservation`, `AllocationRequest`, `AllocationResult`.
- Application : `IpamAllocationService.allocate`.
- Ports : `IpamRepository.acquire_allocation_lock`, réservations, plages, adresses suivies et audit.
- Infrastructure : `JsonIpamRepository`, `PostgreSQLIpamRepository`.
- Interfaces : `openinfra ipam allocate`, `POST /api/v1/ipam/allocate`.
- Migration : `installers/migrations/postgresql/0016_ipam_transactional_allocation.sql`.
- Tests : allocation idempotente, plages allocation/exclusion/réservation, adresses préexistantes, 100 allocations concurrentes sans collision, verrou PostgreSQL simulé, CLI/API de non-régression.
- Production : runtime serveur natif inchangé ; Docker reste facultatif pour smoke local.


## v0.22.0 — P05 / EPIC-0505 UI IPAM opérationnelle

| Exigence | Implémentation | Validation |
|---|---|---|
| UI IPAM opérationnelle | `IpamUiService`, `IpamUiViewModel`, `IpamUiHtmlRenderer` | `tests/integration/test_ipam_ui_services.py` |
| Recherche IPAM | `openinfra ipam ui-search`, `/api/v1/ipam/ui-search` | tests CLI/API et smoke CI |
| Assistant réservation | `openinfra ipam reservation-wizard`, `/api/v1/ipam/reservation-wizard` | dry-run + apply testés |
| Dashboard capacité/conflits | `openinfra ipam ui-dashboard`, `/ui/ipam` | rendu JSON/HTML testé |


## v0.22.2 — Correctif runtime Docker/PostgreSQL

| Élément | Couverture |
|---|---|
| Migrations PostgreSQL audit | `0012`, `0013`, `0014` indexent `audit_events.created_at` et non une colonne inexistante. |
| Runtime Docker facultatif | `Dockerfile` sans healthcheck global ; healthcheck API restreint à `compose.yaml` service `api`. |
| Tags Docker | `.env.example`, `compose.yaml`, `scripts/docker_environment.py` alignés sur `0.22.2`. |


## v0.22.2 — pgAdmin4 lab Docker Compose

| Élément | Couverture |
|---|---|
| Administration BDD lab | Service Compose `pgadmin` exposé sur bind local configurable. |
| Préconfiguration PostgreSQL | `docker/pgadmin/servers.json` référence l’hôte Compose `postgres` et la base `openinfra`. |
| Secrets lab | `.env.example` expose les clés sans valeur sensible ; `scripts/docker_environment.py` génère les secrets localement. |
| Persistance | Volume dédié `openinfra-pgadmin-data`. |

## v0.22.3 — Correctif migration IPAM PostgreSQL

| Élément | Traçabilité |
| --- | --- |
| Migration `0015` | Ajout/backfill/contrainte `prefixes.family` avant `idx_prefixes_vrf_family`. |
| Qualité | `scripts/quality_gate.py` et `tests/integration/test_runtime_docker_environment.py` bloquent la régression. |

## v0.23.0 — P05 / EPIC-0506 DDI intégration baseline

| Élément | Traçabilité |
| --- | --- |
| Roadmap | P05 / EPIC-0506 — DDI intégration baseline. |
| Domaine | `DdiProvider`, `DdiChange`, `DdiDivergence`, `DdiReservationPreview`. |
| Application | `IpamDdiService.preview_reservation`. |
| Ports | `DdiConnector`, `DdiPreviewContext`. |
| Infrastructure | `BindDdiConnector`, `PowerDnsDdiConnector`, `KeaDdiConnector`, `DdiConnectorFactory`. |
| Interfaces | `openinfra ipam ddi-preview`, `POST /api/v1/ipam/ddi-preview`. |
| Acceptation | Une réservation IPAM génère un plan DNS/DHCP dry-run, les divergences sont visibles et un rollback compensatoire est fourni. |
| Tests | `tests/unit/test_domain_ipam_ddi.py`, `tests/integration/test_ipam_ddi_services.py`. |

## v0.23.1 — Correctif runtime API discovery

| Élément | Couverture |
| --- | --- |
| Route racine | `GET /` retourne un document JSON de découverte au lieu de `not_found`. |
| Route API v1 | `GET /api/v1` expose le point d’entrée canonique de l’API versionnée. |
| Logs runtime | `openinfra-api` écrit `openinfra_api_started` sur stdout au démarrage. |
| Tests | `tests/integration/test_http_api.py` et `tests/integration/test_runtime_docker_environment.py` couvrent les nouveaux contrats et empêchent le retour du smoke Docker vers une version codée en dur. |

## v0.26.0 — P06 EPIC-0603 Exports asynchrones et signés

La v0.26.0 ajoute un cycle d’export tracé de bout en bout : job non bloquant, exécution worker séparée, artefact CSV/JSON/XLSX, digest SHA-256, signature HMAC-SHA256 et vérification d’intégrité avant téléchargement. Les contrats exposés sont `openinfra export request|run|report|artifact` et `/api/v1/exports/jobs`, `/api/v1/exports/run`, `/api/v1/exports/artifact`.

Traçabilité :

- domaine : `src/openinfra/domain/data_export.py` ;
- application : `src/openinfra/application/export_services.py` ;
- ports : `ExportRepository` ;
- infrastructure : `JsonExportRepository`, `PostgreSQLExportRepository`, migration `0021_export_framework.sql` ;
- interfaces : CLI `export`, API HTTP `/api/v1/exports/*`, OpenAPI YAML ;
- tests : `tests/integration/test_export_services.py`, `tests/integration/test_cli_export.py`, `tests/integration/test_http_api.py`, `tests/integration/test_postgresql_migration.py`.


## v0.27.0 — P06 EPIC-0604 Migration depuis référentiels existants

La v0.27.0 ajoute une simulation de migration depuis Device42, NetBox, Nautobot, GLPI et CSV générique. Les exigences couvertes sont la préparation de mappings contrôlés, le dry-run sans écriture, le rapport d’écarts complet, la persistance du plan et la reprise par `job_id`. Les contrats exposés sont `openinfra import migration-template|migration-plan|migration-report` et `/api/v1/imports/migration-template`, `/api/v1/imports/migration-plans`, `/api/v1/imports/migration-report`.


## v0.29.14 — P09 RSOT Quality & Certification

| Élément | Couverture |
|---|---|
| RSOT Quality service | `src/openinfra/application/it_resources_management_quality_services.py` |
| CLI | `openinfra rsot quality-object`, `openinfra rsot quality-summary`, alias `sot` |
| API | `/api/v1/rsot/quality/object`, `/api/v1/rsot/quality/summary` |
| Dashboard | opérations RSOT quality dans `interfaces/rendering/static` |
| RBAC | permission `rsot.quality.read` |
| Tests | `tests/integration/test_ri_quality_services.py`, contrat HTTP RSOT quality |

## v0.29.15 — openinfra-web Bootstrap Dashboard

| Domaine | Alignement |
| --- | --- |
| CDC | `REQ-00746` impose le thème Bootstrap 5 Dashboard complet, le header principal unique adapté et les assets Bootstrap locaux. |
| Frontend | `web/src/main.jsx` et `interfaces/rendering/static` exposent Dashboard, RSOT, IPAM, DCIM, Discovery et Sécurité dans le header et la sidebar. |
| Sécurité | Bootstrap est servi localement, le dashboard reste API-only, et aucun DSN PostgreSQL ni secret backend n'est exposé au navigateur. |
| Tests | `TST-WEB-049`, `scripts/validate_frontend.py` et `tests/integration/test_openinfra_web.py` valident les assets, le header, la sidebar et la non-exposition de secrets. |

## v0.29.16 — openinfra-web formulaires métier et trust server-side

| Axe | Alignement |
|---|---|
| Frontend | `interfaces/rendering/static` et `web/src/main.jsx` remplacent les champs génériques par des inputs métier explicites et déplacent les opérations dans les accordéons latéraux. |
| Sécurité | `openinfra-web` ne demande pas de token API à l'opérateur et ne relaie pas `Authorization` venant du navigateur. |
| Runtime | `[web_database]` dans `install.ini` alimente `OPENINFRA_WEB_DATABASE_*_REF` dans `/opt/openinfra/config/openinfra.conf`. |
| CDC | `REQ-00747` et `TST-WEB-050` couvrent le contrat formulaires typés, version package fiable et trust server-side. |

## v0.29.51 — ITAM licences logicielles et contrats

| Élément | Couverture |
| --- | --- |
| CDC | `REQ-00794` / `TST-WEB-095` |
| Roadmap | P12 / EPIC-1205 / `TST-P12-ITAM-SOFTWARE-LICENSES` |
| Domaine | `SoftwareLicenseEntitlement`, `SoftwareLicenseComplianceReport` |
| Application | `RegisterSoftwareLicenseCommand`, `UpdateSoftwareLicenseAssignmentCommand`, `GetSoftwareLicenseCommand`, `GetSoftwareLicenseComplianceCommand` |
| API | `/api/v1/itam/software-license`, `/api/v1/itam/software-license/assignment`, `/api/v1/itam/software-license/compliance` |
| CLI | `openinfra itam register-software-license`, `update-license-assignment`, `software-license`, `software-license-compliance` |
| PostgreSQL | `0028_itam_software_license_entitlements.sql` |
| Tests | `tests/integration/test_itam_software_license_services.py` |


## v0.29.59 — rollback conflict-aware imports massifs

| Élément | Traçabilité |
| --- | --- |
| Roadmap | P13 / EPIC-1305 — rollback opérable des imports massifs. |
| CDC | `REQ-00802`, `TST-WEB-103`. |
| Domaine | `BulkImportRollbackAction`, `BulkImportRollbackItem`, `BulkImportRollbackReport`. |
| Application | `GenericImportService.bulk_import_rollback`. |
| Interfaces | `openinfra import bulk-rollback`, `POST /api/v1/imports/bulk-rollback`, opération web **Rollback import massif**. |
| OpenAPI/discovery | `/api/v1/imports/bulk-rollback`, `imports.bulk_rollback`. |
| Tests | `tests/integration/test_import_services.py`, `tests/integration/test_cli_import.py`, `tests/integration/test_http_api.py`, `tests/integration/test_openinfra_web.py`. |
| Acceptation | Dry-run par défaut, restauration versionnée, mise en retrait sans suppression physique, conflit bloqué par défaut, publication CLI/API/web/OpenAPI/discovery. |


## v0.29.63 — Enterprise agent bootstrap plan

OpenInfra prepares Enterprise discovery agents through `openinfra discovery agent-bootstrap-plan` and `POST /api/v1/discovery/agent-bootstrap-plan`. The contract renders an operator-reviewed `openinfra-agent.service` systemd unit, an agent configuration document, mTLS requirements, vault-only enrollment references and API result publication endpoints. No installation is executed and no secret is materialized by OpenInfra during plan generation.

## v0.29.64 — UX entités propriétaires ITAM

Traçabilité : exigence UI de remplacement du libellé `Tenant` par `Entité propriétaire`, usage de `Organisation` lors de la création d’une entité propriétaire, et obligation de rendu `select` pour les références tenant dans les autres formulaires web. Les contrats techniques restent inchangés pour préserver la compatibilité ascendante.
## v0.29.65 — DCIM sites, dépendances et responsive mobile

La livraison introduit le référentiel de sites DCIM avec retrait logique et publication du catalogue hiérarchique exploité par le portail. Les formulaires web ne rendent plus les références de localisation DCIM en texte libre : le champ est un `select` alimenté par `/api/v1/dcim/topology-catalog`. La sidebar et les cartes sont adaptées aux breakpoints tablette et smartphone.

