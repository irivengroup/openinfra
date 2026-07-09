## v0.29.76 — DCIM sites/dépendances, racks CRUD, pays ISO et libellés ITAM

- Extension du DCIM sites & dépendances avec cycle de vie complet des chassis/racks rattachés à site, bâtiment et salle.
- Ajout de la règle d’étage conditionnelle : étage obligatoire pour créer une salle uniquement si le bâtiment possède au moins un étage actif.
- Ajout de l’expansion contrôlée des plages de lignes et colonnes de salle, par exemple `0-12` et `A-F`, avec limite de 512 valeurs générées.
- Ajout des commandes CLI `dcim racks`, `dcim rack`, `dcim rack-update`, `dcim rack-delete` et des endpoints API correspondants.
- Ajout de la migration PostgreSQL `0033_dcim_site_dependencies_rack_lifecycle.sql` pour le statut de cycle de vie des racks et les index de consultation.
- Ajout du référentiel pays ISO-3166 alpha-2 groupé par continent via `GET /api/v1/reference/countries` et rendu web en `select` groupé.
- Réalignement UI ITAM : `Fournisseurs et Supports` devient `Partenaires`; `Tenant` devient `Filiale/Subdivision` sous le sous-menu `Organisations`, tout en conservant la compatibilité technique `tenant_id`.
- CDC et roadmap mis à jour avec `REQ-00817`, `TST-WEB-116` et `TST-P14-DCIM-SITE-DEPENDENCIES-RACKS-COUNTRIES`.

## v0.29.75 — Référentiel ITAM partenaires, fournisseurs et supports tiers

- Ajout du référentiel ITAM des partenaires rattachés à une organisation : constructeurs, éditeurs logiciels et supports tiers.
- Chaque partenaire exige une carte d’identité entreprise complète et au moins un contact téléphonique exploitable.
- Ajout du cycle de vie CRUD complet via domaine, services, JSON store, PostgreSQL, CLI, API, OpenAPI et portail web.
- Les garanties constructeur utilisent désormais un partenaire accrédité de type `manufacturer`.
- Les licences logicielles utilisent désormais un partenaire accrédité de type `software_publisher`.
- Les contrats de support tiers utilisent désormais un partenaire accrédité de type `third_party_support`.
- Les formulaires ITAM sont réalignés : les supports, garanties et licences sélectionnent l’organisation puis un partenaire compatible, sans fournisseur texte libre comme autorité métier.
- Ajout de la migration PostgreSQL unique `0032_itam_partner_registry.sql`, consolidant la table des partenaires et le rattachement licence fournisseur.
- CDC et roadmap mis à jour avec `REQ-00816`, `TST-WEB-115` et `TST-P14-ITAM-PARTNER-REGISTRY`.

## v0.29.74 — Formulaires ITAM racine et politique migrations minimale

- Correction UX : une organisation ITAM est une entité racine ; ses formulaires de création, modification et suppression n'affichent plus de sélecteur global Organisation/Tenant ni de tenant de sécurité.
- Réalignement des formulaires tenant : un tenant sélectionne uniquement son organisation parente puis le tenant cible lorsque l'opération modifie, consulte ou retire un tenant existant ; aucun tenant parent n'est proposé.
- Les opérations ITAM support/licences et les autres ressources conservent le couple Organisation → Tenant filtré, afin d'éviter toute ressource orpheline.
- Optimisation des migrations : aucune migration PostgreSQL supplémentaire n'est créée pour cette correction UI ; la migration `0031_itam_organization_identity.sql` reste conservée pour compatibilité ascendante.

## v0.29.73 — Organisations ITAM parent des tenants

- Ajout du référentiel Organisations ITAM avec carte d’identité entreprise complète.
- Rattachement obligatoire des tenants à une organisation active via `organization_id`.
- Ajout CLI/API/OpenAPI/web pour créer, consulter, lister, modifier et retirer logiquement les organisations.
- Ajout de la migration PostgreSQL `0031_itam_organization_identity.sql`.
- Ajout du tenant implicite : lorsqu’une organisation active n’a aucun tenant, elle peut être proposée puis matérialisée comme tenant opérationnel.
- Retrait logique d’une organisation avec cascade non destructive vers ses tenants.
- Realignement web : sélection Organisation avant Tenant, filtrage des tenants par organisation et suppression du libellé ambigu `Entité propriétaire`.
- Renforcement support/licences : aucune opération ITAM métier sans tenant actif rattaché à une organisation active.


## v0.29.71 — Hotfix CI edition feature-check data backend

- `openinfra edition feature-check` accepte les options backend homogènes, dont `--data`.
- Ajout d'un test de régression pour la séquence CI `edition list`, `feature-check` et `quota-check`.
