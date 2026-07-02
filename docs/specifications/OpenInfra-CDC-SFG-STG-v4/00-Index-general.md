---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 4.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Index général du dossier

## Objectif

Ce document sert d’index maître pour naviguer dans le référentiel OpenInfra v3.0.0. Il sépare les documents de vision, les spécifications fonctionnelles générales, les spécifications techniques générales, les matrices contractuelles et les annexes de validation.

## Volumes normatifs

| Code | Volume | Fichier |
| --- | --- | --- |
| V01 | Vision & Architecture | Volumes/V01-Vision-et-Architecture.md |
| V02 | Référentiel Source of Truth | Volumes/V02-Référentiel-Source-of-Truth.md |
| V03 | IPAM Enterprise++ | Volumes/V03-IPAM-Enterprise++.md |
| V04 | Discovery | Volumes/V04-Discovery.md |
| V05 | DCIM | Volumes/V05-DCIM.md |
| V06 | Cartographie & Dépendances | Volumes/V06-Cartographie-et-Dépendances.md |
| V07 | ITAM | Volumes/V07-ITAM.md |
| V08 | Sécurité | Volumes/V08-Sécurité.md |
| V09 | API & Intégrations | Volumes/V09-API-et-Intégrations.md |
| V10 | IA & Automatisation | Volumes/V10-IA-et-Automatisation.md |
| V11 | Administration | Volumes/V11-Administration.md |
| V12 | Qualité | Volumes/V12-Qualité.md |

## Documents de pilotage

- `00-Note-de-cadrage-CCTP-CdCF.md` : périmètre contractuel et clauses techniques.
- `11-Matrices/Exigences.csv` : exigences numérotées.
- `11-Matrices/Traceabilite.csv` : traçabilité exigences → cas d’usage → tests.
- `11-Matrices/Registre-risques.csv` : risques projet, produit, sécurité, performance, exploitation.
- `04-Donnees/Dictionnaire.csv` : dictionnaire logique des entités.
- `08-RFC-ADR/` : décisions d’architecture et RFC structurants.
- `10-Diagrammes/` : diagrammes C4, ERD et topologies.

## Convention d’identification

- `REQ-xxxxx` : exigence contractuelle.
- `UC-xxxx` : cas d’usage.
- `TST-xxxx` : test ou preuve de validation.
- `ADR-xxxx` : décision d’architecture.
- `RFC-xxxx` : proposition structurante ou protocole de conception.
- `RISK-xxxx` : risque suivi.


## Volumes v4 ajoutés

- [Volume 13 — Gouvernance de la donnée et sources autoritatives](Volumes/V13-Gouvernance-de-la-donnee.md)
- [Volume 14 — Qualité, certification et réconciliation des données](Volumes/V14-Qualite-certification-reconciliation.md)
- [Volume 15 — Flux réseau, matrices de flux et segmentation](Volumes/V15-Flux-reseau-matrices-flux.md)
- [Volume 16 — Certificats, PKI et secrets référencés](Volumes/V16-Certificats-PKI-secrets-references.md)
- [Volume 17 — Conformité réseau et configuration attendue](Volumes/V17-Conformite-reseau-configuration-attendue.md)
- [Volume 18 — FinOps, coûts, showback et chargeback](Volumes/V18-FinOps-couts-chargeback.md)
- [Volume 19 — Field Operations et mobilité datacenter](Volumes/V19-Field-Operations-mobilite-datacenter.md)
- [Volume 20 — Simulation, analyse d’impact et migration planning](Volumes/V20-Simulation-impact-migration-planning.md)
- [Volume 21 — GreenOps et capacité énergétique](Volumes/V21-GreenOps-capacite-energetique.md)
- [Volume 22 — SBOM, vulnérabilités et exposition contextualisée](Volumes/V22-SBOM-vulnerabilites-exposition.md)
- [Volume 23 — Kubernetes avancé et mapping cloud-native](Volumes/V23-Kubernetes-avance-cloud-native-mapping.md)
- [Volume 24 — Policy Engine et conformité continue](Volumes/V24-Policy-Engine-conformite-continue.md)

## Vue fonctionnelle v4 ajoutée

- [Fonctionnel — Gouvernance de la donnée et sources autoritatives](02-Fonctionnel/13-Gouvernance-de-la-donnee.md)
- [Fonctionnel — Qualité, certification et réconciliation des données](02-Fonctionnel/14-Qualite-certification-reconciliation.md)
- [Fonctionnel — Flux réseau, matrices de flux et segmentation](02-Fonctionnel/15-Flux-reseau-matrices-flux.md)
- [Fonctionnel — Certificats, PKI et secrets référencés](02-Fonctionnel/16-Certificats-PKI-secrets-references.md)
- [Fonctionnel — Conformité réseau et configuration attendue](02-Fonctionnel/17-Conformite-reseau-configuration-attendue.md)
- [Fonctionnel — FinOps, coûts, showback et chargeback](02-Fonctionnel/18-FinOps-couts-chargeback.md)
- [Fonctionnel — Field Operations et mobilité datacenter](02-Fonctionnel/19-Field-Operations-mobilite-datacenter.md)
- [Fonctionnel — Simulation, analyse d’impact et migration planning](02-Fonctionnel/20-Simulation-impact-migration-planning.md)
- [Fonctionnel — GreenOps et capacité énergétique](02-Fonctionnel/21-GreenOps-capacite-energetique.md)
- [Fonctionnel — SBOM, vulnérabilités et exposition contextualisée](02-Fonctionnel/22-SBOM-vulnerabilites-exposition.md)
- [Fonctionnel — Kubernetes avancé et mapping cloud-native](02-Fonctionnel/23-Kubernetes-avance-cloud-native-mapping.md)
- [Fonctionnel — Policy Engine et conformité continue](02-Fonctionnel/24-Policy-Engine-conformite-continue.md)
