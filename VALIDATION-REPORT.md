# OpenInfra v0.31.1 — rapport de validation

Date : 2026-07-12

## Périmètre

Cette livraison clôt le périmètre fonctionnel de **P20 / EPIC-2003 — outbox transactionnelle et workers spécialisés** en branchant les traitements imports, graphes et RAG sur l'infrastructure asynchrone durable introduite en 0.31.0, sans modifier le thème approuvé.

- worker `reporting` pour l'état de la file asynchrone ;
- worker `imports` pour les imports unitaires et massifs depuis un artefact externe ;
- worker `graph` pour la traversée, l'analyse d'impact, le calcul de chemin, la détection SPOF et l'export ;
- worker `rag` pour la synchronisation RSOT, l'import documentaire et l'export des réponses ;
- dépôt contrôlé d'artefacts d'entrée par CLI et HTTP ;
- résultats volumineux externalisés dans l'object store avec intégrité SHA-256 ;
- rôles dédiés en moindre privilège pour chaque spécialisation ;
- parité domaine, application, persistance, CLI, HTTP, OpenAPI, documentation et tests ;
- aucune migration supplémentaire : le schéma `0054_async_outbox_workers.sql` de 0.31.0 couvre les nouvelles spécialisations ;
- aucune modification CSS ni régression de la charte graphique.

Les exigences textuelles du CDC v4.9.0 et la roadmap v2.1 ne sont pas rééditées, car `REQ-00835`, `REQ-00839`, `CDC-PERF-006`, `EPIC-2003` et `TST-P20-OUTBOX-WORKERS` décrivent déjà le périmètre. Le miroir OpenAPI inclus dans le CDC est synchronisé avec le contrat runtime.

## Fichiers principaux

- `src/openinfra/domain/async_processing.py`
- `src/openinfra/application/async_processing_services.py`
- `src/openinfra/application/specialized_worker_services.py`
- `src/openinfra/application/container.py`
- `src/openinfra/application/security_services.py`
- `src/openinfra/interfaces/cli.py`
- `src/openinfra/interfaces/http_api.py`
- `docs/architecture/transactional-outbox-workers.md`
- `docs/runbooks/ASYNC_WORKERS.md`
- `docs/api/openapi.yaml`
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml`
- tests unitaires et d'intégration des workers, autorisations, interfaces et packaging.

## Invariants vérifiés

- un worker ne réclame que les jobs correspondant à sa spécialisation ;
- les payloads sont strictement typés et les opérations non supportées sont rejetées explicitement ;
- les imports consomment un artefact externe, utilisent les services d'import existants et produisent un rapport immuable ;
- les cinq opérations graphe utilisent les services métier existants et externalisent leurs résultats ;
- l'import documentaire RAG est borné à 10 000 documents par job ;
- l'export de réponses RAG est borné à 10 000 résultats et supporte JSON et CSV ;
- les erreurs de payload, de lecture d'artefact ou d'exécution passent par le cycle retries/DLQ du socle 0.31.0 ;
- les artefacts d'entrée sont soumis par un utilisateur autorisé et audités ;
- les rôles workers possèdent uniquement les permissions asynchrones et métier nécessaires ;
- les contenus volumineux ne sont pas insérés dans PostgreSQL ;
- l'isolation tenant, le fencing, l'idempotence et les transitions d'état restent appliqués par le socle commun.

## Validations exécutées

### Python et contrats

- collection : **1 087 tests** sur **187 fichiers** ;
- exécution complète par partitions déterministes : **PASS**, aucune erreur ;
- couverture : **37 558 / 38 322 lignes**, soit **98,006367099838 %** ;
- seuil bloquant `--fail-under=98` : **PASS**, sans arrondi ni exclusion ajoutée ;
- Ruff format : **PASS**, 306 fichiers conformes ;
- Ruff lint : **PASS** ;
- mypy strict : **PASS**, 98 modules source ;
- `compileall` : **PASS** ;
- Bandit : **PASS**, aucun finding bloquant ;
- gate de sécurité du dépôt : **PASS** ;
- gate qualité interne : **PASS** ;
- validation des 6 profils installateur : **PASS** ;
- validation de l'alignement CDC/roadmap : **PASS** ;
- smoke des assets runtime natifs : **PASS** ;
- validation des deux documents OpenAPI : **PASS**.

La suite instrumentée est exécutée en partitions dans ce sandbox afin d'éviter la limite de fermeture du processus monolithique sous xdist. Les mêmes fichiers source sont mesurés dans une base de couverture unique, consolidée puis vérifiée par le gate officiel. Aucun test ni seuil n'est désactivé.

### Frontend

- tests Node : **53 réussis** ;
- validation des assets statiques : **PASS** ;
- ESLint JSX : **PASS** ;
- contrôles WCAG 2.2 AA : **PASS** ;
- build Vite : **PASS** ;
- `npm audit --audit-level=high` : **PASS**, 0 vulnérabilité ;
- les feuilles `web/src/openinfra-theme.css` et `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css` sont **strictement identiques octet par octet** à la version 0.31.0.

### Interfaces et persistance

- contrat OpenAPI : **341 chemins**, dont **22 opérations asynchrones** ;
- CLI `openinfra async` : **20 sous-commandes** ;
- migrations PostgreSQL embarquées : **54**, aucune nouvelle migration dans cet incrément ;
- upload d'artefacts CLI/HTTP : **PASS** ;
- workers reporting/imports/graph/RAG via CLI et HTTP : **PASS** ;
- rôles dédiés et permissions minimales : **PASS** ;
- adaptateurs JSON, PostgreSQL, filesystem et S3 compatible : non-régression **PASS**.

## Packaging

- construction isolée Hatchling du wheel et du sdist : **PASS** ;
- contrôle d’intégrité ZIP/TAR : **PASS** ;
- wheel : migration `0054`, 54 migrations, OpenAPI et assets runtime présents ;
- sdist : code, tests, documentation, scripts, installateurs et rapport de validation présents ;
- installation du wheel dans un environnement Python vierge avec ses seules dépendances runtime : **PASS** ;
- `pip check` : **PASS**, aucune dépendance cassée ;
- smoke du wheel installé : **PASS** — version `0.31.1`, 22 routes asynchrones, 54 migrations et assets runtime ;
- commande `openinfra async --help` : **PASS**, 20 sous-commandes exposées.

## Limites de validation

- aucun serveur PostgreSQL ni endpoint S3 externe n'est disponible dans le sandbox ; les contrats SQL, transactions, signatures SigV4, erreurs réseau et adaptateurs sont couverts par tests déterministes, mais leur qualification sur l'infrastructure cible reste un gate de déploiement Pro/Entreprise ;
- `pip-audit --strict --requirement requirements/security-audit.txt` n'a pas pu interroger `pypi.org` en raison d'une indisponibilité DNS du sandbox ; le gate CI réseau reste inchangé et bloquant ;
- les benchmarks de charge représentatifs de `GATE-09` restent un gate de qualification de l'environnement cible et ne sont pas simulés par des chiffres artificiels.

## Risques résiduels

Le risque fonctionnel résiduel est faible. Il se concentre sur les caractéristiques de l'infrastructure réelle : latence et disponibilité PostgreSQL/S3, dimensionnement des workers, débit d'artefacts et politiques de rétention. Les mécanismes d'idempotence, de fencing, de retries, de DLQ, d'isolation tenant, de limitation des lots et d'intégrité SHA-256 réduisent ces risques. Le passage à l'étape suivante de la roadmap peut désormais s'appuyer sur un socle EPIC-2003 complet sans dupliquer les mécanismes de file, d'outbox ou de stockage d'artefacts.
