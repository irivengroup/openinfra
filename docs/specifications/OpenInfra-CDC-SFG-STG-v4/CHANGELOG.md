# CHANGELOG

## 4.0.0 — Extension fonctionnelle entreprise

### Ajouté

- Volumes V13 à V24 : gouvernance de la donnée, qualité, flux réseau, certificats/PKI, conformité réseau, FinOps, Field Operations, simulation/migration, GreenOps, SBOM/vulnérabilités, Kubernetes avancé et policy engine.
- Vues fonctionnelles dédiées dans `02-Fonctionnel/` pour chaque nouveau volume.
- Exigences REQ supplémentaires numérotées et vérifiables.
- Cas d’usage UC supplémentaires.
- Tests TST-REQ supplémentaires.
- Entités de dictionnaire supplémentaires.
- Risques et conformité supplémentaires.
- Addendum CCTP/CdCF v4.

### Maintenu

- Exclusion stricte d’un ITSM intégré.
- PostgreSQL Cluster comme persistance transactionnelle principale.
- Exigences de partitionnement, hot/warm/cold, concurrence, résilience, sécurité et observabilité.

---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# CHANGELOG

## 3.0.0 — 2026-07-02

### Changements majeurs

- Transformation du CDC v2 en dossier SFG/STG versionné.
- Ajout d’une structure CCTP/CdCF prête pour consultation intégrateurs.
- Ajout de 12 volumes d’architecture et de spécifications.
- Ajout d’exigences numérotées `REQ-xxxxx` avec priorités N1/N2.
- Ajout des cas d’usage `UC-xxxx` et tests `TST-xxxx`.
- Ajout d’une matrice de traçabilité exigences/cas d’usage/tests.
- Ajout du modèle de données logique avec plus de 250 entités.
- Renforcement PostgreSQL : cluster HA, partitionnement, hot/warm/cold, PITR, réplicas, observabilité.
- Renforcement performance/concurrence : p95/p99, API bornées, import/export asynchrones, idempotence.
- Ajout des exigences IA et automatisation : RAG, suggestions, anomalies, gouvernance humaine.
- Ajout d’ADR/RFC et diagrammes C4/ERD/architecture.

### Compatibilité

Cette version conserve le périmètre v2 : Source of Truth, DCIM, ITAM, Discovery, Dependency Mapping, IPAM avancé et exclusion ITSM intégrée. Elle renforce la granularité documentaire et contractuelle.
