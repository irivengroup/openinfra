# Architecture cible par édition

## Vue synthétique

| Domaine | Lite | Pro | Entreprise |
|---|---|---|---|
| Déploiement | Monolithique | Backend + Web + DB séparables | Backend cluster + Web cluster + Agents proxy collectors + Workers + DB HA |
| Service principal | `openinfra.service` | `openinfra.service` | `openinfra.service` |
| Frontend | intégré | `openinfra-web.service` | `openinfra-web.service` en replicas |
| Agent/proxy collector distribué | non | non | `openinfra-agent.service` Enterprise uniquement |
| Workers asynchrones | non | oui | oui, scalables |
| PostgreSQL | local/simple | medium, cluster optionnel | large, cluster optionnel, partitionnement obligatoire |
| ITSM externe | non | oui | oui |
| Quotas | stricts | stricts | illimités |

## Architecture Lite

```mermaid
graph TD
  U[Utilisateur] --> OI[openinfra.service]
  OI --> PG[(PostgreSQL local profil low)]
```

## Architecture Pro

```mermaid
graph TD
  U[Utilisateurs] --> WEB[openinfra-web.service]
  WEB --> API[openinfra.service]
  CLI[CLI] --> API
  API --> PG[(PostgreSQL profil medium)]
  API --> W[openinfra-worker.service]
  API --> C[openinfra-connector.service]
  C --> ITSM[ITSM externe]
```

## Architecture Entreprise

```mermaid
graph TD
  U[Utilisateurs] --> LBWEB[Load Balancer Web]
  LBWEB --> WEB1[openinfra-web.service replica 1]
  LBWEB --> WEB2[openinfra-web.service replica N]
  WEB1 --> LBAPI[Load Balancer API]
  WEB2 --> LBAPI
  CLI[CLI/API Clients] --> LBAPI
  LBAPI --> API1[openinfra.service replica 1]
  LBAPI --> API2[openinfra.service replica N]
  API1 --> MQ[Message Queue]
  API2 --> MQ
  MQ --> W1[openinfra-worker.service pool]
  MQ --> A1[openinfra-agent.service région A]
  MQ --> A2[openinfra-agent.service région B]
  API1 --> PG[(PostgreSQL Cluster profil large)]
  API2 --> PG
  API1 --> ITSM[ITSM externe]
  API2 --> ITSM
```

## Règles communes

- Le frontend ne doit jamais accéder directement à PostgreSQL.
- Les agents proxy collectors Enterprise ne doivent jamais écrire directement dans PostgreSQL et ne sont jamais disponibles en Lite/Pro.
- Les connecteurs ITSM ne doivent jamais contourner l'API backend.
- Les décisions d'autorisation sont prises côté backend.
- Les feature gates sont appliqués côté backend et testés par édition.
- Les migrations doivent rester compatibles avec toutes les éditions supportées.

## Profils d’exécution v4.9.0

- **Lite** : un worker, ASGI recommandé ; runtime legacy autorisé pour compatibilité locale.
- **Pro** : API et Web séparés, ASGI obligatoire, plusieurs réplicas possibles, pool PostgreSQL borné, PgBouncer dès activation HA, réplicas de lecture pour reporting.
- **Entreprise** : API/Web clusterisés, ASGI obligatoire, budgets globaux de connexion, PgBouncer, routage primaire/réplicas, workers distribués, agents régionaux et observabilité de saturation.
