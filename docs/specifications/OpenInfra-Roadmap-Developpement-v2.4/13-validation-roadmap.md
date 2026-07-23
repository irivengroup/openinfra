## OpenInfra 0.29.93 — Validation documentaire

- `TST-P08-WEB-TYPED-VALIDATED-FORMS` verrouille calendriers, normalisation et validation amont dans React et le runtime packagé.
- `TST-P01-OPENAPI-UNIQUE-YAML-KEYS` refuse les clés YAML dupliquées et les versions OpenAPI invalides.
- `TST-P15-GRAPH-RSOT-NAVIGATION` vérifie l’absence de composant Graphe autonome et le rangement sous RSOT.
- Les changements sont mappés à `REQ-00826`, `REQ-00827` et `REQ-00828`.

## OpenInfra 0.29.88 — Accessibilité transversale et header raffiné

`EPIC-0805` applique désormais une baseline WCAG 2.2 AA à toutes les pages : liens d’évitement, landmarks, navigation clavier, lecteurs d’écran, annonces dynamiques, formulaires accessibles, contraste, couleurs forcées, réduction des mouvements et alternatives textuelles. Le header conserve sa densité mais adopte des états actif/hover translucides, des angles discrets, des transitions bounce/fade respectueuses des préférences utilisateur et des contrôles FR/EN-Swagger-ReDoc légèrement réduits.

## OpenInfra 0.29.87 — Ajustements header et mégamenu

`EPIC-0805` conserve les trois modes responsive mais précise que le mégamenu intermédiaire s’ouvre au survol ou au focus, avec clic de secours. La seconde barre retrouve son padding initial de `0,5 rem`; la recherche reste haute de `2 rem`, centrée et large de 50 %. Sur écran large, les composants restent compacts et alignés à droite avec des états actif, hover et focus contrastés.

### Validation v0.29.82 — Réconciliation Discovery multisource gouvernée

La roadmap réalise `EPIC-1405` via `TST-P14-DISCOVERY-MULTISOURCE-RECONCILIATION` : preuves immuables, scores reproductibles, conflits explicites par attribut, résolution complète et justifiée, audit, pagination, persistance JSON/PostgreSQL partitionnée et interdiction de toute mutation RSOT silencieuse.

## 0.29.52

L’incrément v0.29.52 réalise un jalon P13 / EPIC-1301 : progression opérable des imports massifs reprenables avec checkpoint, compteurs, CLI `openinfra import bulk-progress`, API `/api/v1/imports/bulk-progress`, OpenAPI/discovery et portail web.

## v0.29.51 — P12 ITAM licences logicielles et contrats

L’incrément v0.29.51 réalise `EPIC-1205` pour les licences logicielles : entitlements, référence contrat, quantités achetées/assignées, conformité à date, API, CLI, portail web, OpenAPI, migration PostgreSQL partitionnée et tests de non-régression via `TST-P12-ITAM-SOFTWARE-LICENSES`.

# Validation roadmap v2

## Synthèse

- Version roadmap : 2.0.0
- Référence CDC : OpenInfra CDC/SFG/STG v4.8.1 corrigé
- Phases : 19
- Releases : 9
- Epics : 115
- Gates Go/No-Go : 8
- Risques : 12
- Tests roadmap : 97
- Décisions CDC mappées : 97

## Contrôles attendus

Le script `scripts/validate_roadmap.py` vérifie :

- présence des fichiers obligatoires ;
- minimum de phases, epics, gates et tests ;
- présence des services canoniques ;
- absence de `ancien service backend obsolète` ;
- présence de `installers/`, `config/install.ini`, `/data/openinfra/`, `/opt/openinfra/data -> /data/openinfra/` ;
- présence des tailles PGDATA Lite/Pro/Entreprise ;
- présence de LDAP/IPA, RBAC, multisite et connecteurs ITSM externes ;
- absence de marqueurs de brouillon.
- `TST-P09-RSOT-TAXONOMY-LABELS` verrouille l’affichage des libellés opérateur, la conservation des valeurs internes et l’absence des types obsolètes `physical-server`/`disk`.


## Validation v0.29.31

La roadmap v2 intègre P11/IPAM Enterprise++ dashboard parity via TST-P11-IPAM-DASHBOARD-PARITY et l’alignement CDC REQ-00769.


### v0.29.32 — IPAM topologie opérationnelle

Ajout du test `TST-P11-IPAM-TOPOLOGY` pour verrouiller la consolidation nodes/edges IPAM par API, CLI, dashboard et OpenAPI.


### v0.29.35 — Discovery Enterprise proxy enrollment verification

- Ajout `TST-P11-DISCOVERY-PROXY-ENROLLMENT-VERIFY`.
- Alignement CDC `REQ-00773` et CLI Discovery `proxy-enroll-verify`.

### v0.29.33 — Discovery Enterprise proxy CLI enrollment

Ajout du test `TST-P11-DISCOVERY-PROXY-CLI-ENROLLMENT` pour verrouiller l’enrôlement CLI local/distant des proxies Discovery Enterprise auprès des backends, avec refus Lite/Pro.
- v0.29.33 : P08 ajoute la charte graphique premium Bootstrap 5 openinfra-web, sans changement de structure page, validée par TST-P08-WEB-PREMIUM-THEME.

### v0.29.35 — Dashboard court et contenu accueil isolé

- Ajout `TST-P08-WEB-DASHBOARD-SCOPING`.
- Alignement CDC `REQ-00774` et validation frontend/runtime : titre court `Dashboard`, métriques et statistiques d’accueil strictement limitées à la page overview.

### v0.29.35 — Ombres de contenu openinfra-web allégées

Validation attendue : `scripts/validate_frontend.py` et `tests/integration/test_openinfra_web.py` doivent contrôler les variables `--openinfra-content-shadow` et `--openinfra-content-shadow-hover`, ainsi que leur utilisation par les blocs de contenu.

### v0.29.36 — Alertes openinfra-web contextuelles uniquement

Validation attendue : `scripts/validate_frontend.py` et `tests/integration/test_openinfra_web.py` doivent interdire `alert alert-info` et `role="note"` dans les assets runtime, tout en conservant les alertes `success` strictement conditionnées à une soumission de formulaire.


## Validation v0.29.37

La roadmap v2 intègre P08/openinfra-web double barre et recherche globale via `TST-P08-WEB-GLOBAL-SEARCH-HEADER` et l’alignement CDC `REQ-00777`. La validation contextual alerts couvre aussi le retrait des messages permanents hérités des anciennes alertes.

## Validation v0.29.38

La roadmap v2 intègre P08/openinfra-web recherche globale backend via `TST-P08-WEB-BACKEND-GLOBAL-SEARCH` et l’alignement CDC `REQ-00778`. La validation couvre le service applicatif, l’API HTTP, la CLI et le fallback frontend.

## Validation v0.29.46 — accessibilité openinfra-web

La roadmap v2 intègre `TST-P08-WEB-ACCESSIBLE-NAVIGATION` pour verrouiller l’accessibilité du portail web sans modifier les contrats backend. L’alignement CDC ajoute `REQ-00789` sur P08 / EPIC-0805 / release 0.29.46.


## Validation v0.29.47 — badge édition header principal

La roadmap v2 intègre `TST-P08-WEB-EDITION-BADGE-HEADER` pour verrouiller le déplacement de l’édition runtime à côté du logo OpenInfra, le retrait de l’indication visible du mode d’authentification et le style fuchsia dégradé sans changement de gabarit Bootstrap. L’alignement CDC ajoute `REQ-00790` sur P08 / EPIC-0805 / release 0.29.47.

## Validation v0.29.48 — badge édition fuchsia effectif

La roadmap v2 intègre `TST-P08-WEB-EDITION-BADGE-FUCHSIA` pour verrouiller le rendu fuchsia effectif du badge d’édition, sans classe `text-bg-primary`, sans composante bleue dans le gradient dédié, et sans changement du gabarit Bootstrap `badge`. L’alignement CDC ajoute `REQ-00791` sur P08 / EPIC-0805 / release 0.29.48.


## Validation v0.29.49 — badge édition fuchsia très foncé

La roadmap v2 intègre `TST-P08-WEB-EDITION-BADGE-DARK-FUCHSIA` pour verrouiller le rendu fuchsia très foncé du badge d’édition, sans retour au bleu Bootstrap, à l’ancien fuchsia clair ou à une couleur marron explicite. L’alignement CDC ajoute `REQ-00792` sur P08 / EPIC-0805 / release 0.29.49.

## Validation v0.29.50 — administration éditions et quotas API/UI

La roadmap v2 intègre `TST-P08-WEB-EDITION-ADMIN-QUOTAS` pour verrouiller l’exposition opérateur des politiques d’édition, des feature gates et des quotas runtime. L’alignement CDC ajoute `REQ-00793` sur P08 / EPIC-0804 / release 0.29.50, avec validation discovery, OpenAPI, RBAC `security:admin`, portail web Sécurité/RBAC/Audit et CI CLI équivalente.

La roadmap v2 intègre `TST-P25-ITSM-OPENSERVICE-FUTURE-CMDB-CONNECTOR` pour préparer OpenService comme ITSM/CMDB externe futur. L’alignement CDC ajoute `REQ-00801` sur P25 / EPIC-2506 / release 0.29.58, avec validation domaine, service, CLI, API, OpenAPI, discovery et absence d’opération OpenService dans `openinfra-web`.

## Validation v0.29.59 — rollback conflict-aware imports massifs

La roadmap v2 intègre `TST-P13-BULK-IMPORT-ROLLBACK-CONFLICT-AWARE` pour verrouiller le rollback opérable des imports massifs appliqués. L’alignement CDC ajoute `REQ-00802` sur P13 / EPIC-1305 / release 0.29.59, avec validation service, CLI, API, OpenAPI, discovery, portail web, dry-run par défaut, restauration versionnée, mise en retrait sans suppression physique et blocage des conflits.

## Validation v0.29.60 — guides opérables de migration données

La roadmap v2 intègre `TST-P13-DATA-MIGRATION-GUIDES` pour verrouiller les guides structurés Device42, NetBox, Nautobot, GLPI et CSV. L’alignement CDC ajoute `REQ-00803` sur P13 / EPIC-1306 / release 0.29.60, avec validation domaine, service, CLI, API, OpenAPI, discovery, portail web et absence de mutation RSOT.

## Validation v0.29.61 — discovery locale Lite/Pro sans agent

La roadmap v2 intègre `TST-P14-LOCAL-DISCOVERY-PLAN` pour verrouiller le plan discovery locale Lite/Pro. L’alignement CDC ajoute `REQ-00804` sur P14 / EPIC-1401 / release 0.29.61, avec validation domaine, service, CLI, API, OpenAPI, discovery, portail web, dry-run, absence de scan réseau exécuté et absence de mutation RSOT.

### Validation v0.29.61 — panneau latéral groupé par contexte

La roadmap v2 ajoute `TST-P08-WEB-SIDEBAR-CONTEXT-GROUPS` pour verrouiller la navigation web contextuelle : tous les composants regroupent leurs opérations par contexte métier, les intégrations ITSM sont groupées par fournisseur, aucune opération existante n’est supprimée et OpenService reste absent du portail web OpenInfra.


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

PASS — Les coordonnées site/organisation/partenaire, le code postal obligatoire et le comportement pays sont validés par tests ciblés et migration 0036.


### Validation v0.29.81 — Profils Discovery virtualisation, Kubernetes et cloud

La roadmap intègre `TST-P14-DISCOVERY-INTEGRATION-PROFILES` pour couvrir EPIC-1404 : profils VMware, Proxmox, Hyper-V, Kubernetes, AWS, Azure, GCP et OpenStack sécurisés, secrets `vault://` masqués, endpoints HTTPS contrôlés, limites de débit/concurrence actives, CRUD service/CLI/API/web et migration PostgreSQL `0037_discovery_integration_profiles.sql` sans scan réseau ni mutation RSOT.

## Validation v0.29.86 — Navigation responsive adaptative

La roadmap renforce `EPIC-0805` avec `TST-P08-WEB-RESPONSIVE-NAVIGATION` et `TST-P08-WEB-COMPACT-HEADER`. La validation couvre sidebar desktop, mégamenu contextuel intermédiaire, menu compact mobile, parité complète des opérations, clavier et tactile, header à hauteur initiale, recherche compacte, contrôles alignés et ombre du header supérieure aux blocs de contenu. L'alignement CDC référence `REQ-00811` et `REQ-00825`.

## Validation 2.3.0

La roadmap 2.3.0 est valide uniquement avec 24 phases, 14 releases, 141 epics, 16 jalons, 13 gates, 125 tests et 138 lignes d’alignement CDC 4.10.0. Tous les CSV doivent être structurellement valides, sans colonne anonyme. GATE-12 doit couvrir exactement les sept preuves de la politique REL-13 et maintenir une couverture globale minimale de 98 %.

## OpenInfra 0.34.6 — Canonicalisation RSOT définitive

P24 / REL-14 supprime les alias ITRM, RI et SOT et impose GATE-13 avec six preuves fermées, sans suppression de capacité métier RSOT.
