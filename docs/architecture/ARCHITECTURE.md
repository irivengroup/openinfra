## v0.29.75 — Architecture ITAM partenaires accrédités

Le référentiel `ItamPartner` devient la source métier des constructeurs, éditeurs logiciels et supports tiers. Il est rattaché à `ItamOrganization` et consommé par les garanties, licences et contrats de support pour supprimer les fournisseurs texte libre dans les opérations critiques.

Principes conservés :

- domaine pur dans `openinfra.domain.itam` ;
- orchestration métier dans `openinfra.application.itam_services` ;
- persistance interchangeable via ports `ItamSupportRepository` ;
- JSON store et PostgreSQL compatibles ;
- API, CLI et portail web branchés sur le même service applicatif ;
- validation d’organisation active et de type partenaire avant création de garantie, licence ou support ;
- retrait logique non destructif.

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
