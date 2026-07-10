# Navigation responsive du portail OpenInfra

## Objectif

Le portail doit conserver l’intégralité de la navigation métier sur les ordinateurs, tablettes et smartphones sans afficher une sidebar pleine largeur, sans défilement horizontal et sans masquer une opération.

## Modes de navigation

### Écran large — largeur utile supérieure ou égale à 1200 px

- Header fixe avec icônes des composants.
- Sidebar persistante, scrollable et indépendante du contenu principal.
- Les accordéons restent dans le flux vertical et repoussent les éléments suivants.
- Le contenu principal occupe l’espace restant.

### Tablette et portable compact — 768 à 1199,98 px

- Sidebar totalement masquée.
- Les dix icônes de composants restent alignées dans une grille unique du header.
- Le clic sur un composant ouvre son mégamenu sans exécuter implicitement sa première opération.
- Le mégamenu affiche les contextes en colonnes adaptatives et toutes les opérations correspondantes.
- Dashboard reste une navigation directe.

### Mobile — largeur inférieure à 768 px

- La grille des composants est remplacée par une icône de menu unique.
- Le panneau compact expose tous les composants, contextes et opérations de la sidebar.
- Le panneau est scrollable, borné par la hauteur disponible et superposé au contenu via un backdrop.

## Header et barre d’outils

- La seconde barre du header utilise un padding vertical de `0.375rem`, soit une réduction de 25 % par rapport au `0.5rem` précédent.
- La recherche globale, le sélecteur de langue, Swagger et ReDoc partagent la variable `--openinfra-toolbar-control-height`.
- La hauteur visuelle est de `2rem` avec une souris ou un pavé tactile précis.
- Sur un périphérique tactile ou tout pointeur grossier, la hauteur minimale est portée à `2.75rem` (44 px).
- L’ombre du header reste supérieure à `--openinfra-content-shadow`, mais inférieure à l’ancienne ombre afin d’alléger la page.

## Accessibilité

- `aria-current` identifie le composant et l’opération actifs.
- Les déclencheurs de mégamenu utilisent `aria-haspopup`, `aria-expanded` et `aria-controls`.
- Chaque navigation possède un libellé accessible.
- Les menus sont fermables par bouton, backdrop ou touche `Échap`.
- `prefers-reduced-motion` désactive les transitions non essentielles.
- Les identifiants DOM sont préfixés par surface (`sidebar` ou `compact`) pour éviter les doublons.

## Tests

```bash
cd web
npm test
npm run lint
npm run build

cd ..
python -m pytest -q --no-cov tests/integration/test_responsive_navigation_contract.py
python scripts/validate_frontend.py
```
