# OpenInfra v0.33.2 — Rapport de validation

## Identité de la livraison

- Version : `0.33.2`
- Objet : gestion CRUD unifiée et navigation opérateur consolidée
- Nature : amélioration structurelle UX/UI sans rupture des contrats métier
- CDC : `4.9.0`, inchangé
- Roadmap : `2.2.0`, inchangée
- Base fonctionnelle : OpenInfra `0.33.1`

## Objectif validé

La navigation web ne présente plus une succession de liens `Créer`, `Consulter`, `Lister`, `Modifier` et `Retirer` pour les agrégats métier disposant d'un CRUD complet et homogène. Ces opérations sont regroupées derrière une entrée unique `Gestion de …`, sans supprimer ni fusionner les endpoints backend, les commandes CLI, les permissions, les événements d'audit ou les contrats OpenAPI existants.

Le regroupement est piloté par les capacités réelles de la ressource, et non par une simple détection textuelle des verbes. Les opérations qui ne forment pas un cycle de vie homogène restent indépendantes.

## Ressources regroupées

### DCIM

- sites ;
- bâtiments ;
- salles ;
- châssis/racks ;
- zones.

### ITAM

- organisations ;
- filiales/subdivisions ;
- partenaires.

## Expérience opérateur validée

Chaque espace `Gestion de …` fournit :

- une liste tabulaire unique de la famille d'objets ;
- recherche textuelle et filtres multicritères ;
- remise à zéro des filtres ;
- tri de colonnes ;
- pagination bornée `25 / 50 / 100` ;
- option d'inclusion des objets retirés lorsque le backend la supporte ;
- bouton `+ Nouveau` ;
- consultation du détail depuis le nom de l'objet dans un dialogue accessible ;
- colonne `Actions` avec `Éditer` et `Supprimer` ;
- confirmation explicite avant suppression/retrait ;
- identification de l'opérateur pour l'opération destructive lorsque le contrat backend l'exige ;
- écrans dédiés de création et d'édition ;
- conservation des identifiants structurels immuables pendant l'édition ;
- retour automatique à la page de gestion et rechargement de la liste après création, édition ou suppression ;
- conservation de la sémantique de cycle de vie du backend, y compris le retrait logique lorsqu'il est imposé par le domaine.

Les catalogues DCIM hiérarchiques sont aplatis en lecture pour l'affichage tabulaire sans mutation de la source.

## Architecture et compatibilité

- nouveau registre partagé de ressources de gestion entre le portail React et le runtime web packagé ;
- registre chargé paresseusement avec les domaines DCIM/ITAM afin de ne pas alourdir le premier affichage ;
- endpoints CRUD existants conservés intégralement ;
- commandes CLI existantes conservées intégralement ;
- contrats OpenAPI existants conservés ;
- RBAC, audit et validations backend inchangés ;
- aucune migration PostgreSQL ;
- chaîne conservée à **55 migrations**, dernière `0055_kubernetes_topology_inventory.sql` ;
- aucune suppression ou renommage d'opération métier existante.

## Tests Python

- collecte globale : **1 317 tests** ;
- `tests/unit` + `tests/performance` : **635/635 PASS** ;
- lot d'intégration ciblé frontend/runtime/packaging : **57/57 PASS** ;
- contrats Python dédiés à la gestion CRUD : **4/4 PASS**, inclus dans le lot d'intégration ;
- test d'installation/rollback des six profils installateur : **1/1 PASS**, inclus dans le lot ciblé final.

Le lot d'intégration couvre notamment :

- synchronisation du registre React/runtime ;
- conservation des opérations CRUD brutes ;
- démarrage du runtime packagé ;
- modularisation et budgets de chargement ;
- accessibilité web ;
- environnement runtime/Docker contractuel ;
- documentation GA ;
- workflows GitHub Actions ;
- serveur web/BFF ;
- packaging et rollback installateur.

## Frontend

- tests Node : **68/68 PASS** ;
- tests dédiés au registre CRUD : **5/5 PASS**, inclus dans les 68 tests ;
- validation du contrat statique : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint JSX/accessibilité : **PASS** ;
- build Vite : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- budgets de chargement initial EPIC-2004 : **PASS** ;
- registre de gestion chargé à la demande avec DCIM/ITAM : **PASS**.

## Non-régression visuelle

La structure CSS a été enrichie pour les espaces de gestion, mais **la palette du thème n'a pas été modifiée**.

Comparaison avec la v0.33.1 :

- couleurs hexadécimales distinctes avant : **52** ;
- couleurs hexadécimales distinctes après : **52** ;
- nouvelles couleurs hexadécimales : **aucune** ;
- couleurs hexadécimales supprimées : **aucune** ;
- styles de gestion construits à partir des tokens OpenInfra existants ;
- règle de non-régression du fond du composant racine actif au survol toujours couverte par les tests frontend.

## Qualité statique

- `ruff format --check` : **390 fichiers conformes** ;
- `ruff check` : **PASS** ;
- `mypy` strict : **115 modules conformes** ;
- `compileall` sur `src`, `tests` et `scripts` : **PASS**.

## Documentation et contrats

- OpenAPI produit `docs/api/openapi.yaml` : **PASS** ;
- OpenAPI CDC 4.9.0 : **PASS** ;
- documentation GA `0.33.2` : **PASS** ;
- CDC : **840 exigences**, **529 entités**, traçabilité présente ;
- roadmap v2.2 : **22 phases**, **131 epics**, **11 gates**, **112 tests** ;
- alignement Enterprise : **PASS** ;
- frontend contract validator : **PASS**.

## Sécurité

- `security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- `pip-audit --strict` : **non terminé**, la résolution DNS de `pypi.org` échoue dans le sandbox.

## Packaging

- wheel `openinfra-0.33.2-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.2.tar.gz` : **PASS** ;
- `scripts/verify_artifact.py dist/*` : **PASS** ;
- nouveau registre `openinfra-management-resources.js` exigé par le vérificateur de packaging : **PASS** ;
- smoke du wheel installé hors de l'arbre source : **PASS** ;
- version installée : `0.33.2` ;
- assets runtime installés : **18** ;
- routes Kubernetes installées : **8** ;
- migrations installées : **55**, dernière `0055_kubernetes_topology_inventory.sql`.

## Limites de validation locale

La suite globale monolithique `tests/architecture + tests/integration` n'a pas été déclarée intégralement validée dans ce sandbox. Le périmètre directement impacté a été couvert par un lot ciblé de 57 tests d'intégration, en complément des 635 tests unitaires/performance et des 68 tests frontend.

La couverture globale complète n'a pas été recalculée dans cette session. Le seuil contractuel **≥ 98 %** reste bloquant dans GitHub Actions.

Docker n'est pas installé dans le sandbox courant ; les smokes Docker Compose restent délégués à la CI.

## Verdict local

**PASS pour la gestion CRUD unifiée v0.33.2 et tous les gates exécutables localement, avec les limites explicites ci-dessus.**
