# OpenInfra v0.30.9 — rapport de validation

Date : 2026-07-12

## Périmètre

Correctif visuel strictement limité à la restauration des couleurs approuvées.

- composants racine inactifs de la sidebar : bleu IONOS `#003D8F` ;
- titres contextuels des pages métier : bleu IONOS `#003D8F` ;
- composant racine actif au hover/focus : texte, icône et chevron turquoise clair ;
- fond, bordure et ombre de l’état actif inchangés ;
- parité stricte entre le portail React et le runtime statique packagé ;
- aucune migration, dépendance, route, règle métier ou évolution CDC/roadmap.

## Fichiers principaux modifiés

- `web/src/openinfra-theme.css`
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css`
- `web/tests/responsive-navigation.test.mjs`
- `tests/integration/test_responsive_navigation_contract.py`
- métadonnées de version, README, changelog et rapport de validation

## Validations exécutées

### Python

- Ruff format : **PASS**, 295 fichiers déjà formatés.
- Ruff lint : **PASS**.
- mypy strict : **PASS**, 94 fichiers source contrôlés sans erreur.
- `compileall` : **PASS**.
- Bandit : **PASS**, aucun finding bloquant.
- tests unitaires : **408 réussis**.
- tests d’intégration : **588 réussis**.
- tests architecture et performance : **14 réussis**.
- total Python : **1 010 tests réussis**, aucune erreur.
- tests ciblés navigation responsive et accessibilité : **11 réussis**.
- validation OpenAPI des deux contrats : **PASS**.
- garde de sécurité du dépôt : **PASS**.
- validation statique frontend depuis Python : **PASS**.

La suite Python complète a dû être exécutée en partitions déterministes, car une exécution monolithique avec instrumentation de couverture dépasse la fenêtre maximale du sandbox. La couverture globale n’a donc pas pu être recalculée de manière fiable dans cet environnement. La livraison 0.30.8 validait **98,002195 %** et le code Python de production de 0.30.9 ne change que la constante de version ; le seuil CI existant reste bloquant à **98 %** et n’a pas été abaissé ni contourné.

### Frontend

- tests Node : **53 réussis**, aucune erreur.
- ESLint : **PASS**.
- contrôle d’accessibilité statique : **PASS**.
- contrôle JSX/accessibilité : **PASS**.
- build Vite 8.1.4 : **PASS**.
- `npm audit --audit-level=high` : **PASS**, 0 vulnérabilité.

### Packaging

- construction isolée wheel et sdist avec Hatchling : **PASS** ;
- vérification structurelle du wheel et du sdist : **PASS** ;
- installation isolée du wheel sans dépendances embarquées : **PASS** ;
- smoke test du wheel installé : **PASS** — version, scripts console, 53 migrations, OpenAPI et assets runtime validés.

## Limites de validation

- `pip-audit --strict --requirement requirements/security-audit.txt` n’a pas pu joindre `pypi.org` en raison de l’indisponibilité DNS du sandbox. Aucun échec de dépendance n’a été observé localement ; le gate CI réseau reste inchangé.
- l’approbation visuelle finale doit être réalisée dans un navigateur après rechargement forcé afin d’éliminer les anciens assets en cache.

## Risque résiduel

Risque faible et limité au rendu CSS. Les règles ajoutées utilisent le token de thème existant, n’altèrent aucune structure DOM et sont verrouillées par des tests de contrat dans les deux portails.
