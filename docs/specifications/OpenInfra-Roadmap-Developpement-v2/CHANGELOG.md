## OpenInfra 0.29.85 — Réalignement UX/DCIM

- Ajout d’EPIC-0807 pour l’internationalisation complète du portail FR/EN.
- Ajout du gate TST-P08-WEB-I18N-FR-EN.
- Réalignement du test DCIM des étages sur la nomenclature locale `L-01`, `L00`, `L01` et la migration 0040.
- Ajout de l’alignement REQ-00824 vers EPIC-0807.

### Validation v0.29.82 — Réconciliation Discovery multisource gouvernée

La roadmap réalise `EPIC-1405` via `TST-P14-DISCOVERY-MULTISOURCE-RECONCILIATION` : preuves immuables, scores reproductibles, conflits explicites par attribut, résolution complète et justifiée, audit, pagination, persistance JSON/PostgreSQL partitionnée et interdiction de toute mutation RSOT silencieuse.

## v0.29.72 — DCIM dépendances CRUD topologiques

- Ajout `TST-P10-DCIM-DEPENDENCY-CRUD` pour verrouiller la gestion explicite des bâtiments, étages, salles et zones.
- Alignement avec `REQ-00813` du CDC v4.8.1.

## v0.29.71 — compatibilité CLI/CI des commandes édition

- Ajout `TST-P08-CLI-EDITION-DATA-COMPAT`.


### Validation v0.29.74 — Formulaires ITAM racine et migrations minimales

La roadmap intègre `TST-P14-ITAM-FORM-HIERARCHY-MIGRATION-MINIMAL` : les formulaires Organisation sont racine, les formulaires Tenant n'ont pas de tenant parent, les ressources restent rattachées au couple Organisation → Tenant filtré et aucune migration PostgreSQL supplémentaire n'est créée pour un correctif UI.

La roadmap intègre `TST-P14-ITAM-PARTNER-REGISTRY` : ITAM gère les fournisseurs, éditeurs logiciels et supports tiers comme partenaires accrédités par organisation, avec carte d’identité entreprise complète, téléphone obligatoire, cycle de vie CRUD et usage obligatoire dans les formulaires garanties, licences et supports.


### Validation v0.29.79 — Profils protocoles Discovery SNMP/SSH/WinRM

La roadmap intègre `TST-P14-DISCOVERY-PROTOCOL-PROFILES` pour couvrir EPIC-1403 : profils SNMP/SSH/WinRM sécurisés, secrets `vault://` masqués, WinRM non chiffré refusé, limites de débit/concurrence actives, CRUD service/CLI/API/web et liaison des plans discovery locaux à un profil sans scan réseau ni mutation RSOT.


### Validation v0.29.79 — DCIM bâtiments typés et étages générés

- Ajout du type bâtiment Simple/Etages avec niveaux bornés.
- Génération interne des codes et noms d'étages.
- Retrait des opérations d'administration manuelle des étages dans l'UI.
- Correction des selects Pays : valeur alpha2, libellé nom seul.

### Validation v0.29.80 — Adresse complète sites, organisations et partenaires

- Ajout des coordonnées complètes aux sites DCIM.
- Ajout du code postal et du téléphone aux organisations ITAM.
- Ajout du code postal aux partenaires ITAM.
- Correction UI Pays : nom affiché seul, alpha2 conservé en valeur.


### Validation v0.29.81 — Profils Discovery virtualisation, Kubernetes et cloud

La roadmap intègre `TST-P14-DISCOVERY-INTEGRATION-PROFILES` pour couvrir EPIC-1404 : profils VMware, Proxmox, Hyper-V, Kubernetes, AWS, Azure, GCP et OpenStack sécurisés, secrets `vault://` masqués, endpoints HTTPS contrôlés, limites de débit/concurrence actives, CRUD service/CLI/API/web et migration PostgreSQL `0037_discovery_integration_profiles.sql` sans scan réseau ni mutation RSOT.
