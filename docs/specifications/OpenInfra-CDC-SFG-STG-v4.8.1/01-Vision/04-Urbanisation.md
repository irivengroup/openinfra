---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Urbanisation

## Synthèse

OpenInfra s’insère dans le SI comme référentiel technique authoritative source, alimentant ITSM, SIEM, IAM, cloud, DNS/DHCP, CMDB externe et automatisation.

## Principes de décision

- Les composants critiques doivent être open source ou remplaçables par une alternative ouverte.
- Les dépendances lourdes doivent être justifiées par un besoin métier ou opérationnel mesurable.
- Les fonctionnalités doivent être testables automatiquement.
- Les données critiques doivent être persistées dans PostgreSQL Cluster.
- Les traitements longs doivent être asynchrones et observables.
- Les APIs doivent être stables, documentées et versionnées.
- La compatibilité ascendante est préservée sauf décision d’architecture formelle.

## Contraintes d’entreprise

- Multi-tenant logique.
- Séparation des environnements.
- RBAC/ABAC.
- Audit immuable.
- Performances mesurées.
- Exploitabilité Kubernetes.
- Sauvegarde et restauration testées.
- Cartographie et traçabilité des dépendances.
