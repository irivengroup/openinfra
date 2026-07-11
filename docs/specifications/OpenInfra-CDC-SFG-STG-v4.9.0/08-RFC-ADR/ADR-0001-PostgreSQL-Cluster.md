---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# PostgreSQL Cluster comme persistance transactionnelle principale

## Statut

Adopté

## Contexte

OpenInfra doit répondre à des contraintes enterprise : cohérence, évolutivité, auditabilité, exploitabilité, sécurité et absence de régression.

## Décision

PostgreSQL Cluster est retenu pour cohérence transactionnelle, maturité, partitionnement, réplication, PITR et écosystème d’exploitation.

## Conséquences positives

- Décision traçable.
- Alignement développement/exploitation.
- Réduction des ambiguïtés de conception.
- Critères de validation plus objectifs.

## Conséquences et points de vigilance

- La décision doit être réévaluée si les hypothèses de charge ou d’exploitation changent fortement.
- Toute dérogation doit faire l’objet d’un nouvel ADR.
