# V31 — Licence runtime offline

Ce volume prescrit le cycle complet demande, émission, activation, renouvellement, notification, expiration et qualification de la licence OpenInfra.

## Éditions

| Édition | Licence commerciale | Enforcement |
|---|---:|---|
| Lite | non | état `not_required` |
| Pro | oui | fail-closed lorsque configuré |
| Entreprise | oui | fail-closed lorsque configuré |

## Invariants de sécurité

La clé privée d’autorité n’est jamais incluse dans les sources, images, wheels, sdists, installateurs ou sauvegardes clientes. Les clés d’installation sont protégées par permissions minimales. Les opérations critiques sont auditées sans journaliser l’entitlement complet ni une clé privée.

## Disponibilité

Une licence expirée reste utilisable pendant exactement 30 jours. Les portails affichent une notification accessible dès l’approche de l’échéance et pendant la grâce. Après la grâce, les fonctions métier sont refusées, mais le statut, l’activation et le renouvellement restent disponibles.
