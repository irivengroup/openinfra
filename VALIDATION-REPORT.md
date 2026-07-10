# OpenInfra v0.29.85 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.85`  
Périmètre : `Nomenclature locale des étages DCIM et internationalisation web FR/EN`

## Résultat global

La livraison abandonne la concaténation des codes site/bâtiment dans les étages, introduit une nomenclature locale stable et ajoute un moteur d’internationalisation commun aux deux portails web. Les identifiants métier et valeurs API restent indépendants de la langue.

- Tests Python collectés : **615** dans **83 fichiers**.
- Suite complète : **PASS** par lots, sans échec.
- Tests unitaires : **227 PASS**.
- Tests d’intégration : **385 PASS**.
- Tests d’architecture : **3 PASS**.
- Couverture globale exacte : **98,013559 %** — `20 674 / 21 093` instructions couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **8 PASS**.
- Lint frontend : **PASS**.
- Build frontend Vite : **PASS**.

La suite instrumentée a été exécutée par lots avec accumulation dans un fichier de couverture unique. Certains groupes CLI/DCIM dépassaient le timeout lorsqu’ils contenaient trop de fichiers ; ils ont été subdivisés, sans modifier les tests ni la mesure consolidée.

## Nomenclature DCIM des étages

- Code local au bâtiment, triable et indépendant des codes parents :
  - sous-sol 1 : `L-01` ;
  - rez-de-chaussée : `L00` ;
  - étage 1 : `L01` ;
  - étage 2 : `L02` ;
  - niveaux supérieurs à 99 : largeur adaptée, par exemple `L100`.
- Le site et le bâtiment restent portés par la hiérarchie du modèle et ne sont pas répétés dans le code d’étage.
- Les noms générés stockés restent neutres et déterministes : `Basement n`, `Ground floor`, `Level n`.
- Leur affichage est localisé dans l’interface web : `Sous-sol n`, `Rez-de-chaussée`, `Étage n` en français.
- Les alias historiques `<site>_<bâtiment>_ETG<n>`, `F<n>` et `ETG<n>` restent acceptés en lecture pour préserver la compatibilité.
- Les nouveaux enregistrements utilisent exclusivement la nomenclature canonique `L…`.
- Les noms personnalisés existants sont préservés.
- Les collisions de niveau et codes hors bornes sont refusés.
- `define-room` repose sur l’indice de niveau ; les anciens hints de code/nom restent tolérés comme entrées dépréciées.

## Migration des données

- Migration JSON automatique : **PASS**.
- Migration PostgreSQL : `0040_dcim_floor_nomenclature.sql`.
- Mise à jour transactionnelle des références dans : étages, salles, zones de salle, racks et équipements.
- Garde contre les collisions avant renommage : **PASS**.
- Contrainte canonique sur les nouveaux codes : **PASS**.
- Nombre total de migrations PostgreSQL ordonnées : **40**.
- Dernière migration packagée et chargeable : `0040_dcim_floor_nomenclature.sql`.

## Internationalisation web FR/EN

- Langues supportées : **anglais** et **français** uniquement.
- Détection initiale : `navigator.languages`, puis `navigator.language`.
- Réduction des locales régionales : `fr-FR` → `fr`, `en-GB` → `en`.
- Toute langue non supportée utilise l’anglais comme fallback strict.
- Sélecteur `EN/FR` disponible dans le header.
- Choix utilisateur persisté dans `localStorage` sous `openinfra.language`.
- Moteur i18n partagé et byte-identique entre le frontend React et le portail packagé Python.
- Couverture des composants, menus, opérations, formulaires, validations, états, pays, continents, taxonomie des ressources et étages.
- Les clés, codes, identifiants et valeurs API ne sont jamais traduits.
- `Intl.DisplayNames` est utilisé pour les noms de pays lorsque disponible.
- La commutation à chaud ne laisse pas de fragments mixtes français/anglais dans les rendus dynamiques couverts.

## Résolution des assets web

Le build Vite génère `web/dist`, mais ce répertoire ne contient pas les assets contractuels du runtime packagé Python. La résolution statique applique désormais l’ordre suivant :

1. racine explicitement fournie par l’opérateur ;
2. runtime statique packagé dans les sources ;
3. runtime statique installé dans le wheel ;
4. bundle React `web/dist`.

Un build React incomplet ne peut donc plus masquer le portail packagé. Le comportement est couvert par un test de non-régression exécuté avec `web/dist` présent.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker` : **PASS**, **148 fichiers**.
- `ruff check src tests scripts docker` : **PASS**.
- `mypy src/openinfra` : **PASS**, aucune erreur sur **56 fichiers source**.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python -m compileall -q src/openinfra scripts tests` : **PASS**.
- Séparation des dépendances runtime et développement : **PASS**.
- Aucun secret en clair ajouté : **PASS**.

## CDC, roadmap, installateurs et runtime

Cette évolution modifie des décisions existantes ; le CDC et la roadmap ont donc été réalignés.

- CDC v4.8.1 : **PASS** — **824 exigences**, **529 entités**, **623 tests contractuels**.
- Roadmap v2 : **PASS** — **19 phases**, **115 epics**, **8 gates**, **92 tests**.
- Exigence nomenclature : `REQ-00820`.
- Exigence i18n web : `REQ-00824`.
- Epic i18n : `EPIC-0807`.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Alignement Enterprise : **PASS**.
- Validation frontend statique : **PASS**.
- Smoke runtime natif et rendu de trois unités systemd : **PASS**.

## Frontend

- Installation contrôlée des dépendances npm : **PASS**.
- `npm --prefix web test` : **8 tests PASS**.
- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run build` : **PASS** avec Vite `5.4.21`.
- Validation de l’identité du moteur i18n React/runtime packagé : **PASS**.
- `web/node_modules`, `web/dist` et le lockfile généré temporairement sont exclus de l’archive source.

## Packaging

- `python -m build` : **PASS**.
- Wheel : `openinfra-0.29.85-py3-none-any.whl`.
- Source distribution : `openinfra-0.29.85.tar.gz`.
- `python scripts/verify_artifact.py dist/openinfra-0.29.85-py3-none-any.whl` : **PASS**.
- Présence des **40 migrations** dans le wheel : **PASS**.
- Présence du moteur i18n packagé : **PASS**.
- Installation normale du wheel dans un environnement isolé : **PASS**.
- `openinfra version` depuis le wheel : `0.29.85`.
- `openinfra --help` depuis le wheel : **PASS**.
- Résolution et chargement des 40 migrations depuis le wheel : **PASS**.
- Inspection du sdist : **494 entrées**, **0 entrée interdite**.
- Absence de `node_modules`, `web/dist`, caches Python et artefacts temporaires dans le sdist : **PASS**.

## Contrôles limités par l’environnement

- `pip-audit` a été lancé en mode strict, mais n’a pas pu interroger `pypi.org` en raison de l’absence de résolution DNS sortante. Ce contrôle est **non concluant**, et non déclaré comme réussi.
- Aucun exécutable Docker, Podman ou PostgreSQL (`psql`) n’est disponible dans le runner. Les smoke tests nécessitant un daemon de conteneurs ou une instance PostgreSQL réelle n’ont donc pas été exécutés localement.
- Les migrations PostgreSQL ont néanmoins été validées structurellement, packagées, ordonnées et chargées depuis le wheel.

## Commandes de reproduction

```bash
ruff format --check src tests scripts docker
ruff check src tests scripts docker
mypy src/openinfra
bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python scripts/quality_gate.py
python -m compileall -q src/openinfra scripts tests

pytest tests/unit -o addopts=""
pytest tests/integration -o addopts=""
pytest tests/architecture -o addopts=""
coverage report --fail-under=98

npm --prefix web test
npm --prefix web run lint
npm --prefix web run build
python scripts/validate_frontend.py --project-root .

python -m build
python scripts/verify_artifact.py dist/openinfra-0.29.85-py3-none-any.whl
```

Dans le runner utilisé pour cette livraison, les tests d’intégration et la couverture ont été répartis en lots plus petits pour respecter la durée maximale d’une commande tout en conservant une couverture cumulée unique.
