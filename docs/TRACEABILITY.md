# Traçabilité initiale code ↔ exigences source

| Exigence source | Implémentation livrée | Preuve |
|---|---|---|
| PostgreSQL Cluster socle principal | Migration `migrations/postgresql/0001_bootstrap.sql` partitionnée/indexée | `test_postgresql_migration.py`, `openinfra database render-migration` |
| Pas d'ITSM intégré | Aucun module ITSM ; validation ADR source | `ContractualSpecValidator`, `openinfra spec validate` |
| Plans 2D salle et rack elevation | `RoomPlan2D`, `RackElevation`, `DcimVisualizationService` | `test_dcim_visualization_services.py`, `openinfra dcim room-plan`, `openinfra dcim rack-elevation`, OpenAPI DCIM |
| Localisation physique ligne/colonne | `Room`, `Rack`, `EquipmentLocation`, `DcimLocationService` | `test_domain_dcim.py`, `test_services.py`, `openinfra dcim locate` |
| Allocation IP transactionnelle et idempotente | `IpamAllocationService`, `JsonUnitOfWork`, `IpAllocationPolicy` | `test_domain_ipam.py`, `test_services.py`, `openinfra ipam allocate` |
| Audit des opérations critiques | `AuditEvent`, `JsonAuditRepository` | tests d'intégration services et roundtrip audit |
| Architecture hexagonale / POO | packages `domain`, `application`, `infrastructure`, `interfaces` | `test_architecture.py`, `scripts/quality_gate.py` |
| CLI/API/documentation/CI alignées | CLI, API HTTP, OpenAPI, docs, GitHub Actions | `test_cli.py`, `test_http_api.py`, `.github/workflows/ci.yml` |
