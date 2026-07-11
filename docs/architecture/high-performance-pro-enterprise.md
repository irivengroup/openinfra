# Architecture haute performance OpenInfra Pro et Entreprise

## Portée

Cette architecture s’applique aux éditions Pro et Entreprise à partir d’OpenInfra 0.30.0. Elle conserve la Clean Architecture, le DDD, les ports/adaptateurs et le monolithe modulaire. L’objectif est de supprimer les plafonds du runtime sans introduire prématurément des microservices.

## Architecture 0.30.0

```text
Clients
  │ HTTPS
  ▼
Load balancer / reverse proxy
  ├── assets versionnés
  ├── BFF Web ASGI stateless, N réplicas
  │      └── pool HTTP keep-alive + streaming
  └── API ASGI stateless, N réplicas × workers
             └── pool PostgreSQL borné par worker
                    └── PostgreSQL primaire
```

Le runtime ASGI prend en charge sockets, keep-alive, concurrence, backlog, processus et cycle de vie. Les services métier synchrones existants sont exécutés dans le threadpool du runtime pendant la migration progressive des adaptateurs I/O. Cette étape améliore le transport et le scale-out mais ne prétend pas rendre tout le domaine nativement asynchrone.

## Dimensionnement

Le budget PostgreSQL doit toujours satisfaire :

```text
réplicas_api × workers_api × pool_max
+ connexions_migrations
+ connexions_exploitation
+ marge_de_failover
≤ capacité PgBouncer/PostgreSQL
```

Valeurs applicatives par worker :

| Édition | workers API auto max | pool min/max | budget local | workers Web auto max | pool HTTP/keep-alive |
|---|---:|---:|---:|---:|---:|
| Pro | 8 | 1/8 | 80 | 4 | 200/50 |
| Entreprise | 16 | 2/12 | 192 | 8 | 500/100 |

Ces valeurs sont des plafonds logiciels, pas une recommandation universelle. Le nombre effectif doit être établi à partir des CPU, de la mémoire, du débit, de la latence PostgreSQL et des SLO.

## Backpressure

Les limites suivantes sont obligatoires :

- concurrence et backlog ASGI ;
- taille maximale du corps HTTP ;
- délai d’acquisition PostgreSQL ;
- taille maximale de chaque pool ;
- limites de connexions et de keep-alive BFF ;
- timeouts connect/read/write/pool distincts ;
- quotas des workers et agents.

Une saturation doit produire une erreur explicite et observable. La création non bornée de threads, connexions ou tâches est interdite.

## Cible P20

La roadmap 2.1.0 complète ce socle par :

- PgBouncer en mode transaction ;
- routage primaire/réplicas avec contrôle du lag ;
- cohérence lecture-après-écriture ;
- pagination par curseur ;
- outbox transactionnelle et workers ;
- stockage objet des payloads massifs ;
- frontend découpé par domaine, cache de requêtes et virtualisation ;
- métriques p50/p95/p99, pools, threadpool, files et lag.

## Compatibilité et rollback

`--runtime legacy` reste disponible pour un rollback contrôlé. Son activation doit être temporaire, auditée et accompagnée d’un incident ou d’un changement approuvé. Les contrats REST, CLI, OpenAPI, RBAC, migrations et modèles métier restent inchangés.

## Validation de performance en deux niveaux

P19 exécute à chaque CI un benchmark déterministe du transport ASGI pour l’API, le bootstrap Web et le proxy BFF. Le rapport contient p50, p95, p99, maximum, débit, seuils et `capacity_certification=false`. Il détecte les régressions de concurrence, pooling HTTP et streaming, mais n’inclut pas PostgreSQL réel ni la topologie de production.

P20 porte la certification de capacité : PgBouncer, primaire/réplicas, données représentatives, paliers, endurance, spike, saturation, chaos, récupération et absence de fuite. Une édition Pro ou Entreprise ne peut être déclarée dimensionnée sur le seul benchmark P19.
