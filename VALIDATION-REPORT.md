# Rapport de validation — OpenInfra Python POO v0.33.7

## Objet de la livraison

La version **0.33.7** corrige deux régressions constatées après la v0.33.6 :

1. le contexte **Discovery · Kubernetes et cloud-native** était présent dans OpenAPI mais absent de la navigation frontend réelle ;
2. le job GitHub Actions **Transactional outbox and specialized workers regression** échouait parce qu'un test historique imposait encore `0054_async_outbox_workers.sql` et `0055_kubernetes_topology_inventory.sql` comme deux dernières migrations, alors que la migration additive `0056_kubernetes_gitops_drift.sql` est désormais légitime.

Aucune évolution métier, migration, route API, commande CLI ou modification de thème n'est introduite.

## Correctif frontend

- ajout du contexte de navigation `Kubernetes et cloud-native` sous le composant Discovery ;
- regroupement automatique de toutes les opérations dont l'identifiant commence par `kubernetes-` ;
- même contrat dans le frontend React et le runtime web packagé ;
- localisation anglaise `Kubernetes and cloud-native` ;
- suppression du classement des opérations Kubernetes dans le groupe générique `Autres` ;
- ajout d'un test de parité React/runtime couvrant l'intégralité des opérations Kubernetes ;
- conservation du budget EPIC-2004 grâce à un sélecteur déclaratif par préfixe au lieu d'une liste statique volumineuse.

## Correctif CI et politique de migrations

Le test Outbox vérifie désormais l'invariant réellement attendu :

```text
0054_async_outbox_workers.sql
    < 0055_kubernetes_topology_inventory.sql
    < 0056_kubernetes_gitops_drift.sql
```

Les autres assertions historiques qui considéraient `0055` comme dernière migration ont été alignées sur la chaîne additive courante. Aucune migration n'a été modifiée.

## Validation exécutée

### Python

- collecte globale : **1 377 tests** ;
- tests unitaires : **654/654 PASS** ;
- tests performance : **11/11 PASS** ;
- job CI `Transactional outbox and specialized workers regression` reproduit sans couverture : **63/63 PASS** ;
- régression frontend/runtime et budget EPIC-2004 : **24/24 PASS** ;
- documentation GA : **3/3 PASS** ;
- alignement installateur : **8/8 PASS** ;
- migrations multisite : **4/4 PASS** ;
- politique PostgreSQL : **1/1 PASS** ;
- migration GitOps Kubernetes : **2/2 PASS** ;
- contrats runtime Docker non-build ciblés : **6/6 PASS**.

### Qualité statique

- Ruff format : **418 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **120 modules conformes** ;
- `compileall` : **PASS**.

### Frontend

- tests Node : **79/79 PASS** ;
- contrat statique : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint JSX/a11y : **PASS** ;
- build Vite : **PASS** ;
- validation bundle : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- budget JavaScript initial EPIC-2004 : **PASS**.

### Sécurité et documentation

- `security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, sans finding bloquant ;
- OpenAPI produit : **PASS** ;
- OpenAPI CDC : **PASS** ;
- documentation GA 0.33.7 : **PASS** ;
- CDC : **840 exigences / 529 entités** ;
- roadmap v2.2 : **22 phases / 131 epics / 11 gates / 112 tests** ;
- alignement Enterprise : **PASS** ;
- support-readiness : **PASS**.

## Non-régression visuelle

Le fichier CSS runtime principal est strictement identique à celui de la v0.33.6 :

```text
fb7feabe378613ac41efb18db94b0d95a8faa916b6f782c9fd0ea2b0d8e9fcf4
```

Aucune couleur, surface, transparence, règle de hover ou comportement du thème n'a été modifié.

## Limites locales

- `pip-audit --strict -r requirements/runtime.txt` a été lancé mais n'a pas produit de résultat avant le timeout d'accès au registre Python ; il n'est donc pas déclaré comme validé localement.
- Docker n'est pas disponible dans l'environnement courant ; les smokes Docker Compose restent délégués à la CI.
- La suite globale monolithique `tests/architecture + tests/integration` n'a pas été intégralement rejouée. Les périmètres directement concernés ont été exécutés séparément afin d'éviter les blocages de processus déjà observés dans ce sandbox.
- Le seuil global de couverture **>= 98 %** reste bloquant dans GitHub Actions.

## Documentation de planification

Le **CDC 4.9.0** et la **roadmap v2.2** restent inchangés : cette livraison corrige des régressions d'intégration sans nouvelle exigence métier ou architecturale.
