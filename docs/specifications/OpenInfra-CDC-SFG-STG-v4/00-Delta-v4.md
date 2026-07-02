# Delta fonctionnel v4 — OpenInfra Enterprise

**Version :** 4.0.0  
**Objectif :** intégrer les améliorations fonctionnelles de niveau entreprise au dossier SFG/STG v3 sans modifier l’exclusion ITSM.

## Nouveaux volumes ajoutés

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

## Nouvelles vues fonctionnelles ajoutées

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

## Effets sur le périmètre

- Le périmètre Source of Truth est enrichi par la gouvernance, la qualité et la certification des données.
- Le périmètre sécurité est enrichi par les flux, certificats, secrets référencés, SBOM, vulnérabilités contextualisées et policy engine.
- Le périmètre DCIM est enrichi par les opérations terrain, GreenOps et simulation d’impact.
- Le périmètre cloud-native est enrichi par Kubernetes avancé et mapping bout-en-bout.
- Le périmètre financier est enrichi par FinOps, showback et chargeback.
- Le périmètre migration est enrichi par simulation, move groups, vagues et readiness score.

## Maintien des contraintes de niveau 1

- PostgreSQL Cluster reste la persistance transactionnelle principale.
- Les tables massives restent partitionnées et compatibles hot/warm/cold.
- Les APIs volumineuses restent paginées, bornées et filtrées.
- Les traitements longs restent asynchrones et idempotents.
- Aucun module ITSM natif n’est introduit.
- Les exigences nouvelles sont rattachées à des cas d’usage, tests et critères d’acceptation.
