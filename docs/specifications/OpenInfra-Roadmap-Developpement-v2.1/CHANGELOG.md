## 2.1.0 / CDC 4.9.0 / OpenInfra 0.30.0

- Ajout P19 et P20, REL-09 et REL-10, GATE-08 et GATE-09.
- Priorité immédiate au runtime ASGI, pooling PostgreSQL/HTTP et streaming BFF.
- Séquencement professionnel de PgBouncer, read replicas, curseurs, outbox/workers et frontend modulaire.
- Ajout des risques de saturation, lag replica, faux asynchronisme et microservices prématurés.
- Alignement explicite de REQ-00829 à REQ-00840.

## OpenInfra 0.29.93 — Formulaires typés, OpenAPI strict et rangement RSOT

- Renforcement de `EPIC-0805` : calendriers natifs thémés, normalisation ISO 8601, validation amont des saisies libres et focus sans épaississement de contour.
- Renforcement de `EPIC-0102` et `EPIC-0104` : parseur OpenAPI strict refusant toute clé YAML dupliquée dans la CI et avant packaging.
- Réalignement de `EPIC-1505` : le Graphe n’est plus présenté comme composant autonome et reste rangé sous RSOT.
- Ajout de `REQ-00826`, `REQ-00827`, `REQ-00828` et de leurs validations de non-régression.

## OpenInfra 0.29.88 — Accessibilité transversale et header raffiné

- Renforcement de `EPIC-0805` sans nouvel epic.
- Réalignement de `REQ-00789` et `REQ-00825` sur la release 0.29.88.
- Extension de `TST-P08-WEB-ACCESSIBLE-NAVIGATION` à toutes les pages et aux technologies d’assistance.
- Mise à jour de `TST-P08-WEB-COMPACT-HEADER` pour les états translucides, les faibles rayons, les transitions adaptatives et les contrôles réduits.

## OpenInfra 0.29.87 — Ajustements header et mégamenu

- Réalignement de `EPIC-0805` sur l’ouverture hover/focus du mégamenu avec clic de secours.
- Restauration de la hauteur initiale de la seconde barre, recherche 50 % centrée et composants compacts à droite.
- Mise à jour des validations existantes `TST-P08-WEB-RESPONSIVE-NAVIGATION` et `TST-P08-WEB-COMPACT-HEADER`.

## OpenInfra 0.29.86 — Navigation responsive adaptative et header compact

- EPIC-0805 est renforcé par trois modes de navigation sans perte fonctionnelle : sidebar desktop, mégamenu contextuel intermédiaire et menu compact mobile.
- Ajout de `TST-P08-WEB-RESPONSIVE-NAVIGATION` et `TST-P08-WEB-COMPACT-HEADER`.
- Alignement de `REQ-00811` et ajout de `REQ-00825` sur P08 / EPIC-0805.

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
