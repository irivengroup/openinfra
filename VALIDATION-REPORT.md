# Rapport de validation — OpenInfra Python POO v0.33.6

## Objet de la livraison

La version **0.33.6** implémente **P21 / REL-11 / EPIC-2105 — Capacité cluster et namespace**.

Cette livraison ajoute des read models de capacité Kubernetes sans créer de nouvelle source de vérité : les métriques de capacité sont portées par les snapshots Kubernetes immuables existants, et les agrégats sont calculés à la demande avec des bornes strictes.

Aucun endpoint historique, aucune commande CLI, aucune permission RBAC et aucune opération de portail existante n'est supprimé ou renommé.

## EPIC-2105 — Capacité cluster et namespace

### Mesures prises en charge

Les snapshots Kubernetes peuvent désormais porter des mesures normalisées et typées :

- **Node** : capacité CPU, mémoire et stockage ;
- **Pod** : demandes, limites et consommation CPU/mémoire ;
- **Volume** : demandes, limites, consommation et capacité de stockage.

Les unités sont explicites :

- CPU : `millicores` ;
- mémoire et stockage : `bytes`.

Les valeurs doivent être des entiers non négatifs et les invariants `request <= limit` sont validés lorsque les deux valeurs existent.

### Read models

Le moteur produit :

- capacité agrégée du cluster ;
- capacité agrégée par namespace ;
- marges disponibles ;
- pourcentages d'utilisation et de réservation ;
- alertes `warning` et `critical` selon des seuils paramétrables ;
- tendances chronologiques bornées ;
- exports JSON et CSV.

Le calcul est déterministe et n'écrit aucune donnée supplémentaire.

### Bornes de protection

Les tendances sont limitées à :

- **96 snapshots maximum** ;
- **1 000 000 de ressources cumulées maximum**.

Le rapport signale explicitement `truncated=true` lorsqu'une borne empêche de couvrir tout l'historique demandé.

## API et CLI

Cinq nouvelles routes sont exposées :

- `GET /api/v1/kubernetes/topologies/capacity`
- `GET /api/v1/kubernetes/topologies/latest-capacity`
- `GET /api/v1/kubernetes/topologies/capacity-trend`
- `GET /api/v1/kubernetes/topologies/capacity-export`
- `GET /api/v1/kubernetes/topologies/latest-capacity-export`

Les commandes CLI correspondantes sont disponibles :

- `openinfra kubernetes capacity`
- `openinfra kubernetes latest-capacity`
- `openinfra kubernetes capacity-trend`
- `openinfra kubernetes capacity-export`
- `openinfra kubernetes latest-capacity-export`

Swagger/ReDoc classe ces opérations sous **Discovery · Kubernetes et cloud-native**.

Le catalogue runtime contient désormais **293 opérations uniques**.

## Persistance et compatibilité

Aucune nouvelle migration n'est requise.

La livraison conserve **56 migrations**, la dernière étant :

- `0056_kubernetes_gitops_drift.sql`

Les métriques de capacité sont stockées dans les attributs JSONB des snapshots Kubernetes existants. Les snapshots historiques qui ne contiennent pas de capacité conservent leur sérialisation et leur fingerprint antérieurs.

## Industrialisation

EPIC-2105 est intégré à :

- `scripts/validate_kubernetes_capacity.py` ;
- GitHub Actions ;
- `scripts/quality_gate.py` ;
- la vérification du wheel et du sdist ;
- le smoke test du wheel installé.

Le validateur vérifie notamment :

- la parité API / CLI / UI ;
- la présence des read models cluster et namespace ;
- les tendances bornées ;
- les alertes ;
- les exports JSON/CSV ;
- la stabilité de la chaîne de migrations.

## Non-régression visuelle

Aucune modification du thème ou de la charte graphique n'a été introduite.

Le fichier CSS runtime principal est strictement identique à celui de la v0.33.5 :

`fb7feabe378613ac41efb18db94b0d95a8faa916b6f782c9fd0ea2b0d8e9fcf4`

## Validation exécutée

### Python

- **1 377 tests collectés** ;
- **654/654 tests unitaires : PASS** ;
- **11/11 tests performance : PASS** ;
- **46/46 tests d'intégration Kubernetes : PASS** ;
- **31/31 tests d'intégration transverses rapides : PASS** ;
- tests ciblés EPIC-2105 : **PASS** ;
- couverture ciblée du nouveau moteur `kubernetes_capacity.py` : **204/204 instructions, 100 %** ;
- Ruff format, périmètre CI `src tests scripts` : **410 fichiers conformes** ;
- Ruff lint, périmètre CI `src tests scripts` : **PASS** ;
- mypy strict sur les **5 fichiers source modifiés directement** : **PASS** ;
- `compileall` sur `src tests scripts` : **PASS**.

Le lancement mypy monolithique sur tout `src/openinfra` a dépassé la fenêtre locale sans produire de résultat final ; il n'est donc pas déclaré comme validé globalement dans ce rapport.

### Frontend

- **78/78 tests : PASS** ;
- contrat frontend statique : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint : **PASS** ;
- build Vite : **PASS** ;
- budgets de chargement : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

### Sécurité et contrats

- `security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, aucun finding bloquant ;
- validateurs EPIC-2101 à EPIC-2105 : **PASS** ;
- OpenAPI produit + CDC : **PASS** ;
- documentation GA 0.33.6 : **PASS** ;
- roadmap v2.2 : **PASS** ;
- alignement Enterprise : **PASS**.

### Packaging

- wheel 0.33.6 : **PASS** ;
- sdist 0.33.6 : **PASS** ;
- vérification du contenu des artefacts : **PASS** ;
- smoke du wheel réellement installé hors de l'arbre source : **PASS** ;
- version installée : **0.33.6** ;
- routes Kubernetes installées : **16** ;
- assets runtime : **20** ;
- migrations : **56** ;
- dernière migration : `0056_kubernetes_gitops_drift.sql`.

## Limites locales

La suite globale `tests/architecture + tests/integration` n'a pas été intégralement exécutée dans ce sandbox. Les périmètres Kubernetes et transverses directement concernés ont été validés séparément.

Le test `tests/integration/test_runtime_docker_environment.py` n'a pas produit de verdict final avant le timeout local et n'est pas déclaré comme validé.

La couverture globale du dépôt n'a pas été recalculée intégralement. Le seuil contractuel **>= 98 %** reste bloquant dans GitHub Actions.

`pip-audit --strict` n'a pas produit de résultat final avant le timeout lié à l'accès au service PyPI ; il n'est pas déclaré comme validé localement.

Docker n'est pas disponible dans cet environnement. Les smokes Docker Compose restent délégués à la CI.

## Documents de référence

Le **CDC 4.9.0** et la **roadmap v2.2** restent inchangés : EPIC-2105 était déjà planifié et cette implémentation n'introduit aucune nouvelle exigence normative ou architecturale nécessitant leur révision.
