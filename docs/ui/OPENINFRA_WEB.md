## v0.29.75 — ITAM Fournisseurs et Supports

Le portail OpenInfra ajoute le contexte ITAM `Fournisseurs et Supports` pour administrer les partenaires rattachés à une organisation : constructeurs, éditeurs logiciels et supports tiers. Les formulaires de garanties, licences logicielles et supports tiers utilisent désormais des sélecteurs partenaires filtrés par organisation et type de partenaire compatible.

Règles UX :

- Organisation sélectionnée avant partenaire.
- Aucun partenaire en saisie libre comme autorité métier.
- Les partenaires actifs uniquement sont proposés.
- Les formulaires de création partenaire exigent la carte d’identité entreprise et au moins un téléphone.

## v0.29.73 — DCIM dépendances administrables depuis le portail

Le portail OpenInfra expose les opérations DCIM de gestion topologique suivantes dans le contexte `Sites & dépendances` :

- sites ;
- bâtiments ;
- étages ;
- salles ;
- zones ;
- catalogue des dépendances.

Les champs de référence DCIM restent des sélecteurs alimentés par `/api/v1/dcim/topology-catalog`. Les champs servant à définir une nouvelle grille de salle ou de zone restent des valeurs métier explicites (`rows`, `columns`) car ils créent le référentiel de lignes/colonnes lui-même.
