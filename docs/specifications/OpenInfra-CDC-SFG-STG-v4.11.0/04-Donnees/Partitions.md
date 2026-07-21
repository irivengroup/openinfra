---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Partitionnement, indexation et cycle de vie des données

## Règle impérative

La base ne doit jamais reposer sur une table monolithique non partitionnée pour les données volumineuses. Toute table à forte croissance doit être conçue avec partitionnement natif PostgreSQL, index adaptés par partition, pagination obligatoire, requêtes bornées, archivage contrôlé, rétention configurable, séparation hot/warm/cold, lectures scalables via réplicas et jobs batch asynchrones.

## Stratégies de partitionnement

| Type de donnée | Stratégie | Exemple |
|---|---|---|
| Audit | temps + tenant | `audit_event_2026_07_tenant_001` |
| Discovery | temps + tenant + hash cible | `discovery_result_tenant_001_2026_07` |
| IP history | VRF + temps | `ip_history_vrf_001_2026` |
| Graph edges | hash | `dependency_edge_hash_00` |
| Sensor metrics | temps + salle | `sensor_metric_2026_07_room_001` |
| DHCP leases | temps + serveur | `dhcp_lease_2026_07_srv_01` |
| Cloud metadata | tenant + provider + temps | `cloud_metadata_aws_tenant001_2026_07` |

## Indexation par partition

- B-tree pour identifiants, timestamps et statuts.
- BRIN pour grandes partitions temporelles append-only.
- GIN pour JSONB contrôlé.
- GiST/SP-GiST pour `inet` et `cidr`.
- Trigram pour recherche texte.
- Index partiels pour données actives.
- Index composites alignés sur les filtres API.
- Index couvrants pour requêtes fréquentes.

## Gouvernance

Les index inutilisés doivent être détectés, analysés et supprimés seulement après validation. Les index manquants doivent être proposés par analyse de requêtes lentes et validés par benchmark.
