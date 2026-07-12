# OpenInfra v0.31.2 — rapport de validation

Date : 2026-07-12

## Périmètre

Cette livraison implémente **P20 / EPIC-2004 — frontend modulaire et virtualisé** sans modifier la charte graphique approuvée.

- séparation du portail en huit chunks métier chargés à la navigation : `RSOT`, `IPAM`, `DCIM`, `ITAM`, `Discovery`, `Data`, `Intégrations` et `Sécurité` ;
- Dashboard limité au manifeste statistique et au shell initial ;
- index de recherche globale et taxonomie RSOT chargés à la demande ;
- cache de requêtes éphémère, dédupliqué, borné par TTL/LRU et protégé contre les réponses obsolètes concurrentes ;
- annulation des lectures avec `AbortController` et invalidation ciblée après mutation ;
- virtualisation des résultats volumineux au-delà de 40 éléments ;
- collecte bornée en mémoire des Web Vitals avec budgets LCP, INP et tâches longues ;
- chunks Vite distincts pour le portail React et parité avec le runtime statique livré ;
- budgets de transfert et de bundle intégrés aux tests et à la CI ;
- aucune modification d'API, de CLI, de modèle métier ou de schéma PostgreSQL ;
- aucune modification CSS ni régression de la charte graphique.

Les exigences textuelles du CDC v4.9.0 et la roadmap v2.1 ne sont pas rééditées : `EPIC-2004` et ses critères décrivent déjà ce périmètre. Le miroir OpenAPI est uniquement synchronisé avec la version applicative.

## Fichiers principaux

### Runtime statique livré

- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.js`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-domain-manifest.js`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-search-index.js`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-query-cache.js`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-virtual-list.js`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web-vitals.js`
- `src/openinfra/interfaces/rendering/static/assets/domains/*.js`

### Portail React/Vite

- `web/src/domain-manifest.js`
- `web/src/domains/*.js`
- `web/src/core/query-cache.js`
- `web/src/core/virtual-window.js`
- `web/src/core/web-vitals.js`
- `web/src/VirtualizedList.jsx`
- `web/src/bootstrap.js`
- `web/src/main.jsx`
- `web/vite.config.js`
- `web/scripts/validate-bundle.mjs`

### Validation, CI et documentation

- `scripts/validate_frontend.py`
- `scripts/verify_artifact.py`
- `scripts/smoke_installed_wheel.py`
- `.github/workflows/ci.yml`
- `tests/integration/test_frontend_modular_performance.py`
- `docs/architecture/modular-virtualized-frontend.md`
- `docs/operations/frontend-performance.md`

## Invariants vérifiés

- le shell initial n'embarque aucune définition d'opération métier ;
- les 274 identifiants d'opération restent uniques et disponibles après chargement du domaine concerné ;
- les huit domaines existent dans les deux portails et restent des chunks dynamiques ;
- le Dashboard ne déclenche pas le chargement des catalogues métier ;
- le cache ne persiste aucune donnée dans `localStorage`, `sessionStorage` ou IndexedDB ;
- une requête déjà en vol est dédupliquée ;
- une réponse ancienne ne peut pas repeupler le cache après invalidation ou mutation ;
- la virtualisation borne le nombre de nœuds rendus tout en conservant la géométrie complète du défilement ;
- les métriques de performance restent bornées en mémoire et ne bloquent pas l'interface ;
- la recherche globale, les formulaires, la navigation responsive et l'accessibilité conservent leur comportement ;
- les feuilles CSS restent identiques à la version 0.31.1.

## Validations exécutées

### Python et contrats

- collection : **1 093 tests** sur **188 fichiers** ;
- exécution complète par partitions déterministes : **PASS**, aucune erreur ;
- couverture : **37 558 / 38 322 lignes**, soit **98,00636709983822 %** ;
- seuil bloquant `--fail-under=98` : **PASS**, sans arrondi ni exclusion ajoutée ;
- Ruff format : **PASS**, 308 fichiers conformes ;
- Ruff lint : **PASS** ;
- mypy strict : **PASS**, 98 modules source ;
- `compileall` : **PASS** ;
- Bandit : **PASS**, aucun finding bloquant ;
- gate de sécurité du dépôt : **PASS** ;
- gate qualité interne : **PASS** ;
- validation des six profils installateur : **PASS** ;
- validation de l'alignement Enterprise : **PASS** ;
- validation CDC/roadmap : **PASS** ;
- validation des deux contrats OpenAPI : **PASS** ;
- smoke des assets runtime natifs : **PASS**.

La suite instrumentée est exécutée par partitions dans ce sandbox afin d'éviter le blocage de fermeture de certains serveurs de test après la fin de pytest. Chaque partition sauvegarde son statut et sa mesure avant consolidation dans une base de couverture unique. Aucun test ni seuil n'est désactivé.

### Frontend

- tests Node : **60 réussis** ;
- validation des assets statiques et des 274 opérations : **PASS** ;
- ESLint JSX : **PASS** ;
- contrôles WCAG 2.2 AA : **PASS** ;
- build Vite : **PASS** ;
- chunks dynamiques produits : **11**, dont les huit domaines métier, la recherche globale et la taxonomie RSOT ;
- bundle Vite initial JavaScript : **2 556 octets** ;
- bundle Vite initial compressé : **1 260 octets** avant chargement différé de l'application ;
- runtime statique initial JavaScript : **208 115 octets** — 203,24 Kio, seuil 250 Kio ;
- runtime statique initial compressé : **95 642 octets** — 93,40 Kio, seuil 150 Kio ;
- `npm audit --audit-level=high` : **PASS**, 0 vulnérabilité ;
- installation Node CI verrouillée par `npm ci` ;
- le validateur de bundle vérifie explicitement les huit chunks métier, y compris `Intégrations`.

### Charte graphique

Les fichiers suivants sont strictement identiques octet par octet à la version 0.31.1 et partagent le SHA-256 `1df955fd51fdd253590c391a3ee9430c9ca9db88b76819f4482007a5cf567dad` :

- `web/src/openinfra-theme.css` ;
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`.

### Interfaces et persistance

- contrats API et CLI : non-régression **PASS** ;
- migrations PostgreSQL embarquées : **54**, aucune nouvelle migration ;
- services asynchrones et workers spécialisés : non-régression **PASS** ;
- navigation, recherche, formulaires et catalogues métier : parité runtime/React **PASS** ;
- package runtime : manifeste, cache, virtualisation, Web Vitals et huit chunks de domaine présents.

## Packaging

- construction isolée Hatchling du wheel et du sdist : **PASS** ;
- vérification du contenu obligatoire du wheel et du sdist : **PASS** ;
- wheel : version `0.31.2`, OpenAPI, 54 migrations et 17 assets runtime modulaires présents ;
- sdist : code, tests, CI, documentation, installateurs et rapport de validation présents ;
- installation du wheel avec ses seules dépendances runtime dans un environnement Python vierge : **PASS** ;
- `pip check` : **PASS**, aucune dépendance cassée ;
- smoke du package installé : **PASS** — 22 routes asynchrones, 54 migrations et dernier script `0054_async_outbox_workers.sql` ;
- commande `openinfra version` : **PASS**, résultat `0.31.2` ;
- commande `openinfra async --help` : **PASS**, 20 sous-commandes exposées ;
- contrôle d'intégrité ZIP/TAR/Wheel et nettoyage des caches : exécuté lors du scellement final des artefacts.

## Limites de validation

- aucun serveur PostgreSQL ni endpoint S3 externe n'est disponible dans le sandbox ; les contrats SQL, transactions et adaptateurs restent couverts par les tests déterministes existants ;
- `pip-audit --strict --requirement requirements/security-audit.txt` dépend de l'accès à `pypi.org` et peut rester non exécutable si la résolution DNS du sandbox est indisponible ; le gate CI réseau reste inchangé et bloquant ;
- les Web Vitals réels dépendent du navigateur, du terminal et du réseau de production ; les budgets et observateurs sont testés, mais leur qualification terrain reste un gate de déploiement.

## Risques résiduels

Le risque fonctionnel résiduel est faible. Il se concentre sur la performance réelle des navigateurs les plus anciens, la qualité réseau et la taille future des catalogues. Les budgets CI, le chargement différé, l'annulation, la protection générationnelle du cache, la virtualisation et la télémétrie bornée permettent de détecter et contenir ces dérives sans revenir à un frontend monolithique.
