# OpenInfra v0.31.0 — rapport de validation

Date : 2026-07-12

## Périmètre

Cette livraison réalise le premier incrément autonome de **P20 / EPIC-2003 — outbox transactionnelle et workers spécialisés** sans modifier le thème approuvé en 0.30.9.

- file de travaux durable et multi-tenant ;
- idempotence par opération et clé métier ;
- leases expirants avec jetons de fencing monotones ;
- reprise après expiration, renouvellement contrôlé et finalisation protégée ;
- retries bornés, DLQ et rejeu audité ;
- outbox transactionnelle et publication idempotente ;
- artefacts hors PostgreSQL, sur stockage local atomique ou S3 compatible signé AWS SigV4 ;
- worker pilote de reporting et dispatcher d’outbox ;
- parité domaine, application, persistance JSON/PostgreSQL, CLI, API HTTP et OpenAPI ;
- migration PostgreSQL `0054_async_outbox_workers.sql` partitionnée par tenant ;
- aucune modification CSS ni régression du thème.

Les exigences textuelles du CDC v4.9.0 et la roadmap v2.1 ne sont pas rééditées : `REQ-00835`, `REQ-00839`, `CDC-PERF-006`, `EPIC-2003` et `TST-P20-OUTBOX-WORKERS` couvraient déjà cet incrément. Seul le miroir OpenAPI placé dans le répertoire du CDC est synchronisé avec le contrat runtime ; la traçabilité d’implémentation est ajoutée dans `docs/TRACEABILITY.md`.

## Fichiers principaux

- `src/openinfra/domain/async_processing.py`
- `src/openinfra/application/async_processing_services.py`
- `src/openinfra/infrastructure/async_processing.py`
- `src/openinfra/infrastructure/postgresql.py`
- `src/openinfra/interfaces/cli.py`
- `src/openinfra/interfaces/http_api.py`
- `installers/migrations/postgresql/0054_async_outbox_workers.sql`
- `docs/architecture/transactional-outbox-workers.md`
- `docs/runbooks/ASYNC_WORKERS.md`
- `docs/api/openapi.yaml`
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml`
- tests unitaires, intégration, concurrence, migration, interfaces et packaging associés.

## Invariants vérifiés

- vingt-quatre soumissions concurrentes avec la même clé ne créent qu’un job et un événement outbox ;
- un worker dont le lease a expiré ne peut plus renouveler, terminer ou échouer le travail avec un jeton obsolète ;
- un job terminé ne peut pas être validé sans référence d’artefact résultat ;
- l’expiration d’un lease réinsère le travail dans le cycle de reprise sans perte ;
- le nombre maximal de tentatives mène obligatoirement à la DLQ ;
- un rejeu DLQ réinitialise explicitement l’état sans réutiliser un ancien fencing token ;
- une publication outbox déjà acquittée reste idempotente ;
- l’intégrité des artefacts est contrôlée par SHA-256 ;
- les chemins locaux sont bornés au répertoire configuré et écrits atomiquement ;
- les requêtes S3 compatibles sont signées AWS SigV4 sans secret en code ;
- l’isolation tenant est imposée dans les services, dépôts et clés de stockage ;
- les opérations PostgreSQL s’exécutent dans une unité de travail et l’idempotence concurrente utilise un verrou consultatif transactionnel.

## Validations exécutées

### Python et contrats

- collection : **1 066 tests** sur **185 fichiers** ;
- exécution complète par lots déterministes : **PASS**, aucune erreur ;
- couverture : **37 272 / 38 032 lignes**, soit **98,0016827934 %** ;
- seuil bloquant `--fail-under=98` : **PASS**, sans arrondi ni exclusion ajoutée ;
- Ruff format : **PASS**, 303 fichiers conformes ;
- Ruff lint : **PASS** ;
- mypy strict : **PASS**, 97 modules source ;
- `compileall` : **PASS** ;
- Bandit : **PASS**, aucun finding bloquant ;
- gate de sécurité du dépôt : **PASS** ;
- validation des installateurs : **PASS**, 6 profils ;
- validation frontend statique depuis Python : **PASS** ;
- validation des deux documents OpenAPI : **PASS** ;
- tests de workflow GitHub Actions, migrations, packaging et smoke runtime : **PASS**.

La suite instrumentée est exécutée en partitions déterministes dans ce sandbox, car le processus monolithique avec xdist dépasse sa fenêtre de fermeture. Les données de couverture des mêmes fichiers source sont combinées puis vérifiées par le gate officiel ; aucun test ni seuil n’est désactivé.

### Frontend

- tests Node : **53 réussis** ;
- ESLint : **PASS** ;
- contrôles WCAG 2.2 AA statiques et JSX : **PASS** ;
- build Vite : **PASS** ;
- `npm audit --audit-level=high` : **PASS**, 0 vulnérabilité ;
- diff CSS : **vide**.

### Persistance et concurrence

- migration `0054` : contraintes, transitions d’état, index de claim/DLQ/audit et **16 partitions hash** validés ;
- politique PostgreSQL multi-tenant : **PASS** ;
- idempotence concurrente : **PASS** ;
- reprise, fencing, retries, DLQ et rejeu : **PASS** ;
- adaptateurs JSON, PostgreSQL, filesystem et S3 compatible : **PASS**.

### Packaging

- construction isolée Hatchling du wheel et du sdist : **PASS** ;
- vérification structurelle des deux distributions : **PASS** ;
- installation du wheel dans un environnement Python vierge avec ses seules dépendances runtime : **PASS** ;
- `pip check` : **PASS**, aucune dépendance cassée ;
- smoke test installé : **PASS** — version `0.31.0`, 18 routes asynchrones, 54 migrations, OpenAPI, assets runtime et scripts console ;
- commande `openinfra async --help` : **PASS**, 19 sous-commandes exposées.

## Limites de validation

- aucun serveur PostgreSQL ni endpoint S3 externe n’est disponible dans le sandbox ; les contrats SQL, migrations, transactions, signatures SigV4, erreurs réseau et adaptateurs sont couverts par tests déterministes, mais la qualification d’infrastructure réelle reste un gate de déploiement Pro/Entreprise ;
- `pip-audit --strict --requirement requirements/security-audit.txt` n’a pas pu interroger `pypi.org` à cause d’une indisponibilité DNS du sandbox ; le gate CI réseau demeure inchangé et bloquant ;
- les benchmarks de charge représentatifs de `GATE-09` restent hors du périmètre de cet incrément fonctionnel pilote.

## Risques résiduels

Le risque fonctionnel est faible et concentré sur l’intégration avec les infrastructures PostgreSQL/S3 réelles. Il est maîtrisé par les contraintes de schéma, les tests de concurrence, les contrats d’adaptateurs, l’idempotence, le fencing et les runbooks de reprise. EPIC-2003 reste ouvert pour le branchement des workers imports, graphes et RAG ; ces incréments devront réutiliser ce socle sans dupliquer les mécanismes de file ou de persistance.
