---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Synthèse des exigences

## Volumétrie documentaire

- Exigences : 308
- Cas d’usage : 10
- Tests/preuves : 130
- Entités logiques : 319
- Risques : 10

## Répartition par domaine

| Domaine | Libellé | Nombre exigences |
| --- | --- | --- |
| AI | IA & Automatisation | 22 |
| API | API & Intégrations | 23 |
| DATA | Données & PostgreSQL | 14 |
| DCIM | Data Center Infrastructure Management | 28 |
| DEP | Dependency Mapping | 22 |
| DISC | Discovery distribué | 35 |
| IPAM | IP Address Management Enterprise++ | 49 |
| ITAM | IT Asset Management | 21 |
| OPS | Administration & exploitation | 35 |
| QA | Qualité & validation | 16 |
| SEC | Sécurité | 22 |
| RSOT | RSOT (Ressource Source of Truth) | 21 |

Le fichier `11-Matrices/Exigences.csv` constitue la référence contractuelle des exigences.


## Extension v4 — synthèse des exigences ajoutées

La version 4.0.0 ajoute 180 exigences réparties sur les volumes V13 à V24. Ces exigences sont contractuelles et rattachées à des cas d’usage, tests et critères d’acceptation.

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


## Extension v4.10.0 — Licence runtime offline

- **REQ-00846** — Chaque installation Pro ou Entreprise doit posséder une identité Ed25519 locale immuable et produire une demande d’activation signée.
- **REQ-00847** — L’autorité de licence doit émettre les entitlements hors ligne avec une clé privée Ed25519 obligatoirement chiffrée ; seul le trust bundle public est déployé.
- **REQ-00848** — L’entitlement doit être lié au UUID de licence, au UUID d’installation, à l’entreprise, à l’édition, au quota d’hôtes et à ses dates UTC.
- **REQ-00849** — La validation doit refuser schémas inconnus, UUID ou dates invalides, clés non Ed25519, signatures malformées, autorités non approuvées et documents persistés corrompus.
- **REQ-00850** — OpenInfra doit prendre en charge bootstrap, activation initiale et renouvellement sans modifier l’identité d’installation.
- **REQ-00851** — Après expiration, Pro et Entreprise doivent disposer d’une période de grâce fixe de 30 jours, puis toutes les opérations métier sont bloquées.
- **REQ-00852** — Le runtime doit mémoriser la dernière heure UTC observée et invalider une licence lors d’un recul d’horloge supérieur à la tolérance contractuelle.
- **REQ-00853** — Le quota d’hôtes signé doit être vérifié sous le même verrou transactionnel que la création d’un équipement géré.
- **REQ-00854** — Lorsque l’enforcement est actif, la CLI et l’API doivent refuser les opérations métier dans les états bloquants ; l’API répond HTTP 402 avec un diagnostic sans secret.
- **REQ-00855** — Les installateurs serveur Pro et Entreprise doivent demander UUID, entreprise et quota, générer les clés en permissions minimales et activer l’enforcement ; Lite reste exemptée.
- **REQ-00856** — Les backends JSON, PostgreSQL et Oracle doivent implémenter le même contrat de licence, avec migration additive 0059 et verrou transactionnel.
- **REQ-00857** — Les portails React et statique doivent afficher les notifications de licence en français et anglais, au démarrage puis au moins chaque heure, selon WCAG 2.2 AA.
- **REQ-00858** — Les sources, wheels, sdists, images, installateurs et preuves ne doivent contenir aucune clé privée d’autorité ; les écritures sensibles sont atomiques.
- **REQ-00859** — REL-13 doit être bloquée par GATE-12 tant que les sept preuves cryptographie, stockage, enforcement, interfaces, installateur, notifications et exclusion de clé privée ne passent pas.

## Extension v4.11.0 — Canonicalisation RSOT définitive

- **REQ-00860** — La release 0.34.6 retire définitivement les alias ITRM, RI et SOT, conserve toutes les capacités RSOT et fournit un guide de migration.
