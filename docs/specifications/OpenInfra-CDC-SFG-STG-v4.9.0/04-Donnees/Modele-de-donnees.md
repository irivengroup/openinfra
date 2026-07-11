---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Modèle de données logique

## Principes du modèle

Le modèle de données est organisé par domaines afin d’éviter une base confuse et difficile à maintenir. Chaque domaine dispose d’un schéma PostgreSQL dédié, de contraintes explicites, d’index alignés sur les requêtes et de règles de partitionnement pour les tables massives.

## Schémas logiques

| Schéma | Nombre entités |
| --- | --- |
| core | 29 |
| rsot | 31 |
| dcim | 49 |
| ipam | 50 |
| discovery | 36 |
| dependency | 29 |
| itam | 26 |
| security | 25 |
| ops | 26 |
| ai | 18 |

## Entités majeures

Le dictionnaire complet est disponible dans `04-Donnees/Dictionnaire.csv`. Il contient 319 entités logiques couvrant core, RSOT (Ressource Source of Truth), DCIM, IPAM, discovery, dependency mapping, ITAM, sécurité, exploitation et IA.

## Règles transverses

- Les identifiants techniques sont immuables.
- Les noms métiers sont uniques dans un contexte explicitement défini.
- Les suppressions physiques sont interdites pour les objets audités, sauf purge conforme à une politique de rétention.
- Les relations critiques sont typées et historisées.
- Les données volumineuses sont partitionnées.
- Les tables transactionnelles ne doivent pas servir d’entrepôt analytique illimité.
- Les états consolidés sont séparés des observations brutes.
- Les clés de partition sont stables et documentées.

## Tables massives obligatoires

- `audit.audit_event`
- `discovery.discovery_observation`
- `discovery.scan_result`
- `history.object_version`
- `dependency.dependency_edge`
- `dependency.flow_observation`
- `ipam.ip_allocation_history`
- `ipam.dhcp_lease_history`
- `dcim.sensor_metric`
- `security.security_finding`
- `ops.performance_benchmark`
- `core.event_outbox`

## Stratégie hot / warm / cold

| Niveau | Description | Stockage recommandé | Usage |
|---|---|---|---|
| Hot | données récentes et opérationnelles | PostgreSQL primaire + réplicas | API, UI, opérations quotidiennes |
| Warm | historique consultable | partitions compressées, réplica reporting | audits, tendances, restitution |
| Cold | archives peu consultées | S3 compatible, Parquet, entrepôt analytique | conformité, historique long terme |

## Contraintes d’acceptation

Le modèle est accepté si les tables massives sont partitionnées, les contraintes critiques existent, les index sont alignés sur les requêtes, les migrations sont testées et la restauration de partitions est démontrée.
