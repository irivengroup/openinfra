# OpenInfra v0.33.1 — Rapport de validation

## Identité de la livraison

- Version : `0.33.1`
- Phase : `P21`
- Epic : `EPIC-2102`
- Release roadmap : `REL-11`
- Objet : expositions et dépendances réseau cloud-native
- CDC : `4.9.0`, inchangé
- Roadmap : `2.2.0`, inchangée ; EPIC-2102 y était déjà planifié

## Fonctionnalités validées

- nouveaux types de ressources Kubernetes : `load-balancer`, `dns-record`, `mesh-route` ;
- métadonnées d’exposition normalisées pour services et ingress ;
- validation stricte des DNS, IP, ports, protocoles, scopes, types de service, TLS et références RSOT ;
- import immuable et idempotent dans le stockage Kubernetes existant ;
- rapport déterministe `KubernetesExposureReport` ;
- corrélation avec les déclarations de flux `ANY`, `CIDR` et `OBJECT` ;
- corrélation avec les objets et relations de dépendance RSOT ;
- graphe exposition → ressource Kubernetes → workload/pod → dépendances réseau ;
- identification des expositions externes non gouvernées ;
- bornes de protection : 10 000 déclarations de flux, 10 000 relations RSOT, 2 048 objets RSOT et 128 clés de corrélation directes ;
- détection des curseurs cycliques ;
- état `correlation_truncated` lorsqu'une borne de protection est atteinte ;
- parité API, CLI, OpenAPI, portail React et runtime packagé ;
- intégration CI, quality gate, vérification des artefacts et smoke du wheel installé.

## Compatibilité et impact

- aucune nouvelle migration PostgreSQL ;
- chaîne conservée à 55 migrations, dernière `0055_kubernetes_topology_inventory.sql` ;
- aucune nouvelle source de vérité ;
- aucune mutation automatique de firewall, DNS, load balancer ou service mesh ;
- permissions existantes `kubernetes.read` et `kubernetes.write` réutilisées ;
- aucune suppression ou rupture des routes Kubernetes EPIC-2101 ;
- catalogue runtime porté à 280 opérations uniques sans suppression d'opération historique ;
- aucune modification du thème ou de la charte graphique.

## Tests Python

- collecte : **1 313 tests** ;
- `tests/unit` + `tests/performance` : **635/635 PASS** ;
- tests EPIC-2102 dédiés : **27/27 PASS** ;
- tests transverses ciblés Kubernetes, OpenAPI, workflows, documentation, Docker runtime contract, scale-out et frontend modularisé : **59/59 PASS** ;
- couverture ciblée domaine + service Kubernetes concernés : **99 %** ;
- nouveau module `kubernetes_exposure.py` : **98 %** dans la campagne ciblée.

## Qualité statique

- `ruff format --check` : **381 fichiers conformes** ;
- `ruff check` : **PASS** ;
- `mypy` strict : **115 modules conformes** ;
- `compileall` sur `src`, `tests`, `scripts`, `docker`, `installers` : **PASS**.

## Validation P21 et documentation

- `validate_kubernetes_topology.py --enforce` : **PASS** ;
- `validate_kubernetes_exposure.py --enforce` : **PASS** ;
- roadmap v2.2 : **PASS**, 22 phases, 131 epics, 11 gates, 112 tests ;
- OpenAPI YAML : **PASS** ;
- documentation GA 0.33.1 : **PASS** ;
- frontend contract validator : **PASS**.

## Frontend

- tests Node : **63/63 PASS** ;
- validation des assets statiques : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint JSX/accessibilité : **PASS** ;
- build Vite + validation du bundle : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- catalogue runtime : **280 opérations uniques** ;
- SHA-256 du CSS principal : `334fc797cea05d9c2a0f670d8a098fbc8caa2c55a7cd228f3c296338f52c0555`, identique à la v0.33.0.

## Sécurité

- `security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS** ;
- `pip-audit --strict` : **non terminé** ; la résolution DNS de `pypi.org` échoue dans le sandbox.

## Packaging

- wheel `openinfra-0.33.1-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.1.tar.gz` : **PASS** ;
- `scripts/verify_artifact.py dist/*` : **PASS** ;
- smoke du wheel installé dans un environnement virtuel distinct de l'arbre source : **PASS** ;
- version installée : `0.33.1` ;
- routes Kubernetes installées : **8** ;
- migrations installées : **55**, dernière `0055_kubernetes_topology_inventory.sql`.

## Limites de validation locale

La suite monolithique `tests/architecture + tests/integration` a dépassé la fenêtre d'exécution du sandbox après plusieurs tests réussis, sans échec affiché avant l'interruption. Une tentative d'isolation de l'ensemble des 148 fichiers architecture/intégration a également dépassé la fenêtre globale avant de produire un agrégat final. La suite complète n'est donc pas déclarée intégralement validée localement ; elle reste bloquante dans GitHub Actions.

La couverture globale complète n'a pas été recalculée dans cette session. Le seuil contractuel **≥ 98 %** reste bloquant dans la CI.

Docker n'est pas installé dans le sandbox courant ; les smokes Docker Compose restent délégués à la CI.

## Verdict local

**PASS pour le périmètre EPIC-2102 et les gates exécutables localement, avec les limites explicites ci-dessus.**
