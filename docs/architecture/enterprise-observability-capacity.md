# Observabilité et certification de capacité Enterprise

## Objet

OpenInfra 0.32.8 complète P18 / EPIC-1801 sur le socle P20 / EPIC-2005. Le dispositif sépare trois responsabilités :

1. l'observabilité continue des processus API, web et workers ;
2. les benchmarks métier représentatifs API, IPAM, imports, Discovery, base de données et graphes ;
3. la certification de capacité, exécutée uniquement sur une topologie Enterprise représentative avec preuves de charge, d'endurance et de chaos.

Une exécution locale, un benchmark de transport ou une CI standard ne produit jamais une certification Enterprise.

## Architecture

### Instrumentation applicative

`OpenInfraTelemetry` implémente le port `RuntimeTelemetry` et fournit :

- compteurs et histogrammes HTTP par méthode, route normalisée et classe de statut ;
- requêtes en vol, octets reçus et octets émis ;
- exécutions des workers spécialisés et résultats de l'outbox ;
- profondeur et âge des files asynchrones, y compris la DLQ ;
- état des pools PostgreSQL, acquisitions et attente ;
- lag et éligibilité de la réplique ;
- workers ASGI, limites de concurrence, mémoire, CPU, uptime et objets suivis par le GC ;
- traces OpenTelemetry avec propagation W3C `traceparent` entre le BFF et l'API.

Les métriques Prometheus n'utilisent ni tenant, ni acteur, ni identifiant de ressource comme label. Cette règle évite les fuites de données et les séries à cardinalité non bornée.

### Exposition et collecte

Les processus ASGI exposent `GET /metrics`. Le endpoint est volontairement sans authentification métier pour être collecté par Prometheus ; il doit rester sur un réseau d'administration ou derrière une politique réseau dédiée.

En mode multiprocessus, `PROMETHEUS_MULTIPROC_DIR` est un répertoire temporaire distinct par conteneur. L'image Docker utilise l'identité non-root déterministe `10001:10001`, identique au propriétaire du tmpfs Compose. Le runtime crée, nettoie et vérifie l'écriture du répertoire avant le démarrage des workers ; une divergence d'identité ou de permissions arrête immédiatement le parent Uvicorn avec un diagnostic explicite.

La pile optionnelle `observability` comprend :

- OpenTelemetry Collector pour recevoir les traces OTLP/HTTP ;
- Tempo pour stocker les traces ;
- Prometheus pour collecter les métriques et évaluer les règles SLO ;
- Grafana avec datasource et dashboard provisionnés.

### Dégradation contrôlée

OpenTelemetry est désactivé par défaut. Lorsque l'export OTLP est désactivé ou indisponible, les métriques Prometheus restent utilisables. L'instrumentation n'ajoute aucun stockage métier et ne bloque pas les requêtes sur la disponibilité du backend de traces.

## SLO et alertes

Les règles fournies couvrent notamment :

- p95 et p99 HTTP ;
- taux d'erreurs 5xx ;
- file asynchrone bloquée et DLQ non vide ;
- lag ou inéligibilité d'une réplique ;
- attente dans le pool PostgreSQL ;
- saturation de concurrence ;
- disparition des métriques.

Les seuils de certification versionnés sont définis dans `docs/operations/enterprise-capacity-profile.json`.

## Certification de capacité

Le moteur `EnterpriseCapacityCertification` exige simultanément :

- édition Enterprise ;
- au moins 2 API, 2 web, 4 workers spécialisés, 1 primaire, 1 réplique et 2 PgBouncer ;
- au moins 100 000 objets et 100 000 relations ;
- six benchmarks en lecture seule couvrant API, IPAM, imports, Discovery, routage base de données et graphes ;
- cinq phases : baseline, paliers, endurance, spike et saturation ;
- quatre scénarios de chaos : perte API, perte web, perte réplique et redémarrage PgBouncer ;
- métriques complètes, couverture de traces, intégrité des données et absence de perte de travail acquitté ;
- empreintes SHA-256 de chaque preuve source.

Le rapport est écrit atomiquement et porte une empreinte canonique des preuves. `--enforce` retourne un code non nul dès qu'un critère manque ou dépasse un seuil.

Le profil de certification v2 refuse une certification si une famille EPIC-1801 manque. Chaque benchmark utilise uniquement `GET`, un pool HTTP borné, un débit cible, une concurrence maximale et une liste explicite de statuts HTTP attendus. Les chemins exacts sont fournis par l'environnement de qualification afin de viser des données réellement représentatives sans hardcoder d'identifiants de tenant ou de ressources dans le dépôt.

## Sécurité et confidentialité

- aucun secret n'est écrit dans les métriques, dashboards ou rapports ;
- le bearer token de charge est fourni uniquement par variable d'environnement ;
- les URLs de qualification doivent utiliser HTTPS ;
- les preuves de topologie et de chaos sont conservées comme artefacts protégés ;
- la pile Grafana est liée à `127.0.0.1` par défaut et exige un mot de passe explicite ;
- le workflow de certification utilise un runner auto-hébergé dédié et un environnement GitHub protégé.

## Compatibilité et rollback

Aucune migration PostgreSQL n'est ajoutée. La désactivation de l'observabilité distribuée consiste à définir `OPENINFRA_OTEL_ENABLED=false` et à arrêter le profil Compose `observability`. Les endpoints métier, les files, le frontend et les données restent inchangés.
