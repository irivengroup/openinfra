# OpenInfra v0.33.3 — Rapport de validation

## Identité de la livraison

- Version : `0.33.3`
- Phase : `P21`
- Epic : `EPIC-2103`
- Release : `REL-11`
- Objet : corrélation images, SBOM, certificats et secrets référencés pour les workloads Kubernetes
- CDC : `4.9.0`, inchangé
- Roadmap : `2.2.0`, inchangée
- Base fonctionnelle : OpenInfra `0.33.2`

## Objectif validé

OpenInfra contextualise désormais les ressources Kubernetes avec les référentiels de sécurité existants sans créer de nouvelle source de vérité et sans ingérer de secret en clair.

La projection est strictement en lecture :

- `workload/pod → image OCI → SBOM → findings de vulnérabilité` ;
- `ressource Kubernetes → empreinte de certificat → inventaire PKI` ;
- `ressource Kubernetes → référence de secret approuvée → fournisseur + représentation masquée + empreinte SHA-256`.

Aucune remédiation, rotation de secret, modification de certificat, réécriture d'image ou mutation Kubernetes n'est exécutée par le moteur de corrélation.

## Modèle de sécurité

### Images OCI

- référence OCI bornée à 1 024 caractères ;
- rejet explicite des URL de transport contenant `://` ;
- digest SHA-256 optionnel et normalisé ;
- détection des conflits entre digest embarqué et digest explicite ;
- maximum de 32 documents SBOM explicitement liés par image ;
- maximum de 64 images par workload ou pod.

### Certificats

- références limitées aux empreintes SHA-256 ;
- résolution dans l'inventaire PKI existant ;
- exposition du cycle de vie, de l'état de santé, des jours restants, du propriétaire et de l'environnement ;
- signalement explicite des certificats inconnus et non sains.

### Secrets référencés

Schémas autorisés :

- `vault://` ;
- `sops://` ;
- `kms://` ;
- `kubernetes-secret://namespace/name` ;
- `external-secret://` ;
- `aws-secrets-manager://` ;
- `azure-key-vault://` ;
- `gcp-secret-manager://`.

Pour les fournisseurs externes, la référence brute n'est jamais persistée : seule une représentation `provider://***` et le SHA-256 de la référence d'origine sont conservés. La référence native `kubernetes-secret://namespace/name` reste visible car elle identifie un objet Kubernetes et ne contient pas son contenu.

Le security gate a été durci afin de ne plus confondre les continuations de schémas URI `*-secret://` avec des affectations de credentials, tout en conservant le contrôle des véritables affectations de secrets.

## Corrélation et bornes

- maximum de **2 000 documents SBOM** parcourus ;
- maximum de **512 références directes de documents SBOM** ;
- maximum de **10 000 findings** ;
- pagination bornée ;
- détection des curseurs cycliques ;
- `correlation_truncated=true` uniquement lorsqu'une page ou une donnée supplémentaire existe réellement au-delà de la borne ;
- rapport et fingerprint déterministes.

Les snapshots Kubernetes historiques sans références de sécurité conservent exactement leur payload canonique : les nouveaux champs sont omis lorsqu'ils sont vides. Le fingerprint de non-régression v0.33.0–v0.33.2 reste inchangé.

## Interfaces

### API

Deux routes de lecture supplémentaires :

- `GET /api/v1/kubernetes/topologies/security` ;
- `GET /api/v1/kubernetes/topologies/latest-security`.

Le total installé passe à **10 routes Kubernetes**.

### CLI

- `openinfra kubernetes security` ;
- `openinfra kubernetes latest-security`.

### UI / OpenAPI

- deux opérations Discovery supplémentaires ;
- catalogue runtime porté à **282 opérations uniques** ;
- parité React/runtime/search-index ;
- contexte Swagger/ReDoc `Discovery · Kubernetes et cloud-native` conservé.

## Compatibilité et données

- aucune nouvelle migration PostgreSQL ;
- chaîne conservée à **55 migrations** ;
- dernière migration : `0055_kubernetes_topology_inventory.sql` ;
- persistance JSON et PostgreSQL existantes réutilisées ;
- endpoints et commandes EPIC-2101/2102 conservés ;
- compatibilité des fingerprints historiques vérifiée ;
- aucune rupture des contrats API/CLI existants.

## Tests Python

- collecte globale : **1 337 tests** ;
- `tests/unit` + `tests/performance` : **645/645 PASS** ;
- régression P21 Kubernetes inventaire/exposition/sécurité : **61/61 PASS** ;
- lot d'intégration transverse ciblé : **73/73 PASS** ;
- tests EPIC-2103 dédiés : **19 collectés**, tous couverts par les lots ci-dessus ;
- tests du security gate : **13/13 PASS**.

Le lot transverse couvre notamment :

- services, HTTP, CLI et UI Kubernetes ;
- persistance PostgreSQL Kubernetes ;
- migration 0055 ;
- workflows GitHub Actions ;
- security gate ;
- documentation GA ;
- modularisation frontend ;
- environnement runtime Docker contractuel ;
- GATE-09 scale-out.

## Couverture ciblée

- `src/openinfra/domain/kubernetes_security.py` : **226/226 instructions, 100 %**.

La couverture globale complète du dépôt n'a pas été recalculée dans ce sandbox. Le seuil contractuel **≥ 98 %** reste bloquant dans GitHub Actions.

## Qualité statique

- `ruff format --check src tests scripts docker installers` : **398 fichiers conformes** ;
- `ruff check src tests scripts docker installers` : **PASS** ;
- `mypy src/openinfra` strict : **116 modules conformes** ;
- `compileall` : **PASS**.

## Documentation et contrats

- validateur EPIC-2101 : **PASS** ;
- validateur EPIC-2102 : **PASS** ;
- validateur EPIC-2103 : **PASS** ;
- OpenAPI produit et OpenAPI CDC : **PASS** ;
- documentation GA `0.33.3` : **PASS** ;
- roadmap v2.2 : **PASS — 22 phases, 131 epics, 11 gates, 112 tests** ;
- alignement Enterprise : **PASS** ;
- frontend contract validator : **PASS**.

## Frontend

- tests Node : **68/68 PASS** ;
- ESLint / contrat statique : **PASS** ;
- build Vite : **PASS** ;
- validation du bundle : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

## Sécurité

- `security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, sans finding bloquant ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- `pip-audit --strict` : **non terminé**, la résolution DNS de `pypi.org` échoue dans le sandbox.

## Packaging

- wheel `openinfra-0.33.3-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.3.tar.gz` : **PASS** ;
- `scripts/verify_artifact.py dist/*` : **PASS** ;
- smoke du wheel réellement installé hors de l'arbre source : **PASS** ;
- version installée : `0.33.3` ;
- routes Kubernetes installées : **10** ;
- assets runtime installés : **18** ;
- migrations installées : **55**, dernière `0055_kubernetes_topology_inventory.sql`.

Le premier venv de smoke avait été créé sans dépendances runtime et a échoué sur `uvicorn` absent. Le smoke a ensuite été exécuté correctement après installation de `requirements/runtime.txt`, avec le wheel installé hors de l'arbre source.

## Non-régression visuelle

Aucune feuille de style n'a été modifiée par EPIC-2103.

Le CSS runtime principal est bit-pour-bit identique à celui de la v0.33.2 :

`0ef8f1665af70a0d2ac2b07a9de30ec33b7851e00b1731d2c709fbf9a801220e`

La charte graphique et les comportements de navigation précédemment approuvés restent inchangés.

## Limites de validation locale

Une campagne visant les **154 fichiers architecture/intégration** en processus isolés et concurrence bornée a été lancée. Elle a dépassé la fenêtre du sandbox après plusieurs fichiers réussis et sans échec affiché avant l'interruption ; elle n'est donc pas déclarée intégralement validée localement.

Le périmètre directement impacté et les contrats transverses critiques sont couverts par les **73 tests d'intégration ciblés**, complétés par les **645 tests unitaires/performance**, les **61 tests P21** et les **68 tests frontend**.

Docker n'est pas installé dans le sandbox courant ; les smokes Docker Compose restent délégués à la CI.

## Verdict local

**PASS pour OpenInfra v0.33.3 / P21 / EPIC-2103 et tous les gates exécutables localement, avec les limites explicites ci-dessus.**
