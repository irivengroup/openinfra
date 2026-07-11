# OpenInfra v0.30.1 — Rapport de validation

Date : `2026-07-11`  
Release : `0.30.1`  
CDC : `4.9.0`  
Roadmap : `2.1.0`  
Phase : `P20 / EPIC-2001`  
Nature : `plan de données PostgreSQL haute performance Pro et Entreprise`

## Périmètre livré

### PgBouncer et topologie PostgreSQL

- Deux pools PgBouncer indépendants devant le primaire et le standby.
- `pool_mode=transaction`, authentification SCRAM-SHA-256 et limites de connexions bornées.
- Désactivation des requêtes préparées côté client pour la compatibilité avec le pooling transactionnel.
- Standby PostgreSQL initialisé avec `pg_basebackup --write-recovery-conf`.
- Rôle de réplication créé ou remis en conformité de manière idempotente, y compris lorsque le volume primaire existe déjà.
- Scripts shell validés syntaxiquement et contrat Compose vérifié sur les services, dépendances et variables obligatoires.

### Routage lecture/écriture

- Toutes les mutations restent dirigées vers le primaire.
- Les requêtes `GET` et `HEAD` éligibles utilisent la réplique uniquement lorsqu'elle est en recovery et sous le seuil de lag configuré.
- Fallback automatique vers le primaire lorsque la réplique est absente, indisponible ou trop en retard.
- Mode strict disponible pour refuser une lecture plutôt que basculer silencieusement.
- Portée de lecture unique par requête : une connexion et un snapshot cohérent sont réutilisés pendant tout le traitement.
- Compteurs d'acquisition primaire, réplique et fallback exposés par worker.
- Endpoint d'exploitation : `GET /api/v1/database/routing?tenant_id=default`.

### Cohérence lecture-après-écriture

- Jeton HMAC-SHA256 court, signé et expirant.
- Encodage déterministe en deux segments Base64URL `payload.signature`.
- Rejet des jetons altérés, expirés ou mal formés.
- Transmission par en-tête `X-OpenInfra-Consistency-Token`.
- Relais BFF dans un cookie `HttpOnly`, `SameSite=Strict`, `Secure` sous HTTPS et durée de vie synchronisée avec le jeton.
- Une requête de lecture portant un jeton valide reste sur le primaire jusqu'à expiration.

### Compatibilité et sécurité

- Les repositories PostgreSQL continuent d'exiger une unité de travail active.
- Aucun accès direct aux agents ou au frontend vers PostgreSQL.
- Les secrets peuvent être fournis directement ou par référence externe ; aucune valeur n'est embarquée dans le code.
- Le runtime historique reste disponible uniquement comme mécanisme de rollback contrôlé.
- Le format OpenAPI, le BFF, la CLI, les contrats existants et les 52 migrations restent compatibles.

## Résultats Python

| Contrôle | Résultat |
|---|---:|
| Tests collectés et réussis | **983** |
| Échecs | **0** |
| Durée sans collecte de couverture | **129,04 s** |
| Instructions mesurées | **35 986** |
| Instructions non couvertes | **718** |
| Couverture mesurée | **98,0048 %** |
| Seuil contractuel | **98 % — PASS** |

La couverture est calculée selon la configuration contractuelle du projet. L'adaptateur PostgreSQL monolithique reste exclu du calcul global par la configuration historique et fait l'objet de tests d'intégration dédiés ; sa validation sur PostgreSQL réel demeure un gate P20 non exécutable dans cet environnement.

## Tests spécifiques du plan de données

Les tests couvrent notamment :

- lecture sur standby sain ;
- fallback primaire sur panne et lag excessif ;
- mode strict ;
- absence de DSN de lecture ;
- acquisition et restitution des connexions ;
- portée transactionnelle de lecture ;
- invariant d'unité de travail des repositories ;
- jetons valides, expirés, altérés et mal formés ;
- propagation en-tête/cookie par le BFF ;
- cookies sécurisés sous HTTPS ;
- restauration des variables d'environnement ;
- contrat Compose et scripts de réplication idempotents ;
- endpoint de statut et permissions administrateur sécurité.

## Benchmark p95/p99 du transport ASGI

Profil : 500 requêtes par scénario, concurrence 50, 25 warmups.

| Scénario | Débit | p50 | p95 | p99 | Seuil p95/p99 | Résultat |
|---|---:|---:|---:|---:|---:|---|
| API `/health` | 2 230,064 req/s | 12,082 ms | 20,138 ms | 22,712 ms | 150 / 300 ms | PASS |
| Web `/bootstrap.json` | 4 231,237 req/s | 0,212 ms | 0,292 ms | 0,593 ms | 150 / 300 ms | PASS |
| Proxy BFF | 2 515,984 req/s | 0,358 ms | 0,497 ms | 1,043 ms | 200 / 400 ms | PASS |

Le rapport conserve les marqueurs :

```text
scope=asgi-transport-regression
capacity_certification=false
```

Ce benchmark détecte les régressions du transport. Il ne certifie pas encore la capacité PostgreSQL/PgBouncer sur une topologie réelle.

## Frontend

| Contrôle | Résultat |
|---|---|
| Tests Node.js | **47/47 PASS** |
| Contrat statique | PASS |
| ESLint JSX | PASS |
| WCAG 2.2 AA | PASS |
| Build Vite | PASS |
| Audit npm niveau high | **0 vulnérabilité** |
| Bundle CSS | 268,49 Ko brut / 38,10 Ko gzip |
| Bundle JavaScript | 320,39 Ko brut / 92,87 Ko gzip |

La modularisation du bundle React, le cache de requêtes et la virtualisation restent planifiés dans les epics P20 suivants.

## Contrôles statiques, sécurité et contrats

| Contrôle | Résultat |
|---|---|
| Ruff format | **280 fichiers conformes** |
| Ruff lint strict | PASS |
| mypy strict | **92 modules — PASS** |
| `compileall` | PASS |
| Bandit | PASS |
| Security gate | PASS |
| Quality gate | PASS |
| OpenAPI principal | **319 paths — PASS** |
| OpenAPI CDC | **319 paths — PASS** |
| Scripts PostgreSQL/PgBouncer `bash -n` | PASS |
| Contrat Compose YAML | **11 services — PASS** |
| Installateurs | **6 profils — PASS** |
| Alignement Enterprise | PASS |
| CDC 4.9.0 | **840 exigences / 529 entités — PASS** |
| Roadmap 2.1.0 | **21 phases / 125 epics / 10 gates / 106 tests — PASS** |

Les avertissements Bandit correspondent uniquement à des annotations `nosec` déjà contrôlées sur des fragments SQL internes bornés ; aucun finding bloquant n'a été produit.

## Packaging

- Wheel `openinfra-0.30.1-py3-none-any.whl` construit et vérifié.
- Sdist `openinfra-0.30.1.tar.gz` construit et vérifié.
- Installation du wheel avec `--no-deps` dans un répertoire vierge : PASS.
- Smoke du package installé : version 0.30.1, 52 migrations, dernière migration `0052_multisite_disaster_recovery.sql`.
- Présence vérifiée des adaptateurs ASGI, du routeur de lecture, des assets Web et de l'OpenAPI embarqué.
- Route `/api/v1/database/routing` vérifiée dans le package installé.
- Présence vérifiée dans le sdist du CDC 4.9.0, de la roadmap 2.1.0, du runbook PostgreSQL, des scripts PgBouncer/réplication et du présent rapport.
- Vérificateur d'artefact renforcé pour rendre ces fichiers obligatoires dans les prochaines constructions CI.

## Contrôles non exécutables dans l'environnement local

- `pip-audit` a été lancé en mode strict mais la résolution DNS de `pypi.org` a échoué. Aucune conclusion distante ne peut être tirée localement ; le gate reste bloquant en CI avec accès réseau.
- Docker et Podman ne sont pas installés ; aucun démarrage réel de la topologie Compose n'a été revendiqué.
- `psql` et une instance PostgreSQL réelle ne sont pas disponibles ; la réplication physique, le lag, la saturation PgBouncer, l'endurance, les spikes et les scénarios de chaos restent à certifier dans le gate P20 sur infrastructure représentative.

## Conclusion

La release 0.30.1 est validée au niveau code, contrats, sécurité statique, tests fonctionnels, frontend et benchmark de transport. Elle livre le premier plan de données P20 sans revendiquer une certification de capacité PostgreSQL réelle. La prochaine priorité reste la généralisation de la pagination par curseur et l'outbox transactionnelle, après validation conteneurisée du présent socle.
