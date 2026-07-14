# OpenInfra v0.32.10 — rapport de validation

Date : 2026-07-14

## Périmètre livré

La version 0.32.10 réalise **P17 / EPIC-1705 — Observabilité multisite** sans nouvelle source de vérité, sans migration PostgreSQL et sans modification du thème.

Le dispositif :

- calcule le retard des collecteurs Discovery par région et par site à partir des heartbeats déjà persistés ;
- déduplique un même collecteur lorsqu'il dessert plusieurs VRF d'un même site ;
- exporte des métriques Prometheus bornées par `region`, `site` et état, sans identifiant de tenant, utilisateur ou objet métier dans les labels ;
- borne la collecte à 10 000 routes régionales et protège la pagination contre les boucles de curseur ;
- fédère les endpoints `/metrics` des sites via HTTPS et file service discovery ;
- fournit un dashboard Grafana multisite couvrant API, agents, réplication PostgreSQL et files de jobs ;
- ajoute six alertes multisite avec seuils explicites ;
- fournit un profil machine-readable, un validateur strict et un runbook opérateur ;
- intègre la validation au pipeline CI et au quality gate existants.

## Validations réussies

### Python et architecture

- collecte globale : **1 244 tests** ;
- suites unitaires et performance : **593/593 PASS** ;
- tests ciblés observabilité multisite, workflow et régression : **18/18 PASS** lors du dernier passage ciblé ;
- Ruff format : **357 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **109 modules conformes** ;
- `compileall` : **PASS** ;
- validateur observabilité global : **PASS** ;
- validateur observabilité multisite : **PASS** ;
- validateur PRA/PCA : **PASS** ;
- validateur frontend : **PASS** ;
- validateur documentation GA : **10 documents, 33 commandes CLI, 7 opérations API, version 0.32.10** ;
- alignement Enterprise : **PASS** ;
- validation des six profils installateur : **PASS** ;
- support-readiness EPIC-1806 : **PASS** avec preuve signée par clé éphémère de validation locale.

### Frontend

- tests Node.js : **63/63 PASS** ;
- contrat statique : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint JSX accessibilité : **PASS** ;
- build Vite : **PASS** ;
- budgets frontend EPIC-2004 : **PASS** ;
- `npm audit` : **0 vulnérabilité** ;
- aucune modification fonctionnelle ou visuelle du thème dans cette version.

### Sécurité

- security gate : **PASS** ;
- Bandit : **PASS**, aucun résultat bloquant ;
- `pip-audit --strict -r requirements/security-audit.txt` : **NON EXÉCUTABLE dans le sandbox**, échec de résolution DNS vers PyPI ; le contrôle reste obligatoire et bloquant en CI.

### Packaging

- build sdist `openinfra-0.32.10.tar.gz` : **PASS** ;
- build wheel `openinfra-0.32.10-py3-none-any.whl` : **PASS** ;
- vérification du contenu des deux artefacts : **PASS** ;
- runtime `multisite_observability` présent dans le wheel : **PASS** ;
- profil, runbook, dashboard Grafana, cible file-SD et validateur multisite présents dans le sdist : **PASS** ;
- smoke du wheel installé : **PASS** ;
- version installée : **0.32.10** ;
- migrations embarquées : **54**, dernière migration `0054_async_outbox_workers.sql` ;
- contrat multisite installé, dont la borne de 10 000 routes : **PASS**.

## Limites d’exécution locales

- La suite `tests/architecture + tests/integration` complète a dépassé la fenêtre d'exécution du sandbox. Aucun échec n'a été observé avant le timeout, mais la suite complète n'est **pas déclarée comme intégralement validée** localement.
- La couverture globale du projet n'a pas été recalculée entièrement dans ce sandbox. Le seuil contractuel **≥ 98 %** reste bloquant dans GitHub Actions.
- Docker et Docker Compose ne sont pas installés dans l'environnement courant ; les smokes Compose et les validations runtime conteneurisées restent délégués à la CI.
- `pip-audit` n'a pas pu joindre PyPI à cause de la résolution DNS du sandbox ; il reste obligatoire et bloquant en CI.

## Compatibilité et impact

- aucune migration PostgreSQL ;
- aucune modification des 54 migrations existantes ;
- aucune rupture des contrats métier API, CLI ou OpenAPI ;
- aucune suppression de fonctionnalité ;
- aucune modification du thème ou de la charte graphique ;
- compatibilité ascendante conservée ;
- CDC et roadmap inchangés, EPIC-1705 étant déjà défini dans la roadmap 2.1.
