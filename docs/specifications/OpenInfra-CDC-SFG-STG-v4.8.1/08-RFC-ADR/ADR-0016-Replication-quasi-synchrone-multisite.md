# ADR-0016 — Synchronisation quasi temps réel et multisite

## Statut

Accepté.

## Contexte

Les éditions Pro et Entreprise peuvent être déployées en cluster. L'opérateur ne doit pas être expert PostgreSQL HA pour obtenir une installation cohérente.

## Décision

L'installateur backend configure automatiquement la synchronisation quasi temps réel en cluster. Le mode par défaut privilégie un standby local ou proche réseau alimenté en continu, sans commit distant bloquant. Le multisite est supporté pour Pro et Entreprise, avec un modèle centralisé pour Pro et distribué pour Entreprise.

## Conséquences

- Réduction forte de la complexité opérateur.
- RPO local très faible.
- Contrôle de la latence WAN.
- Nécessité de tests de failover et de supervision du lag.
