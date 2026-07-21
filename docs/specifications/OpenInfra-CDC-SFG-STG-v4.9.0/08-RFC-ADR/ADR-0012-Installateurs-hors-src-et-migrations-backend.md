# ADR-0012 — Installateurs hors `src` et migrations portées par le backend installer

## Statut

Accepté en v4.4.0.

## Contexte

Le dépôt OpenInfra doit séparer clairement code applicatif, migrations et logique d'installation. Les migrations de base de données sont une responsabilité backend, car elles concernent le schéma transactionnel central.

## Décision

Les installateurs sont placés dans un dossier racine `installers/`, hors de `src/`. L'installateur `server` applique toutes les migrations backend avant le démarrage applicatif final. Les installateurs `web` et `agent` ne peuvent pas appliquer de migrations base de données.

## Conséquences positives

- Séparation claire des responsabilités.
- Réduction du couplage entre packaging et code métier.
- Migrations centralisées, traçables et testables.
- Moins de risque de migration accidentelle depuis un frontend ou un agent.

## Conséquences à maîtriser

- Le pipeline CI/CD doit vérifier la présence des migrations et leur exécution.
- Les upgrades multi-éditions doivent être testés.
- Les migrations doivent rester compatibles avec les quotas et capacités d'édition.
