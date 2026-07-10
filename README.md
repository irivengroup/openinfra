# OpenInfra v0.29.84

## Correctif CI DCIM et compatibilité GitHub Actions Node.js 24

OpenInfra v0.29.84 corrige deux défauts de la chaîne d’intégration continue sans modifier les contrats métier ni les schémas de données. Les smoke tests DCIM consomment désormais le code d’étage canonique réellement retourné par `openinfra dcim define-room`, au lieu de réutiliser le code libre `F01` devenu invalide après normalisation. Les deux scénarios concernés — modèle physique et fondation câblage/énergie — sont couverts.

Les actions GitHub sont également migrées vers des versions reposant sur Node.js 24 : `actions/checkout@v6`, `actions/setup-python@v6` et `actions/setup-node@v6`. Le gate de sécurité refuse explicitement les anciennes versions Node.js 20 afin d’éviter toute régression.

Aucune modification du CDC ni de la roadmap n’est nécessaire : il s’agit d’un correctif d’industrialisation conforme aux exigences existantes.


## Résilience des workers et agents Discovery

OpenInfra v0.29.83 réalise **P14 / EPIC-1406** avec une file de jobs Discovery persistante, idempotente et récupérable après interruption d’un worker ou d’un agent. Un job validé est enregistré avant sa remise à un collector ; il ne peut donc plus être perdu à la suite d’un arrêt brutal entre l’autorisation et l’exécution.

Chaque réservation repose sur un bail expirant et un **jeton de fencing monotone**. Lorsqu’un worker disparaît, un autre peut reprendre le job après expiration du bail ; l’ancien worker ne peut plus terminer ou altérer le traitement avec son jeton périmé. Les échecs suivent une politique de tentatives bornées, puis basculent dans une **DLQ** (Dead-Letter Queue, file de quarantaine) administrable et auditée.

## Capacités livrées

- états persistants `queued`, `leased`, `retry-wait`, `completed` et `dead-letter` ;
- soumission idempotente par tenant et clé métier ;
- réservation atomique concurrente et reprise des baux expirés ;
- jetons de fencing empêchant le double traitement par un worker obsolète ;
- renouvellement de bail, terminaison idempotente et empreinte SHA-256 du résultat ;
- retries bornés, DLQ et rejeu explicite par un administrateur ;
- persistance JSON et PostgreSQL, partitionnée par tenant via la migration `0039_discovery_job_resilience.sql` ;
- CLI, API HTTP, OpenAPI et portail web alignés ;
- audit des soumissions, réservations, reprises, erreurs, mises en DLQ, rejeux et terminaisons ;
- tests domaine, services, concurrence, CLI, HTTP, portail, migration, sécurité et non-perte ;
- runbook `docs/runbooks/DISCOVERY_JOB_RESILIENCE.md`.

La réconciliation multisource v0.29.82 et les corrections DCIM/ITAM antérieures restent compatibles. Le CDC et la roadmap ne sont pas modifiés : EPIC-1406 était déjà défini et aucune nouvelle recommandation n’impacte l’existant.
