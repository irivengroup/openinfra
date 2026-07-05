# ADR-0011 — Installation autonome cluster

## Statut

Accepté en v4.4.0.

## Contexte

OpenInfra cible des environnements d'enterprise où le déploiement peut concerner backend, frontend, agents et PostgreSQL Cluster. L'opérateur ne doit pas être expert en haute disponibilité, PostgreSQL, VIP, systemd, certificats ou orchestration de services.

## Décision

OpenInfra fournit des installateurs autonomes par édition et par scope. En mode cluster, les installateurs utilisent uniquement les FQDN, IP, masque, VIP, passerelle et DNS fournis par l'opérateur pour configurer l'ensemble des composants nécessaires.

## Conséquences positives

- Déploiement reproductible.
- Réduction des erreurs humaines.
- Déploiement exploitable par équipes non expertes.
- Preuves d'installation standardisées.
- Meilleure supportabilité.

## Conséquences à maîtriser

- Les installateurs doivent être fortement testés.
- Les distributions supportées doivent être explicitement cadrées.
- Les actions système nécessitent des privilèges élevés.
- Les échecs doivent produire rollback et diagnostics détaillés.
