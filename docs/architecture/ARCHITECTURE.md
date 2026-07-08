## v0.29.73 — Architecture DCIM topologique CRUD

La couche application expose désormais `DcimTopologyService` comme point d'entrée unique du cycle de vie des sites et de leurs dépendances topologiques : bâtiments, étages, salles et zones.

Principes conservés :

- domaine pur dans `openinfra.domain.dcim` ;
- orchestration métier dans `openinfra.application.dcim_services` ;
- ports de persistance inchangés dans `openinfra.application.ports` ;
- adaptateurs JSON/PostgreSQL compatibles ;
- API, CLI et portail web branchés sur le même service applicatif ;
- retrait logique non destructif avec cascade contrôlée ;
- catalogue `/api/v1/dcim/topology-catalog` maintenu comme source des sélecteurs UI.
