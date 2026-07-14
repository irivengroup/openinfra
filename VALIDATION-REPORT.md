# OpenInfra v0.32.8 — rapport de validation

Date : 2026-07-14

## Objet

Cette livraison corrige exclusivement la régression de cascade CSS introduite par la couche de profondeur visuelle 0.32.7 sur le composant racine actif de la sidebar.

Le comportement attendu est désormais verrouillé :

- le fond du composant racine actif reste strictement identique au repos, au survol et au focus ;
- la couche de hover transparente ne s'applique qu'aux composants racine inactifs via `:not(.active)` ;
- au survol/focus d'un composant racine actif, seuls le texte, l'icône et le chevron passent au bleu turquoise du thème par héritage de `currentColor` ;
- aucune autre couleur, surface, transparence, animation ou règle responsive n'est modifiée.

## Impact et compatibilité

- aucune modification de la palette approuvée ;
- aucune modification du schéma PostgreSQL ni nouvelle migration ;
- aucune rupture d'API métier ou de CLI publique ;
- aucune suppression de fonctionnalité ;
- aucune nouvelle dépendance runtime ;
- accessibilité et responsive conservés ;
- compatibilité ascendante avec la v0.32.7.

## Fichiers principaux modifiés

- `web/src/openinfra-theme.css` ;
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css` ;
- `tests/integration/test_responsive_navigation_contract.py` ;
- `web/tests/responsive-navigation.test.mjs` ;
- métadonnées et contrats de version 0.32.8 ;
- `README.md` ;
- `CHANGELOG.md` ;
- `VALIDATION-REPORT.md`.

## Validations exécutées

### Régression visuelle et frontend

- test Python du contrat responsive/sidebar : **7 réussis** ;
- tests Python ciblés frontend/runtime/documentation/version : **62 réussis** ;
- tests frontend Node : **63 réussis** ;
- synchronisation exacte du CSS React/runtime : **PASS** ;
- validation des assets statiques : **PASS** ;
- validation accessibilité WCAG 2.2 AA : **PASS** ;
- ESLint JSX/accessibilité : **PASS** ;
- build Vite production et validation du bundle : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

### Python, qualité et sécurité

- suites unitaires et performance : **581 tests réussis** ;
- Ruff format sur le périmètre CI (`src tests scripts docker installers`) : **348 fichiers conformes** ;
- Ruff lint sur le périmètre CI : **PASS** ;
- mypy strict : **107 modules conformes** ;
- `compileall` : **PASS** ;
- validation OpenAPI des deux spécifications : **PASS** ;
- validation documentation GA : **10 documents, 33 commandes CLI, 7 opérations API, version 0.32.8** ;
- support-readiness EPIC-1806 : **PASS** ;
- validation frontend Python : **PASS** ;
- security gate : **PASS** ;
- Bandit `src/openinfra` : **PASS, aucun résultat bloquant**.

### Packaging

- build sdist `openinfra-0.32.8.tar.gz` : **PASS** ;
- build wheel `openinfra-0.32.8-py3-none-any.whl` : **PASS** ;
- vérification du contenu des artefacts : **PASS** ;
- smoke du wheel installé avec `--no-deps` dans un répertoire isolé : **PASS** ;
- version installée : **0.32.8** ;
- migrations détectées : **54** ;
- assets runtime, contrats GA/release et routes attendues : **PASS**.

## Couverture et intégration complète

Cette correction est limitée à la cascade CSS et à ses tests de non-régression. Les tests directement impactés sont couverts par les **62 tests Python ciblés** et les **63 tests frontend**, tous réussis. Les **581 tests unitaires/performance** ont également tous réussi.

La suite d'intégration complète et la mesure globale de couverture n'ont pas été réexécutées intégralement dans ce sandbox. Le seuil contractuel global de couverture **>= 98 %** reste bloquant dans GitHub Actions, de même que la suite d'intégration complète.

## Limites de l'environnement

Docker n'est pas disponible dans le sandbox. Les validations suivantes restent déléguées aux workflows bloquants de CI/CD :

- build et démarrage Compose réels ;
- smoke conteneurs ;
- Trivy image/repository ;
- DAST ;
- couverture globale complète >= 98 % ;
- exécution complète de la suite d'intégration dans l'environnement CI dédié.
