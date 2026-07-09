- 0.29.59 : ajout `TST-P13-BULK-IMPORT-ROLLBACK-CONFLICT-AWARE` pour couvrir le rollback conflict-aware des imports massifs appliqués, avec dry-run, restauration versionnée, mise en retrait non destructive et publication CLI/API/OpenAPI/discovery/web.
- 0.29.58 : ajout `TST-P25-ITSM-OPENSERVICE-FUTURE-CMDB-CONNECTOR` pour préparer OpenService comme ITSM/CMDB externe autonome, sans UI dans openinfra-web et sans ticketing natif.
- 0.29.57 : ajout `TST-P25-ITSM-GLPI-FRESHSERVICE-EXTERNAL-CONNECTORS` pour couvrir GLPI Inventory et Freshservice Assets comme connecteurs ITSM externes sans ticketing natif.
- 0.29.56 : ajout `TST-P25-ITSM-JIRA-ASSETS-EXTERNAL-CONNECTOR` pour couvrir Jira Service Management Assets comme connecteur ITSM externe sans ticketing natif.
- 0.29.56 : ajout `TST-P25-ITSM-SERVICENOW-EXTERNAL-CONNECTOR` pour couvrir les connecteurs ITSM externes ServiceNow, sans ticketing natif, et la correction thème Bootstrap `btn-primary`/statut runtime.
- 0.29.54 : ajout `TST-P13-ASYNC-EXPORT-STREAMING` pour couvrir EPIC-1302 avec API/CLI/UI de lecture chunkée des artefacts exportés signés.
## v0.29.51 — P12 ITAM licences logicielles et contrats

L’incrément v0.29.51 réalise `EPIC-1205` pour les licences logicielles : entitlements, référence contrat, quantités achetées/assignées, conformité à date, API, CLI, portail web, OpenAPI, migration PostgreSQL partitionnée et tests de non-régression via `TST-P12-ITAM-SOFTWARE-LICENSES`.

- v0.29.50 : P08/EPIC-0804 expose l’administration éditions et quotas dans le portail web et l’API, avec discovery/OpenAPI, RBAC `security:admin` et parité CLI/CI.
- v0.29.49 : P08/EPIC-0805 ajuste le badge édition avec un dégradé fuchsia très foncé tirant vers prune chaud/bruné sans devenir marron, tout en conservant le gabarit Bootstrap.
- v0.29.48 : P08/EPIC-0805 corrige le badge édition pour garantir un dégradé fuchsia effectif, sans héritage bleu `text-bg-primary`, tout en conservant le gabarit Bootstrap.
- v0.29.48 : P08/EPIC-0805 déplace le badge édition dans le header principal, retire le badge visible du mode d’authentification et applique un fond fuchsia dégradé sans changer le gabarit.
- v0.29.46 : P08/EPIC-0805 ajoute l’accessibilité critique openinfra-web : skip-link, états ARIA, recherche globale annonçable et focus contenu principal.
# OpenInfra — Roadmap de développement v2.0.0

Roadmap mise à jour pour alignement avec **OpenInfra CDC/SFG/STG v4.8.1 corrigé**.

## Contenu

- `01-roadmap-detaillee-openinfra-v2.md` : roadmap narrative complète.
- `02-roadmap-phases.csv` : 19 phases programme.
- `03-roadmap-releases.csv` : 9 releases macro.
- `04-roadmap-epics.csv` : 114 epics détaillés.
- `05-roadmap-jalons.csv` : jalons de pilotage.
- `06-roadmap-dependances.csv` : dépendances inter-phases.
- `07-roadmap-go-nogo.csv` : gates Go/No-Go.
- `08-roadmap-risques.csv` : risques et mitigations.
- `09-roadmap-tests-validation.csv` : tests et validations.
- `10-roadmap-streams.csv` : streams d’exécution.
- `11-plan-90-jours.md` : plan initial recalé sur v4.8.1.
- `12-plan-equipe-et-gouvernance.md` : gouvernance et équipe.
- `13-validation-roadmap.md` : preuve de validation documentaire.
- `14-alignement-cdc-v4.8.1.csv` : mapping CDC → roadmap.
- `15-plan-livraison-editions.csv` : plan Lite/Pro/Entreprise.
- `16-plan-installateurs.csv` : plan installateurs par scope.
- `17-plan-migration-pgdata-lvm.csv` : plan stockage, LVM, PGDATA.

## Décisions clés intégrées

- `openinfra.service` est le service backend canonique.
- `ancien service backend obsolète` est interdit.
- `openinfra-web.service` est le service frontend React + Bootstrap 5.
- `openinfra-agent.service` est le service collecteur discovery.
- Les installateurs sont dans `installers/`, hors `src/`.
- Chaque scope possède `config/install.ini`.
- PostgreSQL initialise ses données sous `/data/openinfra/`.
- `/opt/openinfra/data` pointe vers `/data/openinfra/`.
- Tailles PGDATA : Lite 2GB, Pro 100GB, Entreprise 1TB.
- Pro/Entreprise supportent LDAP/IPA, RBAC groupes, multisite et connecteurs ITSM externes.


### v0.29.32 — IPAM topologie opérationnelle

Ajout du test `TST-P11-IPAM-TOPOLOGY` pour verrouiller la consolidation nodes/edges IPAM par API, CLI, dashboard et OpenAPI.

### v0.29.35 — Discovery Enterprise proxy enrollment verification

- P11 ajoute `openinfra discovery proxy-enroll-verify` pour valider hors-ligne les fichiers d’enrôlement proxy Enterprise générés par `--config-output`.
- P08 simplifie le titre accueil en `Dashboard` et isole les métriques/statistiques d’accueil hors pages composants.
- La vérification couvre édition, schéma JSON, résultats backend, permissions POSIX et mode `--allow-partial`.

### v0.29.33 — Discovery Enterprise proxy CLI enrollment

Ajout du test `TST-P11-DISCOVERY-PROXY-CLI-ENROLLMENT` pour verrouiller l’enrôlement CLI local/distant des proxies Discovery Enterprise auprès des backends, avec refus Lite/Pro.
- v0.29.33 : P08 ajoute la charte graphique premium Bootstrap 5 openinfra-web, sans changement de structure page, validée par TST-P08-WEB-PREMIUM-THEME.

- 0.29.60 : ajout `TST-P13-DATA-MIGRATION-GUIDES` pour couvrir EPIC-1306 avec guides Device42/NetBox/Nautobot/GLPI/CSV exposés CLI/API/OpenAPI/discovery/web sans mutation RSOT.

- 0.29.61 : ajout `TST-P14-LOCAL-DISCOVERY-PLAN` pour couvrir EPIC-1401 avec plan discovery locale Lite/Pro sans agent, dry-run, secrets vault://, sans scan réseau exécuté et sans mutation RSOT.

### Validation v0.29.61 — panneau latéral groupé par contexte

La roadmap v2 ajoute `TST-P08-WEB-SIDEBAR-CONTEXT-GROUPS` pour verrouiller la navigation web contextuelle : tous les composants regroupent leurs opérations par contexte métier, les intégrations ITSM sont groupées par fournisseur, aucune opération existante n’est supprimée et OpenService reste absent du portail web OpenInfra.

- 0.29.62 : ajout `TST-P14-ITAM-TENANT-LIFECYCLE` pour couvrir le CRUD des tenants ITAM, le tenant par défaut unique, le retrait logique, le sélecteur web et l’auto-sélection mono-tenant.


### Validation v0.29.63 — plan bootstrap agent Enterprise

La livraison v0.29.63 ajoute `TST-P14-ENTERPRISE-AGENT-BOOTSTRAP` pour couvrir le contrat Enterprise `openinfra-agent.service`, le rendu systemd, la configuration agent, mTLS, les références `vault://`, les endpoints API de publication et l’absence d’installation ou de secret en clair.

### Validation v0.29.64 — UX tenants ITAM

La livraison v0.29.64 a introduit `TST-P14-ITAM-TENANT-UX-LABELS`, désormais réaligné : le portail distingue `Organisation` comme entreprise/groupe client et `Tenant` comme subdivision rattachée, sans libellé ambigu `Entité propriétaire`.
### Validation v0.29.65 — DCIM sites et responsive mobile

La livraison v0.29.65 ajoute `TST-P14-DCIM-SITE-LIFECYCLE-RESPONSIVE` pour couvrir le CRUD des sites DCIM, la cascade non destructive vers les dépendances, le catalogue hiérarchique, les sélecteurs obligatoires pour les références de localisation et l’optimisation responsive du portail.



### Validation v0.29.73 — Organisations ITAM parent des tenants

La roadmap v2 ajoute `TST-P14-ITAM-ORGANIZATION-IDENTITY` pour couvrir le référentiel organisations, la carte d’identité entreprise, le rattachement obligatoire tenant/support/licence, le filtrage UI Organisation → Tenant, le tenant implicite et la cascade de retrait logique.


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
