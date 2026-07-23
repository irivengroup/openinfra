# Delta CDC 4.9.0 — Architecture haute performance Pro et Entreprise

## Décision

Le CDC 4.9.0 rend contractuelle une architecture d’exécution haute performance pour les éditions Pro et Entreprise. La Clean Architecture, le DDD et le monolithe modulaire sont conservés ; le transport, les connexions et les modèles de lecture évoluent sans réécriture du domaine.

## Changements obligatoires

- API et BFF Web servis par un runtime ASGI stateless, multiprocessus et réplicable.
- Runtime historique synchrone autorisé uniquement pour rollback contrôlé, diagnostic et compatibilité transitoire.
- Pool PostgreSQL borné par worker, avec budget global de connexions et acquisition temporisée.
- PgBouncer en mode transaction devant PostgreSQL dans les topologies Pro HA et Entreprise.
- Client HTTP BFF persistant, asynchrone, avec keep-alive, limites, timeouts séparés et streaming.
- Routage lecture/écriture vers primaire et réplicas avec contrôle du lag et cohérence lecture-après-écriture.
- Pagination par curseur pour les collections volumineuses ; OFFSET limité aux référentiels bornés.
- Exports et traitements lourds exécutés par workers, avec outbox transactionnelle et stockage objet.
- Frontend découpé par domaine, chargement dynamique, cache de requêtes, annulation et virtualisation.
- Budgets p95/p99, saturation des pools, backpressure et tests de charge bloquants dans la CI.

## Livraison initiale OpenInfra 0.30.0

La première tranche applique immédiatement : runtime ASGI API/Web, workers par édition, pool PostgreSQL borné, budget de connexions, client HTTP persistant, streaming BFF, configuration externalisée, tests de sécurité/concurrence et gate CI. Les évolutions PgBouncer, read replicas, pagination curseur généralisée, frontend modulaire et outbox sont ordonnancées dans la roadmap 2.1.0.

## Compatibilité

Les contrats métier, REST, OpenAPI, CLI, migrations et règles RBAC restent compatibles. Aucune fonctionnalité existante n’est supprimée. Le basculement `legacy` constitue un mécanisme de rollback temporaire documenté et testé.
