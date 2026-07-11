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

## Hiérarchie chromatique des textes

Le thème n’utilise pas les gris Bootstrap par défaut pour le contenu fonctionnel. La lisibilité et l’identité visuelle reposent sur quatre jetons sémantiques explicitement bleus :

- `--openinfra-text-primary: #001b41` pour le texte principal et les titres ;
- `--openinfra-text-secondary: #234f7d` pour les sous-titres et informations secondaires importantes ;
- `--openinfra-text-muted: #315d8a` pour les métadonnées et aides contextuelles ;
- `--openinfra-text-subtle: #3d648d` pour les placeholders et informations de moindre priorité.

Les utilitaires Bootstrap `text-secondary`, `text-muted` et `text-body-secondary` sont redéfinis avec ces jetons. Les couleurs sont des valeurs opaques et déterministes : aucun mélange alpha du bleu nuit sur un fond clair n’est utilisé pour les textes, car ce mélange produisait un rendu grisâtre variable. Chaque niveau conserve un contraste WCAG 2.2 AA supérieur à 4,5:1 sur les surfaces blanches, bleu très pâle et fond de page OpenInfra. Les thèmes React et runtime packagé doivent rester strictement identiques.

## Accessibilité transversale

Toutes les pages et tous les composants appliquent la baseline WCAG 2.2 AA décrite dans `docs/ui/WEB_ACCESSIBILITY.md`. Le contrat couvre la navigation clavier, les lecteurs d’écran, les annonces dynamiques, les formulaires, le focus, le contraste, les couleurs forcées, la réduction des mouvements et les alternatives textuelles. Aucun état métier n’est communiqué uniquement par une couleur ou par un son.

## Formulaires typés, validation anticipée et normalisation

Les deux portails utilisent le même moteur de définition et de validation des champs. Les champs de date et de date-heure sont rendus par les contrôles natifs `date` et `datetime-local`, habillés par le thème OpenInfra. La valeur date reste au format `YYYY-MM-DD` ; la date-heure est normalisée par l’application en ISO-8601 UTC avant l’appel API.

Les champs libres sont contrôlés avant soumission selon leur nature : IPv4/IPv6, CIDR, email, téléphone, code postal contextualisé par pays, adresse MAC, hostname/FQDN, URL HTTP(S), nombre, JSON, CSV et texte. Les erreurs sont exposées avec `aria-invalid` et le message de validation localisé. Cette validation ergonomique ne remplace jamais les contraintes et validations métier du backend.

Le focus d’un champ ne modifie ni son épaisseur, ni sa position, ni sa taille : seule la couleur de bordure change. Les erreurs conservent une bordure rouge sans halo supplémentaire.

## Rangement fonctionnel du Graphe

Le Graphe de dépendances est une capacité RSOT et non un composant de premier niveau. Ses opérations sont regroupées sous RSOT dans trois ensembles cohérents : exploration, analyse d’impact et exports. Les routes HTTP et commandes CLI restent inchangées pour préserver la compatibilité ascendante.
