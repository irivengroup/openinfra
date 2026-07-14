# OpenInfra v0.32.9 — rapport de validation

Date : 2026-07-14

## Périmètre livré

La version 0.32.9 réalise **P17 / EPIC-1704 — PRA/PCA complets** sans nouvelle source de vérité ni migration PostgreSQL.

Le dispositif :

- réutilise les plans et exercices DR d’EPIC-1703 ;
- agrège cinq preuves : plan DR, exercice DR, sauvegarde/restauration, PITR et procédures ;
- mesure le RPO comme le pire cas entre lag de réplication et perte de données PITR ;
- mesure le RTO comme le pire cas entre l’exercice DR et la récupération PITR ;
- contrôle l’âge de sauvegarde, la restauration, l’intégrité, le chiffrement et la cohérence PITR ;
- exige dix étapes de procédure complètes ;
- hache chaque source en SHA-256 et protège le manifeste par un digest canonique ;
- fournit un workflow GitHub Actions manuel sur environnement protégé et runner dédié ;
- ne déclenche aucune bascule, promotion, restauration ou mutation d’infrastructure.

## Validations réussies

### Python et architecture

- collecte globale : **1 235 tests** ;
- suites unitaires et performance : **590/590 PASS** ;
- tests ciblés PRA/PCA : **12/12 PASS** ;
- régression transversale ciblée version, documentation, GA, runtime et frontend : **75/75 PASS** ;
- couverture du nouveau module `openinfra.quality.continuity_certification` : **258/258 instructions, 100 %** ;
- Ruff format : **354 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **108 modules conformes** ;
- `compileall` : **PASS** ;
- validateur PRA/PCA : **PASS** ;
- validateur documentation GA : **10 documents, 33 commandes CLI, 7 opérations API, version 0.32.9** ;
- validation observabilité/capacité : **PASS** ;
- alignement Enterprise : **PASS** ;
- validation des six profils installateur : **PASS** ;
- quality gate : tous les contrôles préalables ont passé ; arrêt final attendu uniquement sur l’absence de base de couverture globale complète dans le sandbox.

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
- Bandit sur `src/openinfra` : **PASS**, aucun résultat bloquant ;
- `pip-audit --strict -r requirements/security-audit.txt` : **NON EXÉCUTABLE dans le sandbox**, échec de résolution DNS vers PyPI ; le contrôle reste bloquant en CI.

### Packaging

- build sdist `openinfra-0.32.9.tar.gz` : **PASS** ;
- build wheel `openinfra-0.32.9-py3-none-any.whl` : **PASS** ;
- vérification du contenu des deux artefacts : **PASS** ;
- smoke du wheel installé : **PASS** ;
- version installée : **0.32.9** ;
- migrations embarquées : **54**, dernière migration `0054_async_outbox_workers.sql` ;
- contrat PRA/PCA présent dans le wheel installé : **PASS**.

## Limites d’exécution locales

- La suite `tests/architecture + tests/integration` monolithique a dépassé la fenêtre d’exécution du sandbox. Aucun échec n’a été observé avant le timeout, mais la suite complète n’est **pas déclarée comme intégralement validée** localement.
- La couverture globale du projet n’a pas été recalculée entièrement dans ce sandbox. Le seuil contractuel **≥ 98 %** reste bloquant dans GitHub Actions.
- Docker et Docker Compose ne sont pas installés dans l’environnement courant ; les smokes Compose et les validations runtime conteneurisées restent délégués à la CI.
- `pip-audit` n’a pas pu joindre PyPI à cause de la résolution DNS du sandbox ; il reste obligatoire et bloquant en CI.

## Compatibilité et impact

- aucune migration PostgreSQL ;
- aucune modification des 54 migrations existantes ;
- aucune rupture des contrats métier API, CLI ou OpenAPI ;
- aucune suppression de fonctionnalité ;
- aucune modification du thème ou de la charte graphique ;
- compatibilité ascendante conservée ;
- CDC et roadmap inchangés, EPIC-1704 étant déjà défini dans la roadmap 2.1.
