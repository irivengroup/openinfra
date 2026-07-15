# Rapport de validation — OpenInfra Python POO v0.33.8

## Objet de la livraison

La version **0.33.8** corrige l'erreur PostgreSQL :

```text
postgresql operation requires an active unit of work
```

La cause était une divergence entre les backends JSON et PostgreSQL dans les services Kubernetes récents. Le backend JSON acceptait des lectures directes de repository, tandis que les repositories PostgreSQL imposent explicitement une connexion liée à un `UnitOfWork` actif. Plusieurs chemins Kubernetes effectuaient donc encore des lectures de repository hors frontière transactionnelle.

Aucune migration, route API, commande CLI, permission RBAC ou modification de thème n'est introduite.

## Correctif transactionnel

### Kubernetes topology

Les opérations suivantes s'exécutent désormais dans un `UnitOfWork` actif :

- recherche d'un snapshot existant lors d'un import idempotent ;
- lecture d'un snapshot précis ;
- lecture du dernier snapshot d'un cluster ;
- listing paginé des snapshots ;
- calcul des expositions cloud-native ;
- corrélation sécurité SBOM/PKI/secrets référencés ;
- tendance de capacité cluster/namespace.

La vérification d'idempotence d'un import et l'écriture du snapshot/outbox/audit partagent désormais la même unité de travail.

### Kubernetes GitOps

Les opérations suivantes s'exécutent désormais dans un `UnitOfWork` actif :

- recherche d'un état GitOps existant lors d'un import idempotent ;
- lecture d'un état précis ;
- lecture du dernier état d'un cluster ;
- listing paginé des états ;
- lecture de l'état attendu et du snapshot observé pour une évaluation ;
- écriture de l'audit et de l'événement de dérive.

Une évaluation GitOps utilise une seule frontière transactionnelle pour ses lectures et écritures. La transaction imbriquée précédente a été supprimée afin de conserver une liaison PostgreSQL déterministe.

## Test de non-régression

Le nouveau test :

```text
tests/integration/test_kubernetes_unit_of_work_regression.py
```

instrumente les repositories Kubernetes, GitOps, Flow Matrix et SBOM et échoue immédiatement si une méthode est appelée sans unité de travail active.

Il couvre notamment :

- imports idempotents ;
- lecture/listing/latest ;
- exposition ;
- sécurité ;
- tendance de capacité ;
- import/listing GitOps ;
- évaluation GitOps précise et latest.

Le sdist doit désormais obligatoirement embarquer ce test de non-régression.

## Validation exécutée

### Python

- collecte globale : **1 378 tests** ;
- tests unitaires : **654/654 PASS** ;
- tests performance : **11/11 PASS** ;
- régression Kubernetes ciblée services/API/CLI/PostgreSQL/UnitOfWork : **32/32 PASS** ;
- job CI `Transactional outbox and specialized workers regression` : **63/63 PASS** ;
- nouveau test de discipline `UnitOfWork` : **PASS**.

### Qualité statique

- Ruff format : **411 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **120 modules conformes** ;
- `compileall` : **PASS**.

### Contrats Kubernetes et release

- EPIC-2101 Topologie Kubernetes : **PASS** ;
- EPIC-2102 Expositions cloud-native : **PASS** ;
- EPIC-2103 Corrélation sécurité : **PASS** ;
- EPIC-2104 GitOps drift : **PASS** ;
- EPIC-2105 Capacité cluster/namespace : **PASS** ;
- OpenAPI produit : **PASS** ;
- OpenAPI CDC : **PASS** ;
- documentation GA 0.33.8 : **PASS** ;
- validateur frontend : **PASS** ;
- alignement Enterprise : **PASS**.

### Frontend

- tests Node : **79/79 PASS** ;
- contrat statique : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint JSX/a11y : **PASS** ;
- build Vite : **PASS** ;
- validation bundle : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

### Sécurité

- `security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, sans finding bloquant ;
- `pip-audit --strict -r requirements/runtime.txt` : **non validé localement**, échec de résolution DNS vers `pypi.org`.

### Packaging

- wheel `openinfra-0.33.8-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.8.tar.gz` : **PASS** ;
- vérification du contenu des artefacts : **PASS** ;
- smoke du wheel réellement installé hors de l'arbre source : **PASS** ;
- version installée : **0.33.8** ;
- routes Kubernetes : **16** ;
- migrations : **56** ;
- dernière migration : `0056_kubernetes_gitops_drift.sql` ;
- assets runtime : **20**.

## Non-régression visuelle

Le fichier CSS runtime principal est strictement inchangé :

```text
fb7feabe378613ac41efb18db94b0d95a8faa916b6f782c9fd0ea2b0d8e9fcf4
```

Aucune couleur, surface, transparence, règle de hover ou comportement du thème n'a été modifié.

## Limites locales

- la couverture globale du dépôt n'a pas été recalculée intégralement ; le seuil contractuel **>= 98 %** reste bloquant dans GitHub Actions ;
- `pip-audit` n'a pas pu joindre PyPI à cause d'un échec de résolution DNS ;
- Docker n'est pas disponible dans l'environnement courant ; les smokes Docker Compose restent délégués à la CI.

## Documentation de planification

Le **CDC 4.9.0** et la **roadmap v2.2** restent inchangés. Cette livraison corrige une régression transactionnelle d'implémentation sans nouvelle exigence métier, réglementaire ou architecturale.
