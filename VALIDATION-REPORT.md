# OpenInfra v0.32.7 — rapport de validation

Date : 2026-07-14

## Objet

Cette livraison affine l'expérience visuelle du portail OpenInfra sans modifier la palette approuvée. Les menus racine de la sidebar, les titres de contexte et les titres de page utilisent le bleu nuit le plus sombre déjà présent dans le thème (`--openinfra-ink`). Une couche de transparence contrôlée renforce la profondeur visuelle des surfaces sans appliquer d'opacité aux contenus lisibles.

## Fonctionnalités livrées

- menus racine de la sidebar en bleu nuit très foncé proche du noir ;
- titres de contexte de navigation et titres contextuels de page alignés sur le même niveau de hiérarchie visuelle ;
- conservation stricte des états actifs existants, notamment le turquoise sur le texte et l'icône du composant actif au survol ;
- transparence contrôlée sur sidebar, titlebar, cartes, formulaires, recherche globale, résultats, mégamenu, navigation compacte, tableaux et surfaces secondaires ;
- profondeur visuelle obtenue par backgrounds alpha, bordures translucides, ombres légères et `backdrop-filter` ;
- fallback opaque pour les navigateurs sans `backdrop-filter` ;
- mode `prefers-contrast: more` rendu opaque et fortement contrasté ;
- aucun `opacity` appliqué aux conteneurs de contenu, afin de ne pas dégrader textes, icônes ou contrôles ;
- thème React et runtime packagé strictement synchronisés ;
- tests de non-régression verrouillant la palette approuvée et la nouvelle hiérarchie bleu nuit.

## Palette et compatibilité

La palette existante n'a pas été modifiée. Les tests verrouillent notamment les valeurs suivantes :

- `--openinfra-ink: #001b41` ;
- `--openinfra-navy: #001b41` ;
- `--openinfra-navy-2: #052f6f` ;
- `--openinfra-blue: #003d8f` ;
- `--openinfra-action: #0066ff` ;
- `--openinfra-cyan: #00c2ff` ;
- `--openinfra-green: #15a362` ;
- `--openinfra-fuchsia: #ff00ff` ;
- `--openinfra-page-bg: #f4f8ff`.

Impact :

- aucune migration PostgreSQL ;
- aucune rupture d'API métier ou de CLI publique ;
- aucune suppression de fonctionnalité ;
- aucune nouvelle dépendance runtime ;
- comportement responsive conservé ;
- accessibilité WCAG 2.2 AA conservée ;
- compatibilité ascendante complète avec la v0.32.6.

## Fichiers principaux modifiés

- `web/src/openinfra-theme.css` ;
- `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css` ;
- `web/tests/theme-colors.test.mjs` ;
- `VERSION` ;
- `pyproject.toml` ;
- `web/package.json` ;
- `web/package-lock.json` ;
- métadonnées et contrats de version 0.32.7 ;
- `README.md` ;
- `CHANGELOG.md` ;
- `VALIDATION-REPORT.md`.

## Validations exécutées

### Frontend

- tests frontend Node : **63 réussis** ;
- tests ciblés thème/navigation/accessibilité : **19 réussis** ;
- validation des assets statiques : **PASS** ;
- validation accessibilité WCAG 2.2 AA : **PASS** ;
- ESLint JSX/accessibilité : **PASS** ;
- build Vite production : **PASS** ;
- validation du bundle : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- synchronisation exacte du CSS React/runtime : **PASS**.

### Python et contrats runtime

- tests collectés : **1 223** ;
- suites unitaires et performance : **581 tests réussis** ;
- tests Python ciblés de régression frontend/runtime/documentation/version : **66 réussis** ;
- Ruff format : **348 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **107 modules conformes** ;
- `compileall` : **PASS** ;
- validation frontend Python : **PASS** ;
- validation documentation GA : **10 documents, 33 commandes CLI, 7 opérations API, version 0.32.7** ;
- alignement Enterprise : **PASS** ;
- runtime natif : **PASS** ;
- security gate : **PASS** ;
- Bandit complet `src/openinfra` : **PASS, aucun résultat bloquant**.

### Packaging

- build final sdist `openinfra-0.32.7.tar.gz` : **PASS** ;
- build final wheel `openinfra-0.32.7-py3-none-any.whl` : **PASS** ;
- vérification du contenu des deux artefacts : **PASS**.
- smoke du wheel installé en environnement virtuel dédié : **PASS**, version **0.32.7**, **54 migrations**, assets runtime et contrats GA/release présents.

## Couverture et intégration complète

La suite d'intégration complète contient **133 fichiers**. Une exécution séquentielle isolée a été lancée afin d'éviter les interactions entre runtimes, mais elle a dépassé la fenêtre maximale d'exécution du sandbox avant de produire un résultat global exploitable. Elle n'est donc pas déclarée comme validée intégralement dans cet environnement.

Les tests directement impactés par cette évolution visuelle et de version sont couverts par les **66 tests Python ciblés** et les **63 tests frontend**, tous réussis. Les **581 tests unitaires/performance** ont également tous réussi.

Le seuil contractuel global de couverture **>= 98 %** reste bloquant dans GitHub Actions. Une exécution partielle ciblée ne peut pas fournir un taux global représentatif et n'est pas utilisée comme preuve de couverture de release.

## Limites de l'environnement

Docker n'est pas disponible dans le sandbox. Les validations suivantes restent déléguées aux workflows bloquants de CI/CD :

- build et démarrage Compose réels ;
- smoke conteneurs ;
- Trivy image/repository ;
- DAST ;
- couverture globale complète >= 98 % ;
- exécution complète des 133 fichiers d'intégration dans l'environnement CI dédié.
