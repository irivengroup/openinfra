## v0.29.76 — DCIM sites & dépendances, partenaires et pays ISO

Le portail OpenInfra expose désormais le contexte DCIM **Sites & dépendances** avec le CRUD des sites, bâtiments, étages, salles et chassis/racks. Les formulaires de salles acceptent des plages bornées de lignes et colonnes (`0-12`, `A-F`) qui sont normalisées par le backend et réutilisées par les sélecteurs de localisation.

La sélection d’un étage est conditionnelle : elle est obligatoire uniquement lorsque le bâtiment possède au moins un étage actif. Les bâtiments sans étage peuvent contenir des salles sans champ étage, ce qui couvre les locaux plain-pied ou les sites techniques simples.

Côté ITAM, le libellé **Fournisseurs et Supports** est remplacé par **Partenaires**. Les anciens tenants sont présentés à l’opérateur comme **Filiale/Subdivision** et regroupés sous le sous-menu **Organisations**, sans modifier les contrats techniques `tenant_id` existants.

Les champs pays nécessaires dans les formulaires web sont rendus en listes déroulantes ISO-3166 alpha-2 groupées par continent via `/api/v1/reference/countries`.
