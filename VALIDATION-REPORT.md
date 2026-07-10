# OpenInfra v0.29.87 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.87`  
Périmètre : `P08 / EPIC-0805 — Ajustements du header, recherche globale centrée et mégamenu au survol` ; conservation intégrale de `P15 / EPIC-1501`

## Résultat global

La livraison affine le contrat responsive existant sans retirer de fonctionnalité : hauteur initiale de la seconde barre restaurée, recherche globale compacte centrée à 50 %, composants rapprochés à droite, états visuels contrastés et mégamenu déclenché au survol/focus avec clic de secours. Le graphe RSOT livré en v0.29.86 reste inchangé.

- Tests Python collectés : **635** dans **87 fichiers**.
- Tests unitaires : **234 PASS**.
- Tests d’intégration : **398 PASS**.
- Tests d’architecture : **3 PASS**.
- Couverture globale exacte : **98,0338384308 %** — `21 091 / 21 514` lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **13 PASS**.
- Lint frontend : **PASS**.
- Build frontend Vite : **PASS**.
- Vite **8.1.4** et plugin React actualisés ; `npm audit --audit-level=high` : **0 vulnérabilité**.

La suite Python a été exécutée par lots avec accumulation dans un fichier de couverture unique. Les fichiers CLI et certains groupes DCIM dépassaient le timeout lorsqu’ils étaient instrumentés ensemble ; ils ont été isolés sans exclusion de test ni altération du calcul final.

## Graphe de dépendances RSOT

- Projection en lecture des objets et relations RSOT historisés, sans seconde source de vérité.
- Isolation stricte par tenant et permission `rsot.read`.
- Parcours entrant, sortant ou bidirectionnel.
- Parcours en largeur déterministe, borné en profondeur et nombre de nœuds.
- Tolérance des cycles sans boucle infinie.
- Filtres par type de relation et date de référence `as_of`.
- Recherche du chemin le plus court.
- Analyse d’impact direct et indirect avec agrégats par distance, type d’objet et catégorie de ressource.
- Résultats tronqués explicitement lorsque les limites sont atteintes.
- Audit des consultations.
- Exposition alignée par service applicatif, CLI, API HTTP, OpenAPI et portail FR/EN.
- Aucune migration PostgreSQL : réutilisation des tables RSOT et relations existantes.

## Navigation web responsive

Trois modes non superposés sont appliqués selon la largeur utile :

1. **Écran large — `>= 1200 px`** : sidebar persistante et scrollable sous le header fixe.
2. **Tablette et portable compact — `768 px` à `1199,98 px`** : sidebar masquée ; les dix icônes de composants restent alignées et ouvrent au survol ou au focus un mégamenu contextuel multicolonne reprenant tous les contextes et opérations.
3. **Mobile — `< 768 px`** : barre de composants remplacée par un bouton de menu unique ouvrant la navigation complète.

Garanties validées :

- aucune opération de la sidebar n’est perdue dans le mégamenu ou le menu compact ;
- Dashboard reste une navigation directe ;
- fermeture par bouton, backdrop et touche `Échap` ;
- identifiants DOM distincts entre surfaces ;
- panneaux scrollables avec `overscroll-behavior` ;
- support de `prefers-reduced-motion` ;
- cibles interactives d’au moins **44 px** sur périphériques à pointeur grossier ;
- parité exacte des styles React/runtime packagé ;
- suppression de l’ancien mécanisme mobile `mobile-open` devenu redondant.

## Header et navigation ajustés

- Padding vertical initial de la seconde barre restauré à `0,5 rem`.
- Recherche globale conservée à `2 rem`, centrée par rapport à la page et dimensionnée à `50 %` de la largeur disponible.
- Composants compacts, rapprochés et alignés à droite sur écran large.
- États actif, survol et focus rendus fortement contrastés sur le fond bleu du header.
- En mode mégamenu, survol et focus ouvrent le panneau ; le clic reste disponible comme fallback tactile et accessible.
- Sélecteur FR/EN, Swagger et ReDoc restent alignés ; les cibles tactiles atteignent `2,75 rem` sur pointeur grossier.
- Ombre du header et offset dynamique du contenu préservés.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker` : **PASS**, **154 fichiers**.
- `ruff check src tests scripts docker` : **PASS**.
- `mypy src/openinfra` : **PASS**, aucune erreur sur **57 modules source**.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python -m compileall -q src tests scripts docker` : **PASS**.
- Validation syntaxique et contractuelle des workflows GitHub Actions : **PASS**.
- Gate CI ciblé Graphe : **PASS**.
- Gate CI ciblé navigation responsive/header : **PASS**.

## Frontend

- `npm --prefix web test` : **12 PASS**.
- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run build` : **PASS** avec Vite `5.4.21`.
- Validation statique React/runtime packagé : **PASS**.
- Parité byte-identique des feuilles de style React/runtime : **PASS**.
- Validation du moteur i18n FR/EN partagé : **PASS**.
- Nettoyage des anciens styles et méthodes mobiles non utilisés : **PASS**.

## CDC, roadmap et installateurs

Cette livraison réémet le CDC et la roadmap parce que la recommandation responsive modifie une décision UX existante.

- CDC v4.8.1 : **PASS** — **825 exigences**, **529 entités**, **625 tests contractuels**.
- Roadmap v2 : **PASS** — **19 phases**, **115 epics**, **8 gates**, **94 tests**.
- `REQ-00811` : navigation responsive adaptative à trois modes.
- `REQ-00825` : header compact, contrôles alignés, cibles tactiles et hiérarchie d’ombres.
- `TST-WEB-124` et `TST-WEB-125` : régressions responsive et header.
- `EPIC-0805` : accessibilité et navigation responsive adaptative.
- `TST-P08-WEB-RESPONSIVE-NAVIGATION` et `TST-P08-WEB-COMPACT-HEADER` : gates roadmap.
- Six installateurs autonomes Lite/Pro/Entreprise : **PASS**.
- Alignement Enterprise : **PASS**.
- Les six guides de scopes manquants exigés par le validateur CDC ont été ajoutés.
- La variante de nom `Matrice-alignement-enterprise-v4.3.csv` attendue par le validateur est fournie sans supprimer la matrice historique en français.

## Packaging attendu

Le build doit produire :

- `openinfra-0.29.86-py3-none-any.whl` ;
- `openinfra-0.29.86.tar.gz`.

Le vérificateur d’artefact exige notamment :

- le service de graphe ;
- les assets i18n, JavaScript et CSS du portail ;
- le document OpenAPI packagé ;
- les **40 migrations PostgreSQL**, dernière migration `0040_dcim_floor_nomenclature.sql`.

## Contrôles limités par l’environnement

- `pip-audit --strict` a été lancé mais n’a pas pu résoudre `pypi.org`. Le contrôle est **non concluant**, et non déclaré comme réussi.
- Docker, Podman et `psql` ne sont pas disponibles ; les smoke tests nécessitant un daemon de conteneurs ou une instance PostgreSQL réelle ne sont donc pas exécutables localement.
- La capture visuelle automatisée par navigateur Chromium est indisponible dans ce conteneur. Le contrat UX a été validé par tests DOM/CSS, tests Node.js, tests Python et build Vite, mais pas par comparaison de captures d’écran.

## Commandes de reproduction

```bash
ruff format --check src tests scripts docker
ruff check src tests scripts docker
mypy src/openinfra
bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python scripts/quality_gate.py
python scripts/validate_frontend.py --project-root .
python scripts/validate_autonomous_installer.py --root installers
python scripts/validate_enterprise_alignment.py --project-root .
python -m compileall -q src tests scripts docker

python -m pytest
coverage report --fail-under=98

npm --prefix web test
npm --prefix web run lint
npm --prefix web run build

python -m build
python scripts/verify_artifact.py dist/openinfra-0.29.86-py3-none-any.whl
```
