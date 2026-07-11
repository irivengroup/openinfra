# OpenInfra v0.30.0 — Rapport de validation

Date : `2026-07-11`  
Release : `0.30.0`  
CDC : `4.9.0`  
Roadmap : `2.1.0`  
Nature : `évolution architecturale majeure — socle haute performance Pro et Entreprise`

## Périmètre livré

### Runtime API et Web

- ASGI stateless activé par défaut pour l’API et le BFF Web en Pro et Entreprise.
- Politiques multiprocessus bornées par édition.
- Limites configurables de concurrence, backlog et keep-alive.
- Lifespan applicatif avec fermeture déterministe des ressources.
- Runtime historique conservé via `--runtime legacy` pour rollback contrôlé.
- Restauration atomique des variables d’environnement après arrêt, interruption ou échec de démarrage.

### PostgreSQL

- Pool `psycopg_pool` par worker.
- Bornes min/max, timeout d’acquisition, idle timeout et durée de vie maximale.
- Budget global de connexions contrôlant le produit `workers × pool_max`.
- Restitution des connexions après transaction et fermeture explicite du pool.
- Paramètres externalisés dans `.env.example`, Compose et installateurs.

### BFF Web

- Client `httpx.AsyncClient` persistant.
- Pools de connexions et keep-alive bornés.
- Timeouts distincts de connexion, lecture, écriture et acquisition du pool.
- Streaming des réponses backend sans buffering intégral.
- Conservation des protections CSP, anti-traversal, tailles de corps, cache, ETag et compression.

### Gouvernance et qualité

- CDC réaligné en version 4.9.0 avec 12 exigences haute performance supplémentaires.
- Roadmap réalignée en version 2.1.0 avec phases P19/P20, releases, epics, risques, tests et gates Go/No-Go.
- Gate CI p95/p99 du transport ASGI avec rapport JSON.
- Distinction obligatoire entre régression de transport P19 et certification de capacité P20.
- Documentation d’architecture, runbook d’exploitation, rollback et traçabilité actualisés.

## Capacités explicitement non revendiquées en 0.30.0

Les éléments suivants restent planifiés en P20 et ne sont pas déclarés comme livrés :

- PgBouncer en mode transaction ;
- routage primaire/réplicas avec contrôle du lag ;
- pagination par curseur généralisée ;
- outbox transactionnelle et workers spécialisés ;
- frontend React découpé par domaine et listes virtualisées ;
- stockage objet des payloads append-only massifs ;
- certification de capacité sur PostgreSQL réel avec endurance, spike, saturation et chaos.

## Résultats Python

| Contrôle | Résultat |
|---|---:|
| Tests réussis | **967** |
| Échecs | **0** |
| Durée | **155,22 s** |
| Instructions mesurées | **35 774** |
| Instructions non couvertes | **712** |
| Couverture globale | **98,01 %** |
| Seuil contractuel | **98 % — PASS** |

La couverture a été exécutée sur la suite complète avec la configuration du projet. Aucun seuil, fichier source ou branche nouvelle n’a été exclu pour obtenir le résultat.

## Benchmark p95/p99 du transport ASGI

Profil : 500 requêtes par scénario, concurrence 50, 25 warmups.

| Scénario | Débit | p50 | p95 | p99 | Seuil p95/p99 | Résultat |
|---|---:|---:|---:|---:|---:|---|
| API `/health` | 2 263,498 req/s | 11,912 ms | 20,687 ms | 23,397 ms | 150 / 300 ms | PASS |
| Web `/bootstrap.json` | 4 510,601 req/s | 0,200 ms | 0,263 ms | 0,534 ms | 150 / 300 ms | PASS |
| Proxy BFF | 3 172,892 req/s | 0,293 ms | 0,367 ms | 0,674 ms | 200 / 400 ms | PASS |

Le rapport porte :

```text
scope=asgi-transport-regression
capacity_certification=false
```

Ce benchmark est un gate déterministe de non-régression du transport. Il ne remplace pas la certification de capacité P20 sur une topologie PostgreSQL/PgBouncer représentative.

## Benchmark volumétrique RSOT

Profil : 5 000 nœuds, 100 hubs SPOF, 3 échantillons.

| Scénario | p95 | Seuil | Résultat |
|---|---:|---:|---|
| Parcours un niveau | 200,481 ms | 1 500 ms | PASS |
| Parcours filtré | 102,810 ms | 1 500 ms | PASS |
| Analyse SPOF | 199,388 ms | 5 000 ms | PASS |
| Pagination SPOF complète | 518,578 ms | 15 000 ms | PASS |

## Frontend

| Contrôle | Résultat |
|---|---|
| Tests Node.js | **47/47 PASS** |
| Contrat statique | PASS |
| ESLint JSX | PASS |
| WCAG 2.2 AA | PASS |
| Build Vite | PASS |
| Bundle CSS | 268,49 Ko brut / 38,10 Ko gzip |
| Bundle JavaScript | 320,39 Ko brut / 92,87 Ko gzip |

Le bundle React reste monolithique. Sa modularisation, son cache de requêtes et sa virtualisation sont inscrits en P20/EPIC-2004.

## Contrôles statiques, sécurité et contrats

| Contrôle | Résultat |
|---|---|
| Ruff format | **283 fichiers conformes** |
| Ruff lint strict | PASS |
| mypy strict | **91 modules — PASS** |
| `compileall` | PASS |
| Bandit | PASS |
| Security gate | PASS |
| Quality gate | PASS |
| OpenAPI principal | **318 paths — PASS** |
| OpenAPI CDC | **318 paths — PASS** |
| Installateurs | **6 profils — PASS** |
| Dry-run installateurs | PASS |
| Alignement Enterprise | PASS |
| CDC 4.9.0 | **840 exigences / 529 entités — PASS** |
| Roadmap 2.1.0 | **21 phases / 125 epics / 10 gates / 106 tests — PASS** |

Les avertissements Bandit correspondent à des annotations `nosec` existantes et reconnues sur des fragments SQL internes bornés ; aucun finding bloquant n’a été produit.

## Packaging

- Wheel `openinfra-0.30.0-py3-none-any.whl` construit et vérifié.
- Sdist `openinfra-0.30.0.tar.gz` construit et vérifié.
- Installation du wheel avec `--no-deps` dans un répertoire vierge : PASS.
- Smoke du package installé : version 0.30.0, 52 migrations, dernière migration `0052_multisite_disaster_recovery.sql`.
- Présence vérifiée dans le wheel des adaptateurs ASGI, du scope d’environnement et de l’infrastructure PostgreSQL.
- Métadonnées runtime vérifiées pour `uvicorn`, `httpx` et `psycopg-pool`.
- Présence vérifiée dans le sdist du CDC 4.9.0, de la roadmap 2.1.0, du benchmark et de ses tests.

## Contrôles non exécutables dans l’environnement local

- `pip-audit` a été lancé mais n’a pas pu résoudre `pypi.org` ; aucune conclusion sur les vulnérabilités distantes ne peut être tirée localement. Le gate reste bloquant en CI avec accès réseau.
- Docker et Podman ne sont pas installés ; les smokes conteneurisés restent des gates CI.
- `psql` et une instance PostgreSQL réelle ne sont pas disponibles ; la saturation réelle, PgBouncer, les réplicas, l’endurance et le chaos restent des validations P20.

## Conclusion

Le socle P19 est validé pour livraison : runtime ASGI, pooling borné, BFF asynchrone persistant, compatibilité, documentation et gates CI sont intégrés et régressés. La release ne doit pas être présentée comme une certification de capacité Pro/Entreprise tant que le gate P20 sur infrastructure représentative n’a pas été exécuté avec succès.
