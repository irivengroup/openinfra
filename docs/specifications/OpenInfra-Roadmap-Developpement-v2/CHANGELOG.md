## v0.29.72 — DCIM dépendances CRUD topologiques

- Ajout `TST-P10-DCIM-DEPENDENCY-CRUD` pour verrouiller la gestion explicite des bâtiments, étages, salles et zones.
- Alignement avec `REQ-00813` du CDC v4.8.1.

## v0.29.71 — compatibilité CLI/CI des commandes édition

- Ajout `TST-P08-CLI-EDITION-DATA-COMPAT`.


### Validation v0.29.74 — Formulaires ITAM racine et migrations minimales

La roadmap intègre `TST-P14-ITAM-FORM-HIERARCHY-MIGRATION-MINIMAL` : les formulaires Organisation sont racine, les formulaires Tenant n'ont pas de tenant parent, les ressources restent rattachées au couple Organisation → Tenant filtré et aucune migration PostgreSQL supplémentaire n'est créée pour un correctif UI.
