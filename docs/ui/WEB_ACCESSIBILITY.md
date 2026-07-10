# Accessibilité du portail web OpenInfra

## Référence et périmètre

Le portail React et le runtime web packagé utilisent **WCAG 2.2 niveau AA** comme baseline contractuelle. Cette baseline couvre toutes les pages, tous les composants, les menus, les formulaires, la recherche globale, les résultats et les messages d’état. Elle ne constitue pas une certification externe : la conformité finale doit également être vérifiée manuellement avec des technologies d’assistance et des utilisateurs représentatifs.

## Navigation clavier et lecteurs d’écran

- trois liens d’évitement permettent d’atteindre directement le contenu, la navigation des composants et la recherche globale ;
- les zones principales sont exposées par des landmarks sémantiques (`banner`, `navigation`, `main`, `form`, `status`, `alert`) ;
- la navigation des composants accepte `Tab`, `Maj+Tab`, les flèches, `Home`, `End`, `Entrée`, `Espace`, `Échap` et restaure le focus après fermeture ;
- les changements de page, ouvertures/fermetures de navigation, sélections d’opération, résultats et états runtime sont annoncés dans une région `aria-live` ;
- les champs obligatoires ont un libellé explicite, un marqueur textuel, `required`, `aria-invalid` et une validation native focalisable ;
- les liens Swagger et ReDoc annoncent l’ouverture dans un nouvel onglet.

## Accessibilité visuelle et motrice

- le focus visible utilise un contour à double contraste ;
- les états actif, survol et focus ne reposent jamais uniquement sur la couleur ;
- les modes `prefers-contrast: more` et couleurs forcées sont pris en charge ;
- les cibles tactiles atteignent au moins 44 px sur les périphériques à pointeur grossier ;
- les animations bounce/fade sont courtes et supprimées lorsque `prefers-reduced-motion: reduce` est actif ;
- le header fixe est compensé par `scroll-padding-top` et `scroll-margin-top` afin de ne pas masquer le contenu focalisé.

## Utilisateurs sourds ou malentendants

Le portail actuel ne contient aucun média audio ou vidéo et ne transmet aucune information uniquement par le son. Tout futur contenu audio ou vidéo devra fournir, selon sa nature, des sous-titres synchronisés, une transcription textuelle et une alternative visuelle aux alertes sonores avant intégration.

## Contrôle qualité

La CI exécute :

```bash
npm --prefix web run lint
npm --prefix web run a11y
npm --prefix web run a11y:jsx
npm --prefix web test
npm --prefix web run build
python -m pytest -q tests/integration/test_web_accessibility_contract.py
python scripts/validate_frontend.py --project-root .
```

Les validations automatisées vérifient les contrats DOM/CSS/ARIA, la parité React/runtime, les règles JSX accessibles, la navigation clavier, la réduction des animations, les modes de contraste et l’absence de média non accompagné. Une recette manuelle doit compléter ces gates avec au minimum NVDA ou JAWS sous Windows, VoiceOver sous macOS/iOS, TalkBack sous Android, navigation clavier seule, zoom 200 % et mode contraste élevé.

