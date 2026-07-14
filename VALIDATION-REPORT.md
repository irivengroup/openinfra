# OpenInfra v0.33.0 — Rapport de validation

## Périmètre

- Version : `0.33.0`
- Phase : `P21 — Kubernetes & Cloud-native`
- Epic : `EPIC-2101 — Inventaire Kubernetes et topologie physique`
- Release roadmap : `REL-11`
- Roadmap : `2.2.0`
- CDC : `4.9.0` inchangé ; les exigences `REQ-00469` et `REQ-00470` existaient déjà.

## Fonctionnalités validées

- instantanés Kubernetes immuables, dédupliqués par empreinte canonique SHA-256 et limités à 50 000 ressources ;
- inventaire `namespace`, `node`, `workload`, `pod`, `service`, `ingress`, `network-policy` et `volume` ;
- intégrité référentielle, relations typées et isolation inter-namespace ;
- graphe `cluster → namespace → workload/pod/service → node → VM → hyperviseur → serveur → rack → salle → site` ;
- persistance JSON et PostgreSQL avec pagination par curseur et migration `0055_kubernetes_topology_inventory.sql` ;
- outbox PostgreSQL cohérente avec la clé primaire partitionnée `(tenant_id, id)` ;
- permissions `kubernetes.read` et `kubernetes.write`, rôles `kubernetes:reader` et `kubernetes:operator`, audit et rejet des clés sensibles ;
- parité HTTP, CLI, OpenAPI et portails React/runtime ;
- catalogue runtime Discovery préservé : 28 opérations historiques + 4 opérations Kubernetes, soit 278 opérations runtime globales ;
- ouverture de la roadmap `2.2.0` avec P21, REL-11, M13, GATE-10 et EPIC-2101 à EPIC-2106.

## Tests exécutés

- collecte Python : **1 286 tests** ;
- suite `tests/unit + tests/performance` : **615/615 PASS** ;
- gate CI P21 exact : **19/19 PASS** ;
- tests transverses ciblés installateurs/workflows/migrations/runtime/documentation/support : **69/69 PASS** ;
- tests packaging et sécurité release : **40/40 PASS** ;
- frontend Node : **63/63 PASS** ;
- couverture ciblée du nouveau domaine et service Kubernetes : **403/403 instructions, 100 %**.

La suite complète `tests/architecture + tests/integration` a été tentée en isolation. Elle a identifié une attente historique obsolète qui imposait encore `0054` comme dernière migration ; ce test a été corrigé pour vérifier l'ordre `0054 → 0055` et repasse avec le test de migration P21. La campagne complète n'a toutefois pas terminé dans la fenêtre d'exécution du sandbox et n'est donc pas déclarée intégralement validée localement.

Le seuil de couverture globale **≥ 98 %** reste bloquant dans GitHub Actions. La couverture globale complète n'a pas été recalculée localement dans ce sandbox.

## Qualité statique

- Ruff format : **381 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **114 modules conformes** ;
- `compileall` : **PASS** ;
- OpenAPI opérationnel et OpenAPI CDC : **PASS** ;
- validateur P21 : **PASS** ;
- roadmap 2.2 : **22 phases, 131 epics, 11 gates, 112 tests — PASS** ;
- documentation CDC : **840 exigences, 529 entités, traçabilité présente — PASS** ;
- alignement Enterprise CDC 4.9.0 / roadmap 2.2 : **PASS** ;
- six profils installateur : **PASS** ;
- documentation GA et support-readiness : **PASS** ;
- observabilité, observabilité multisite, PRA/PCA, chaos multisite et GATE-09 : **PASS**.

## Frontend et accessibilité

- tests frontend : **63/63 PASS** ;
- contrat statique frontend : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint JSX : **PASS** ;
- build Vite et budgets de bundle : **PASS** ;
- `npm audit` : **0 vulnérabilité** ;
- aucune modification du thème : `openinfra-web.css` est bit-pour-bit identique à la v0.32.12 ;
- SHA-256 CSS : `334fc797cea05d9c2a0f670d8a098fbc8caa2c55a7cd228f3c296338f52c0555`.

## Sécurité

- `scripts/security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, aucun finding bloquant ;
- `pip-audit --strict` : **NON TERMINÉ**, résolution DNS de `pypi.org` indisponible depuis le sandbox ;
- aucun secret en clair ajouté ;
- les attributs Kubernetes contenant des clés sensibles sont rejetés avant persistance.

## Packaging

Validation intermédiaire avant rapport final :

- wheel `openinfra-0.33.0-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.0.tar.gz` : **PASS** ;
- vérification de contenu des artefacts : **PASS** ;
- smoke du wheel installé hors de l'arbre source : **PASS** ;
- version installée : `0.33.0` ;
- routes Kubernetes installées : **6** ;
- migrations installées : **55** ;
- dernière migration : `0055_kubernetes_topology_inventory.sql`.

Les artefacts sont reconstruits une dernière fois après inclusion de ce rapport, puis revérifiés avant création de l'archive de livraison.

## Limites de l'environnement

- Docker et Docker Compose ne sont pas installés dans le sandbox : les smokes Compose restent bloquants dans la CI ;
- `pip-audit` ne peut pas joindre PyPI depuis le sandbox ;
- la suite d'intégration complète et la couverture globale complète restent exécutées par GitHub Actions avec le seuil contractuel de couverture **≥ 98 %**.
