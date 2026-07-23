---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Architecture cible

## Synthèse

L’architecture cible repose sur APIs stateless, PostgreSQL Cluster, workers spécialisés, bus d’événements, cache, stockage objet, observabilité et intégrations externes.

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

## Architecture d’exécution Pro et Entreprise — v4.9.0

Le plan de contrôle reste un monolithe modulaire. Les interfaces API et Web sont stateless et servies par ASGI. Les réplicas sont placés derrière un load balancer ; PgBouncer protège PostgreSQL ; les lectures non critiques peuvent utiliser des réplicas ; les traitements longs utilisent workers, outbox et stockage objet. La séparation en microservices n’est autorisée qu’après mesure d’un besoin d’isolation, de cadence ou de scalabilité indépendant.
