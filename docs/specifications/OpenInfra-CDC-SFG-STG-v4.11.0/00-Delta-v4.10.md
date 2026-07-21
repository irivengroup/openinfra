# Delta CDC v4.10.0 — Licence runtime offline

Le présent delta est additif par rapport au CDC 4.9.0. Aucune exigence historique, API métier, permission RBAC ou capacité d’édition n’est supprimée.

## Décisions contractuelles

- Lite fonctionne sans licence commerciale.
- Pro et Entreprise exigent une licence valide lorsque l’enforcement runtime est activé.
- La licence est validée sans accès Internet au moyen de signatures Ed25519.
- L’entitlement est lié au UUID de licence, au UUID d’installation, à l’entreprise, à l’édition, au quota d’hôtes et aux dates de validité.
- Après expiration, une grâce non renouvelable de 30 jours est appliquée avec notifications ; après cette grâce, les commandes métier et l’API sont bloquées.
- La clé privée de l’autorité de licence n’est jamais livrée avec OpenInfra. L’outil d’émission offline exige une clé privée chiffrée par mot de passe.
- Les backends JSON, PostgreSQL et Oracle présentent le même contrat de persistance. La migration additive courante est `0059_runtime_offline_licensing.sql`.
- Le quota d’hôtes est contrôlé dans la même unité de travail que l’écriture de l’équipement.
- GATE-12 est bloquant pour REL-13 et vérifie sept preuves fermées.

## Compatibilité

PostgreSQL reste le backend par défaut. Oracle reste réservé à l’édition Entreprise. La charte graphique approuvée est inchangée ; les portails réutilisent les alertes accessibles Bootstrap existantes.
