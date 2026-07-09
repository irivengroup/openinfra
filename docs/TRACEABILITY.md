## v0.29.76 — Traçabilité DCIM sites/dépendances et réalignement ITAM

| Surface | Élément livré |
|---|---|
| Domaine | Plages DCIM bornées, étage conditionnel salle, cycle de vie rack |
| Application | CRUD chassis/racks, cascade non destructive site/bâtiment/salle vers racks |
| Persistance | Migration PostgreSQL `0033_dcim_site_dependencies_rack_lifecycle.sql` |
| API | `/api/v1/dcim/rack*`, `/api/v1/reference/countries` |
| CLI | `openinfra dcim racks`, `rack`, `rack-update`, `rack-delete` |
| Web | `Partenaires`, `Filiale/Subdivision` sous `Organisations`, pays ISO groupés |
| Tests | `TST-WEB-116`, `TST-P14-DCIM-SITE-DEPENDENCIES-RACKS-COUNTRIES` |
