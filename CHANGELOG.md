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
