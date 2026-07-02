
# OpenInfra — Dossier SFG/STG, CCTP/CdCF et architecture entreprise

**Version :** 4.0.0  
**Date :** 2026-07-02  
**Statut :** version enrichie entreprise, prête pour cadrage, consultation d’intégrateurs, lancement de conception détaillée et pilotage de développement.  
**Périmètre :** Source of Truth, DCIM, ITAM, Discovery, Dependency Mapping, IPAM Enterprise++, sécurité, API, IA/automatisation, administration, qualité.  
**Exclusion structurante :** aucune fonction ITSM intégrée. Les outils ITSM sont intégrés par connecteurs externes uniquement.

## Contenu du livrable

Ce référentiel documentaire transforme le CDC initial en dossier industriel structuré :

- 12 volumes SFG/STG alignés sur la structure demandée ;
- CCTP/CdCF exploitable en appel d’offres ;
- exigences numérotées `REQ-xxxxx` ;
- cas d’usage `UC-xxxx` ;
- tests `TST-xxxx` ;
- matrice de traçabilité exigences → cas d’usage → tests ;
- modèle de données logique avec plus de 250 entités ;
- exigences PostgreSQL Cluster, partitionnement, hot/warm/cold et objectifs de performance ;
- ADR/RFC d’architecture ;
- diagrammes C4, PlantUML, Mermaid et ERD ;
- OpenAPI 3.1 et schéma GraphQL de référence ;
- registre des risques ;
- critères d’acceptation contractuels.

## Arborescence principale

```text
OpenInfra-CDC-SFG-STG-v4/
├── 00-README.md
├── 00-Index-general.md
├── 00-Note-de-cadrage-CCTP-CdCF.md
├── 01-Vision/
├── 02-Fonctionnel/
├── 03-Technique/
├── 04-Donnees/
├── 05-Tests/
├── 06-Exploitation/
├── 07-Architecture-Entreprise/
├── 08-RFC-ADR/
├── 09-API/
├── 10-Diagrammes/
├── 11-Matrices/
├── Volumes/
├── Annexes/
└── scripts/
```

## Règles contractuelles majeures

1. PostgreSQL Cluster est obligatoire comme socle transactionnel principal.
2. Les tables massives ne doivent jamais être monolithiques non partitionnées.
3. L’architecture doit supporter plus de 10 milliards d’entrées sans refonte majeure.
4. Toute lecture volumineuse doit être paginée et bornée.
5. Tout import/export massif doit être asynchrone.
6. Toute allocation IP doit être transactionnelle, idempotente et sûre en concurrence.
7. La localisation physique en salle impose ligne, colonne et coordonnées X/Y/Z lorsque disponibles.
8. Les opérations critiques doivent être auditées et traçables.
9. Les exigences N1 sont obligatoires et non négociables.
10. Les critères d’acceptation et tests associés conditionnent la réception.

## Validation locale du dossier

```bash
python3 scripts/validate_docs.py
```

Le script vérifie la présence des documents essentiels, l’unicité des exigences, l’absence de marqueurs de brouillon et la cohérence minimale des matrices.


## Extension v4.0.0 — améliorations fonctionnelles entreprise

La version 4.0.0 ajoute douze volumes fonctionnels avancés, sans introduire d’ITSM intégré :

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

Le dossier v4 ajoute également les exigences, entités, cas d’usage, tests, risques et lignes de conformité correspondants dans les matrices contractuelles.
