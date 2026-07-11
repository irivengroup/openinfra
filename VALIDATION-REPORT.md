# OpenInfra v0.29.100 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.100`  
Périmètre : correctif bloquant du démarrage du portail web packagé

## Résultat global

La livraison corrige l'écran blanc observé sur `openinfra-web`. Le runtime statique référençait `FIELD_SETS.cursor` dans cinq opérations SBOM sans déclarer ce champ partagé. Les tableaux de champs contenaient donc des valeurs `undefined`, puis le calcul des métriques du Dashboard levait une exception sur `field.required` avant tout rendu.

- Tests Python collectés et validés : **888 PASS** dans **146 fichiers**.
- Tests unitaires : **375 PASS**.
- Tests d'intégration : **509 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture exacte : **98,0029060 %**, soit **31 701 / 32 347** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **36 PASS**.
- Ruff format et lint : **PASS** sur **247 fichiers**.
- mypy strict : **PASS** sur **82 modules**.
- Bandit, compilation, gates sécurité et qualité : **PASS**.
- OpenAPI strict sans clé YAML dupliquée : **PASS**.
- Contrat WCAG 2.2 AA, JSX-a11y, build Vite et audit npm : **PASS**.
- Audit npm production : **0 vulnérabilité**.

## Correctifs validés

- Déclaration du champ partagé `FIELD_SETS.cursor` utilisé par les listes SBOM.
- Validation statique de toutes les références `FIELD_SETS.*` par `scripts/validate_frontend.py`.
- Validation runtime du catalogue des composants, opérations et champs.
- Compatibilité conservée avec les anciens champs définis par simple libellé texte.
- Calcul des métriques rendu défensif avec `field?.required`.
- Premier rendu du Dashboard avant les appels `/config.json`, `/version`, `/ready`, `/status` et catalogues backend.
- Écran d'erreur fatal accessible si le point de montage, le catalogue ou l'initialisation JavaScript échoue.
- Gestion explicite des rejets asynchrones de `start()`.
- Revalidation HTTP systématique de `index.html` et des assets non versionnés (`Cache-Control: no-cache, max-age=0, must-revalidate`) pour empêcher la conservation de l’ancien bundle défectueux.
- Test de non-régression vérifiant qu'une référence partagée manquante est rejetée par le gate frontend.

## Reproduction navigateur

Le runtime JavaScript packagé a été exécuté dans un navigateur headless avec réponses backend simulées :

- avant correction : exception `Cannot read properties of undefined (reading 'required')` et racine vide ;
- après correction : Dashboard rendu, racine DOM non vide et aucune exception de démarrage.

## Packaging et compatibilité

- Version synchronisée dans `VERSION`, `pyproject.toml`, package Python, package frontend, Compose, `.env.example` et OpenAPI.
- Aucune route API, commande CLI, permission, migration ou structure de données modifiée.
- Total migrations PostgreSQL inchangé : **48**.
- Wheel et sdist `0.29.100` construits avec succès.
- Installation du wheel dans une cible vierge : **PASS**.
- Smoke installé : version, routes historiques, 48 migrations, quatre assets runtime et trois points d'entrée publics : **PASS**.

## Performance

Benchmark déterministe sur **5 000 nœuds** et **100 SPOF** :

| Scénario | p95 observé | Seuil |
|---|---:|---:|
| Graphe à un niveau | 261,993 ms | 1 500 ms |
| Graphe filtré | 125,338 ms | 1 500 ms |
| Analyse SPOF | 258,961 ms | 5 000 ms |
| Pagination SPOF complète | 652,891 ms | 15 000 ms |

Tous les seuils passent.

## Limites de l'environnement

- `pip-audit` n'a pas pu interroger `pypi.org` en raison de l'échec de résolution DNS du runner.
- Docker, Podman et PostgreSQL live ne sont pas disponibles dans l'environnement courant.
- Les recettes statiques, installateurs, runtime natif et package installé ont néanmoins été validés.

Le CDC et la roadmap restent inchangés : ce correctif ne modifie aucune exigence fonctionnelle, technique, réglementaire ou architecturale.
