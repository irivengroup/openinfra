# OpenInfra v0.31.4 — rapport de validation

Date : 2026-07-12

## Objet

Cette livraison corrige le démarrage des runtimes ASGI multiprocessus lorsque `prometheus_client` utilise `PROMETHEUS_MULTIPROC_DIR` dans Docker Compose.

La cause de la régression 0.31.3 était une divergence d'identité Unix :

- l'image créait l'utilisateur `openinfra` avec un UID/GID système dynamique ;
- Compose montait `/tmp/openinfra-prometheus` avec l'UID/GID fixe `10001:10001` ;
- les workers Uvicorn non-root ne pouvaient donc pas créer les fichiers mmap Prometheus.

## Correctifs

- UID/GID Docker déterministes `10001:10001` pour l'utilisateur `openinfra` ;
- propriétaire du tmpfs Compose conservé à `10001:10001` pour les services API et web ;
- préflight d'écriture réel avant le fork Uvicorn ;
- nettoyage contrôlé des fichiers `*.db` au démarrage ;
- arrêt anticipé avec un diagnostic indiquant le chemin et l'identité effective lorsque le montage n'est pas inscriptible ;
- gate d'observabilité et test Docker/Compose empêchant une nouvelle divergence d'identité.

## Compatibilité

- aucune migration PostgreSQL ;
- aucun changement de route ou de contrat API/CLI métier ;
- aucune dépendance runtime ajoutée ;
- aucun changement du frontend fonctionnel ;
- aucune modification des feuilles CSS.

Les deux feuilles de style conservent le SHA-256 suivant, identique à 0.31.3 :

```text
1df955fd51fdd253590c391a3ee9430c9ca9db88b76819f4482007a5cf567dad
```

## Validations exécutées

### Python et contrats

- collection : **1 112 tests** sur **192 fichiers** ;
- suites unitaires, architecture et performance : **486 tests réussis** ;
- tests ciblés observabilité, interfaces et environnement Docker : **15 tests réussis** ;
- Ruff format : **PASS**, 321 fichiers conformes ;
- Ruff lint : **PASS** ;
- mypy strict : **PASS**, 102 modules ;
- `compileall` : **PASS** ;
- Bandit : **PASS**, aucun finding bloquant ;
- validation observabilité : **PASS** ;
- validation OpenAPI des deux contrats : **PASS** ;
- validation frontend statique : **PASS** ;
- validation alignement Enterprise : **PASS** ;
- validation des six profils installateur : **PASS**.

La couverture globale exacte n'a pas été recalculée dans le sandbox pour cette correction : la suite d'intégration monolithique reste bloquée lors de la fermeture de certaines ressources réseau, après exécution sans échec apparent. Le seuil CI `--cov-fail-under=98` demeure inchangé et bloquant. La livraison 0.31.3 de référence validait **98,00240427654296 %** ; les nouvelles branches du préflight sont couvertes par les tests ciblés succès et refus.

### Frontend

- `npm ci` : **PASS** ;
- tests Node : **60 réussis** ;
- validation statique/ESLint : **PASS** ;
- build Vite : **PASS** ;
- chunks dynamiques : **11** ;
- `npm audit --audit-level=high` : **PASS**, 0 vulnérabilité.

### Packaging

- build isolé wheel/sdist : **PASS** ;
- installation du wheel dans un environnement Python vierge : **PASS** ;
- `pip check` : **PASS** ;
- smoke installé : version, OpenAPI, assets runtime et migrations **PASS**.

## Limites de validation

Docker n'est pas installé dans le sandbox. L'image n'a donc pas pu être démarrée localement ; l'identité Dockerfile, le propriétaire tmpfs Compose, le préflight applicatif et leurs tests sont validés statiquement et fonctionnellement. La commande de reconstruction `--no-cache` est obligatoire lors du déploiement afin de ne pas réutiliser l'ancienne couche créant l'utilisateur dynamique.
