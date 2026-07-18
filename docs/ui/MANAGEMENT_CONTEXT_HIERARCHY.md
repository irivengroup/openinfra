# Hiérarchie de contexte des formulaires de gestion

Version cible : `0.34.4`

## Objectif

Toutes les pages de gestion et tous les formulaires qui manipulent une ressource rattachée à un contexte organisationnel ou physique doivent présenter les critères structurants dans un ordre unique et prévisible.

Ordre canonique :

1. Organisation ;
2. Filiale/Subdivision ;
3. Site ;
4. Bâtiment ;
5. Étage ;
6. Salle ;
7. Ligne / Colonne ;
8. Rack.

La hiérarchie est appliquée **selon le contexte**. Un niveau absent du modèle de la ressource n'est pas inventé et un niveau qui représente l'objet cible lui-même n'est pas ajouté comme faux parent.

## Règles UX

- Les critères parents sont placés avant les filtres métier tels que statut, type, pays ou ville.
- Les listes de valeurs sont dépendantes des parents déjà sélectionnés.
- La modification d'un parent efface automatiquement les sélections descendantes devenues ambiguës ou invalides.
- Ligne et Colonne appartiennent au même niveau de priorité et ne s'invalident pas mutuellement.
- Les références DCIM sont proposées sous forme de sélecteurs issus du catalogue de topologie ; aucun champ texte libre n'est introduit pour Site, Bâtiment, Étage, Salle, Ligne, Colonne ou Rack.
- Lorsqu'un parent requis par le formulaire n'est pas encore sélectionné, le sélecteur enfant est désactivé jusqu'à la définition du contexte parent.
- Les valeurs devenues inexistantes après rechargement du catalogue sont supprimées des filtres actifs.
- Les filtres sans valeur pertinente dans le contexte courant ne sont pas affichés.

## Portée organisationnelle et localisation

`Organisation` et `Filiale/Subdivision` définissent la portée organisationnelle. La chaîne `Site → Bâtiment → Étage → Salle → Ligne/Colonne → Rack` définit la localisation physique.

Les étages restent une projection générée du bâtiment : cette hiérarchie n'introduit aucun CRUD d'étage.

## Implantation dans le projet

Le code source de cette logique fait partie intégrante du projet :

```text
web/src/management/
├── context-hierarchy.js
├── operation-schema.js
└── resources.js
```

Le runtime packagé conserve la même hiérarchie sous :

```text
src/openinfra/interfaces/rendering/static/assets/management/
├── context-hierarchy.js
└── resources.js
```

Les anciens modules `management-resources.js` restent des façades de compatibilité afin de préserver les imports historiques.

## Non-régression

Cette évolution ne modifie ni les endpoints API, ni les commandes CLI, ni les permissions RBAC, ni les migrations, ni la palette graphique. Elle agit uniquement sur l'ordre, la dépendance et la cohérence des critères de gestion.
