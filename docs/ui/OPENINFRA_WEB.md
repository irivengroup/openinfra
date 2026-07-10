# Interface web OpenInfra

## Internationalisation FR/EN

L'interface web prend en charge uniquement le français (`fr`) et l'anglais (`en`). Le moteur d'internationalisation est partagé, sans divergence, entre le frontend React et le portail statique packagé dans le wheel Python.

### Sélection initiale

L'ordre de résolution est déterministe :

1. choix explicite précédemment enregistré dans `localStorage` sous la clé `openinfra.language` ;
2. première langue supportée de `navigator.languages` ;
3. langue `navigator.language` ;
4. anglais comme fallback obligatoire.

Les variantes régionales sont ramenées à leur langue principale : `fr-FR` devient `fr`, `en-GB` devient `en`. Toute langue non supportée, par exemple `de-DE`, `es-ES` ou `ja-JP`, bascule sur `en`.

### Changement de langue

Le sélecteur `EN / FR` du header applique la langue immédiatement, met à jour l'attribut HTML `lang` et mémorise le choix. Aucun rechargement de page n'est requis.

### Périmètre traduit

La localisation couvre tous les composants du portail :

- header, panneau latéral, dashboard et recherche globale ;
- noms et descriptions des composants ;
- groupes fonctionnels et opérations ;
- libellés, options, validations et résultats de formulaires ;
- états, compteurs et messages utilisateur ;
- catégories et types de ressources ;
- pays ISO et continents ;
- libellés générés des étages DCIM.

Les identifiants techniques, codes, valeurs API, chemins HTTP, clés JSON et données métier saisies par les opérateurs ne sont jamais traduits. Les pays conservent leur code ISO alpha-2 comme valeur et affichent uniquement leur nom localisé.

### Résolution du runtime web

Le serveur Python utilise par défaut le portail statique packagé, qui constitue le runtime de référence et contient les assets contractuels stables. Un build React présent dans `web/dist` ne peut pas masquer ce runtime. Un répertoire alternatif reste utilisable uniquement lorsqu'il est fourni explicitement avec `--static-root`.

### Sécurité et fonctionnement hors ligne

Le catalogue i18n est livré localement dans `assets/openinfra-i18n.js`. Aucun service de traduction, CDN ou appel réseau tiers n'est utilisé. Aucun secret n'est stocké par le mécanisme de langue.

### Validation

Les gates bloquent la livraison si :

- le fallback n'est pas `en` ;
- une langue autre que `fr` ou `en` est déclarée ;
- la détection navigateur ou le sélecteur disparaît ;
- les moteurs React et runtime diffèrent ;
- l'asset i18n manque dans le wheel ;
- les tests de localisation, le lint ou le build frontend échouent.

## Accessibilité transversale

Toutes les pages et tous les composants appliquent la baseline WCAG 2.2 AA décrite dans `docs/ui/WEB_ACCESSIBILITY.md`. Le contrat couvre la navigation clavier, les lecteurs d’écran, les annonces dynamiques, les formulaires, le focus, le contraste, les couleurs forcées, la réduction des mouvements et les alternatives textuelles. Aucun état métier n’est communiqué uniquement par une couleur ou par un son.
