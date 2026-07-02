---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Cycle de vie hot/warm/cold des données massives

## Statut

Adopté

## Contexte

OpenInfra doit répondre à des contraintes entreprise : cohérence, évolutivité, auditabilité, exploitabilité, sécurité et absence de régression.

## Décision

Les données transactionnelles ne doivent pas devenir un entrepôt analytique illimité.

## Conséquences positives

- Décision traçable.
- Alignement développement/exploitation.
- Réduction des ambiguïtés de conception.
- Critères de validation plus objectifs.

## Conséquences et points de vigilance

- La décision doit être réévaluée si les hypothèses de charge ou d’exploitation changent fortement.
- Toute dérogation doit faire l’objet d’un nouvel ADR.
