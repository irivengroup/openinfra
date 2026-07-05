# ADR-0016 — Réplication quasi synchrone et multisite

## Statut

Accepté.

## Contexte

Les éditions Pro et Entreprise peuvent être déployées en cluster. L'opérateur ne doit pas être expert PostgreSQL HA pour obtenir une installation cohérente.

## Décision

L'installateur backend configure automatiquement la réplication quasi synchrone en cluster. Le mode par défaut privilégie un standby synchrone local ou proche réseau. Le multisite est supporté pour Pro et Entreprise, avec un modèle centralisé pour Pro et distribué pour Entreprise.

## Conséquences

- Réduction forte de la complexité opérateur.
- RPO local très faible.
- Contrôle de la latence WAN.
- Nécessité de tests de failover et de supervision du lag.
