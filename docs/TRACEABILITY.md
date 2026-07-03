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
