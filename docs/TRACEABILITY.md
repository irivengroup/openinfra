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
- Migration : `migrations/postgresql/0018_ipam_conflict_detection.sql`.
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
- Migration : `migrations/postgresql/0017_ipam_networking_foundation.sql`.
- Tests : domaine réseau IPAM, cohérence VRF/VLAN/VNI/ASN, persistance JSON, mapping PostgreSQL, CLI/API et non-régression CI.
- Production : runtime serveur natif inchangé ; Docker reste facultatif pour smoke local.

## v0.19.0 — P05 / EPIC-0502 Allocation IP transactionnelle

- Roadmap : P05 / EPIC-0502.
- Domaine : `IpAllocationPolicy`, `IpRange`, `IpReservation`, `AllocationRequest`, `AllocationResult`.
- Application : `IpamAllocationService.allocate`.
- Ports : `IpamRepository.acquire_allocation_lock`, réservations, plages, adresses suivies et audit.
- Infrastructure : `JsonIpamRepository`, `PostgreSQLIpamRepository`.
- Interfaces : `openinfra ipam allocate`, `POST /api/v1/ipam/allocate`.
- Migration : `migrations/postgresql/0016_ipam_transactional_allocation.sql`.
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
