# ADR-0017 — Fichier `install.ini` par dossier d'installation

## Statut

Accepté.

## Contexte

Les éditions OpenInfra Lite, Pro et Entreprise comportent plusieurs scopes d'installation.
Les paramètres varient selon le serveur, le site, la topologie réseau, le mode cluster, le stockage et les intégrations.
Un opérateur ne doit pas modifier les scripts ni posséder une expertise approfondie des composants HA pour installer OpenInfra.

## Décision

Chaque dossier d'installation contient un fichier `./config/install.ini`.
Ce fichier constitue le contrat de configuration opérateur.
Les scripts d'installation sont génériques et déterministes.

## Conséquences positives

- Installation plus simple.
- Automatisation plus fiable.
- Meilleure traçabilité.
- Réduction des erreurs humaines.
- Validation avant changement système.
- Même logique pour Lite, Pro et Entreprise.

## Contraintes

- Le schéma `install.ini` doit être versionné.
- Les validations doivent être strictes.
- Les secrets en clair sont interdits.
- Les templates doivent être maintenus avec les installateurs.
- Les tests doivent couvrir chaque édition et scope.
