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
