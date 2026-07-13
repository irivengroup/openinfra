# OpenInfra v0.32.4 — rapport de validation

Date : 2026-07-13

## Objet

Cette livraison corrige l’échec de construction Docker de la version 0.32.3 : Hatchling exigeait `docs/ga`, `docs/release` et `docs/runbooks/GA_GO_NO_GO.md`, alors que le Dockerfile ne copiait que `docs/api` avant `pip install`.

## Correctifs

- copie de `docs/ga`, `docs/release` et `docs/runbooks` dans le contexte de l’image avant l’installation Python ;
- définition de build locale partagée par `migrate`, `auth-bootstrap`, `api`, `web` et `smoke` ;
- `pull_policy: build` afin de ne pas rechercher `openinfra/runtime` dans un registre externe ;
- test réel de construction d’un wheel depuis un contexte minimal reproduisant le Dockerfile ;
- test de correspondance entre les chemins `force-include` Hatchling et les ressources copiées ;
- test des cinq services runtime Compose.

## Compatibilité

- aucune migration PostgreSQL ;
- aucune modification métier, API ou CLI ;
- aucune dépendance runtime ajoutée ;
- aucune modification CSS ou du thème ;
- EPIC-1805 et la décision GATE-07 restent inchangés.

## Validations exécutées

- tests de non-régression ciblés : **39 réussis** ;
- construction d’un wheel depuis le contexte Docker minimal : PASS ;
- validation YAML Compose et build partagé : PASS ;
- Ruff format : **340 fichiers conformes** ;
- Ruff lint : PASS ;
- mypy strict : **106 modules conformes** ;
- Bandit : PASS ;
- OpenAPI et documentation GA : PASS ;
- packaging wheel/sdist : PASS ;
- installation du wheel, `pip check` et smoke installé : PASS ;
- collection complète disponible : **1 196 tests**.

La baseline complète 0.32.3 reste de 1 193 tests avec 98,07959163445337 % de couverture. Le correctif 0.32.4 ne modifie aucun module métier Python ; les tests de non-régression ajoutés ciblent précisément le défaut de build Docker.
