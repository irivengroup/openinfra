## v0.29.73 — DCIM dépendances administrables depuis le portail

Le portail OpenInfra expose les opérations DCIM de gestion topologique suivantes dans le contexte `Sites & dépendances` :

- sites ;
- bâtiments ;
- étages ;
- salles ;
- zones ;
- catalogue des dépendances.

Les champs de référence DCIM restent des sélecteurs alimentés par `/api/v1/dcim/topology-catalog`. Les champs servant à définir une nouvelle grille de salle ou de zone restent des valeurs métier explicites (`rows`, `columns`) car ils créent le référentiel de lignes/colonnes lui-même.
