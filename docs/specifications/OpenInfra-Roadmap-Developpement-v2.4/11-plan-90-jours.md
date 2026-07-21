# OpenInfra — Plan opérationnel 90 jours CDC 4.9.0

## Jours 1 à 30 — Fondation 0.30.0

- Finaliser ASGI API/Web, pools bornés et streaming.
- Déployer les métriques workers/pools et documenter les budgets.
- Exécuter la régression complète, sécurité, packaging et smoke multiworker.
- Préparer un environnement PostgreSQL/PgBouncer représentatif Pro.

## Jours 31 à 60 — Données et backpressure

- Déployer PgBouncer transaction pooling.
- Séparer DSN primaire et lecture ; mesurer le lag.
- Migrer deux collections volumineuses pilotes vers pagination curseur.
- Mettre en place paliers, spike et endurance avec rapports p95/p99.

## Jours 61 à 90 — Frontend et asynchrone

- Découper Dashboard, DCIM et RSOT en chunks dynamiques.
- Introduire cache de requêtes, annulation et virtualisation pilote.
- Livrer l’outbox transactionnelle et un worker de rapport pilote.
- Exécuter le gate GATE-09 sur une topologie Pro puis Entreprise.
