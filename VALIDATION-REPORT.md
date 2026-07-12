# OpenInfra v0.30.8 — rapport de validation

Date : 2026-07-12

## Périmètre

Correctif visuel strictement limité au survol et au focus d’un composant racine déjà actif dans la sidebar.

- le fond actif existant est conservé sans modification ;
- la bordure et l’ombre restent inchangées ;
- seuls le texte, l’icône et le chevron héritant de `currentColor` passent au turquoise clair du thème ;
- le portail React et le runtime statique packagé utilisent une feuille de style strictement identique ;
- aucune migration, dépendance, route, règle métier ou évolution du CDC/roadmap n’est introduite.

## Fichiers principaux modifiés

- `web/src/openinfra-theme.css`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`
- `web/tests/responsive-navigation.test.mjs`
- `tests/integration/test_responsive_navigation_contract.py`
- métadonnées de version et documentation de livraison

## Résultats

### Backend et contrats

- 1 009 tests Python réussis ;
- couverture : 98,002195 % ;
- seuil contractuel de 98 % : PASS ;
- Ruff format : 288 fichiers conformes ;
- Ruff lint : PASS ;
- mypy strict : 94 modules, PASS ;
- `compileall` : PASS ;
- Bandit : PASS ;
- security gate : PASS ;
- quality gate : PASS ;
- deux contrats OpenAPI : PASS ;
- six profils installateurs : PASS ;
- CDC 4.9.0 : 840 exigences et 529 entités, PASS ;
- roadmap 2.1.0 : 21 phases, 125 epics, 10 gates et 106 tests, PASS.

### Frontend

- 52 tests Node.js réussis ;
- parité CSS React/runtime statique : PASS ;
- contrat du hover actif limité à la propriété `color` : PASS ;
- ESLint JSX : PASS ;
- WCAG 2.2 AA : PASS ;
- build Vite : PASS ;
- audit npm : 0 vulnérabilité.

## Sécurité des dépendances

`pip-audit --strict --requirement requirements/security-audit.txt` a été lancé, mais l’environnement n’a pas pu résoudre `pypi.org`. Le gate reste bloquant dans GitHub Actions. Aucune dépendance n’est modifiée dans cette livraison.

## Validation visuelle

Le contrat automatisé garantit l’absence de modification du fond, de la bordure et de l’ombre. L’approbation visuelle finale doit être effectuée dans le navigateur cible après reconstruction des assets et rechargement forcé. Après approbation, la charte graphique est considérée comme figée et ne doit plus être modifiée sans demande explicite.
