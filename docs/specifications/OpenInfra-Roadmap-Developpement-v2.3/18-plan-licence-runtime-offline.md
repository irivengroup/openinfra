# Plan P23 — Licence runtime offline

## Objectif

Livrer une validation offline déterministe pour les éditions Pro et Entreprise, sans appel réseau obligatoire et sans clé privée d’autorité déployée chez le client. L’édition Lite reste exploitable sans licence commerciale.

## Séquence d’implémentation

1. **EPIC-2301 — Chaîne de confiance** : identité locale Ed25519, demande signée, autorité hors ligne chiffrée, trust bundle public et validation stricte.
2. **EPIC-2302 — Persistance et quota** : repositories JSON/PostgreSQL/Oracle, migration 0059, écriture atomique, verrou transactionnel et protection contre le recul d’horloge.
3. **EPIC-2303 — Parcours opérateur** : bootstrap, activation, renouvellement, CLI/API, HTTP 402, installateurs Pro/Entreprise et notifications accessibles FR/EN.
4. **EPIC-2304 — Qualification** : politique REL-13, GATE-12 7/7, tests, couverture globale minimale de 98 %, packaging, smoke test et runbook.

## Invariants de sécurité

- La clé privée d’autorité est chiffrée, utilisée hors ligne et absente des sources, installations, images, wheels et sdists.
- L’entitlement est lié au UUID de licence, au UUID d’installation, à l’entreprise, à l’édition, au quota et aux dates UTC.
- Les états absents, corrompus, expirés hors grâce, non encore valides ou soumis à recul d’horloge sont bloquants lorsque l’enforcement est actif.
- Le quota d’hôtes est évalué dans la même unité de travail transactionnelle que l’écriture de l’équipement.
- Toute activation ou tout renouvellement produit une preuve auditable sans exposer l’entitlement complet au frontend.

## Définition de terminé

REL-13 est terminée uniquement lorsque GATE-12 retourne 7/7, que la couverture globale atteint au moins 98 %, que les trois backends et les installateurs passent leurs tests, que l’OpenAPI et les notifications sont validés, et que les artefacts installés passent leur smoke test sans matériel privé d’autorité.
