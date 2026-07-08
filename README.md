# OpenInfra v0.29.73

## v0.29.73 — Organisations ITAM parent des tenants

OpenInfra v0.29.73 réaligne le modèle ITAM autour d’un référentiel **Organisations** : l’organisation représente l’entreprise, le groupe ou l’entité juridique cliente ; le tenant représente une subdivision rattachée à cette organisation, par exemple `organisation=Orange` et `tenant=DSI`.

La création d’une organisation exige une carte d’identité entreprise complète : code organisation, raison sociale, nom d’usage, numéro d’immatriculation, identifiant fiscal, pays ISO 3166-1 alpha-2, ville, adresse siège, email de contact, contact support, statut et description. Les tenants, supports et licences ne peuvent plus être opérés sans tenant actif rattaché à une organisation active.

### Surfaces exposées

- Domaine : `ItamOrganization`, `ItamOrganizationStatus`, `ItamOrganizationCatalog` et rattachement `ItamTenant.organization_id`.
- Service applicatif : CRUD organisations, validation d’organisation active, tenant implicite lorsque l’organisation n’a aucun tenant et cascade de retrait logique des tenants.
- Persistance : JSON store et PostgreSQL avec migration `0031_itam_organization_identity.sql`.
- CLI : `openinfra itam organizations`, `organization`, `organization-create`, `organization-update`, `organization-delete`.
- API : `/api/v1/itam/organizations`, `/organization`, `/organization/create`, `/organization/update`, `/organization/delete`.
- Web : sélection Organisation avant Tenant, filtrage des tenants par organisation, proposition du tenant implicite et suppression du libellé ambigu `Entité propriétaire`.

### Garde-fous

- Aucun tenant ne peut être créé sans organisation active.
- Les supports et licences vérifient l’existence d’un tenant actif rattaché à une organisation active.
- Le retrait d’une organisation est non destructif et retire logiquement les tenants rattachés.
- Une organisation de compatibilité `default` est matérialisée pour préserver les installations mono-tenant existantes.
- Les anciens contrats `tenant_id` restent compatibles ; l’organisation devient le référentiel métier parent.

## v0.29.65 — DCIM sites, dépendances et responsive mobile

OpenInfra v0.29.65 ajoute un référentiel DCIM des sites avec cycle de vie CRUD, retrait logique et cascade non destructive vers les dépendances de localisation connues. Le portail web expose les sites et le catalogue hiérarchique DCIM pour alimenter les formulaires par listes déroulantes : les champs `site`, `building`, `floor`, `room`, `zone`, `rack`, `row` et `column` ne sont plus rendus en saisie libre dans les formulaires métier.

La même livraison optimise `openinfra-web` pour les tablettes et smartphones : sidebar responsive, hauteur bornée sur écrans intermédiaires, blocs plus compacts, formulaires adaptatifs et actions API mieux empilées sur mobile.

### Surfaces exposées

- Domaine : statuts de cycle de vie DCIM `active`, `suspended`, `retired` pour site, bâtiment, étage, salle et zone.
- Service applicatif : CRUD site et catalogue de topologie DCIM.
- Persistance : JSON store et PostgreSQL avec migration `0030_dcim_site_lifecycle.sql`.
- CLI : `openinfra dcim sites`, `site`, `site-create`, `site-update`, `site-delete`, `topology-catalog`.
- API : `/api/v1/dcim/sites`, `/site`, `/site/create`, `/site/update`, `/site/delete`, `/topology-catalog`.
- Web : groupe **Sites & dépendances** et sélecteurs DCIM obligatoires pour les références de localisation.

### Garde-fous

- Aucune suppression physique lors du retrait d’un site.
- Les dépendances bâtiment/étage/salle/zone sont retirées logiquement avec le site.
- Les références DCIM côté web sont sélectionnées depuis le catalogue backend, avec option courante conservée si le catalogue est temporairement vide.
- Le responsive n’altère pas les contrats API ni la sidebar contextuelle existante.


## v0.29.64 — UX tenants ITAM, remplacée par v0.29.73

La livraison v0.29.64 avait introduit une première correction UX autour des tenants. Ce comportement est désormais remplacé par le modèle v0.29.73 : **Organisation** représente l’entreprise, le groupe ou l’entité juridique cliente ; **Tenant** représente une subdivision interne rattachée. Les formulaires actifs exposent donc Organisation puis Tenant, avec filtrage des tenants par organisation et tenant implicite lorsqu’une organisation active ne dispose encore d’aucun tenant.

## v0.29.62 — référentiel tenants ITAM

OpenInfra v0.29.62 ajoute un référentiel ITAM des tenants avec cycle de vie CRUD, sélection opérateur dans les formulaires web et choix automatique lorsqu’un seul tenant actif existe. La fonctionnalité reste non destructive : la suppression logique retire le tenant sans effacer l’historique ni les audits.

### Surfaces exposées

- Domaine : `ItamTenant`, `ItamTenantStatus`, `ItamTenantCatalog`.
- Service applicatif : `ItamSupportService.create_tenant`, `update_tenant`, `delete_tenant`, `get_tenant`, `list_tenants`.
- Persistance : JSON store et PostgreSQL avec migration `0029_itam_tenant_lifecycle.sql`.
- CLI : `openinfra itam tenants`, `tenant`, `tenant-create`, `tenant-update`, `tenant-delete`.
- API : `/api/v1/itam/tenants`, `/api/v1/itam/tenant`, `/api/v1/itam/tenant/create`, `/api/v1/itam/tenant/update`, `/api/v1/itam/tenant/delete`.
- Web : champ tenant global rendu en `select` dès que le catalogue ITAM est disponible ; fallback select conservé avec option courante si le backend est indisponible.

### Garde-fous

- Un seul tenant actif peut être marqué par défaut à un instant donné.
- Un tenant retiré ou suspendu ne peut pas être défini comme tenant par défaut.
- Si un seul tenant actif existe, il est sélectionné automatiquement dans les formulaires.
- Le retrait est logique (`status=retired`) et non destructif.
- Les formulaires existants conservent leur contrat et bénéficient du sélecteur tenant sans changement d’API publique.

## v0.29.61 — discovery locale Lite/Pro sans agent

OpenInfra v0.29.61 ouvre P14 / EPIC-1401 avec une brique de discovery locale pour les éditions Lite et Pro. Cette livraison génère un plan opérable, sécurisé et revu par l’opérateur, sans scan réseau réel, sans agent proxy, sans écriture RSOT automatique et sans secret en clair.

### Surfaces exposées

- Domaine : `LocalDiscoveryPlan`, `LocalDiscoveryJobPlan`, `LocalDiscoveryProtocol`, `LocalDiscoveryTarget`.
- Service applicatif : `DiscoveryCollectorService.build_local_discovery_plan`.
- CLI : `openinfra discovery local-plan`.
- API : `POST /api/v1/discovery/local-plan`.
- Discovery/OpenAPI : contrat publié sous `discovery.local_plan`.
- Web : opération **Plan discovery locale Lite/Pro** dans le composant **Discovery**.
- Web UX : panneau latéral groupé par contextes fonctionnels sous chaque composant, sans suppression d’opération existante.

### Navigation web par contexte

Le panneau latéral regroupe désormais les opérations de tous les composants par contexte métier : référentiel, adressage IP, réseau L2/L3, connectivité, énergie/refroidissement, support matériel, licences logicielles, discovery locale/agents Enterprise, imports/migration/exports, connecteurs ITSM et sécurité.

Pour **Intégrations externes**, les actions sont regroupées par fournisseur : ServiceNow, Jira Assets, GLPI Inventory et Freshservice Assets. OpenService reste volontairement absent du portail `openinfra-web`, car sa future interface sera portée par OpenService.

### Garde-fous

- Disponible uniquement pour les runtimes `lite` et `pro`.
- Mode plan-only/dry-run systématique.
- Aucun agent proxy requis.
- Aucun scan réseau exécuté pendant la génération du plan.
- Aucune écriture RSOT automatique.
- Secrets uniquement sous forme de référence `vault://...`.
- Concurrence et rate limit explicitement bornés.

# OpenInfra v0.29.59

## v0.29.59 — rollback conflict-aware des imports massifs

OpenInfra v0.29.59 complète l’exploitation des imports massifs avec un rollback opérable, auditables et non destructif. Un import massif appliqué peut être rejoué en mode planification pour produire les actions de rollback, puis appliqué explicitement si aucun conflit bloquant n’est détecté.

### Surfaces exposées

- Service applicatif : `GenericImportService.bulk_import_rollback`.
- CLI : `openinfra import bulk-rollback`.
- API : `POST /api/v1/imports/bulk-rollback`.
- Discovery/OpenAPI : contrat publié sous `imports.bulk_rollback`.
- Web : opération **Rollback import massif** dans le composant **Imports / Exports**.

### Garde-fous

- Dry-run par défaut côté CLI/API.
- Aucun hard delete : les objets créés par import sont mis en retrait avec `status=retired`.
- Les objets déjà existants sont restaurés par nouvelle révision RSOT depuis le snapshot précédent.
- Les modifications concurrentes sont bloquées par défaut (`conflict_policy=fail`) ou ignorables explicitement (`conflict_policy=skip`).
- Le rollback relit le dataset source et le checkpoint persistant pour limiter l’annulation aux lignes réellement traitées.

## v0.29.58 — préparation connecteur futur OpenService CMDB

OpenInfra v0.29.58 prépare les briques d’intégration pour **OpenService**, solution ITSM autonome future disposant de sa propre interface web. OpenInfra ne développe pas OpenService et n’ajoute aucune fonctionnalité de ticketing natif : il expose uniquement les contrats backend/API, CLI, discovery et OpenAPI nécessaires au raccordement futur Pro/Enterprise.

### Surfaces OpenService préparées

- Domaine : fournisseur `openservice` avec alias contrôlés `open-service`, `openservice-cmdb`, `openservice-itsm`.
- Service application : validation de profil OpenService et plan déterministe de synchronisation CMDB depuis RSOT.
- CLI :
  - `openinfra integrations openservice-validate`
  - `openinfra integrations openservice-cmdb-sync-plan`
- API :
  - `POST /api/v1/integrations/itsm/openservice/validate`
  - `POST /api/v1/integrations/itsm/openservice/cmdb-sync-plan`
- Discovery/OpenAPI : endpoints publiés pour consommation par OpenService ou outils d’intégration.
- Web : aucune opération OpenService n’est ajoutée à `openinfra-web`; l’interface opérateur appartient à OpenService.

### Garde-fous OpenService

- OpenService est traité comme produit autonome externe, non inclus dans OpenInfra.
- Le CDC OpenService futur pourra préciser son modèle sans migration lourde côté OpenInfra.
- Les secrets restent uniquement des références `auth_secret_ref`.
- Les URL doivent être HTTPS et sans credentials embarqués.
- `native_ticketing_enabled` reste `false`.
- `openinfra_web_ui_enabled` vaut `false` pour OpenService.

## v0.29.57 — connecteurs externes GLPI Inventory et Freshservice Assets

OpenInfra v0.29.57 complète les connecteurs ITSM externes P13 avec **GLPI Inventory** et **Freshservice Assets**, sans introduire de ticketing natif OpenInfra. Les contrats ServiceNow et Jira Service Management Assets restent inchangés.

### Surfaces GLPI/Freshservice ajoutées

- CLI :
  - `openinfra integrations glpi-validate`
  - `openinfra integrations glpi-asset-sync-plan`
  - `openinfra integrations freshservice-validate`
  - `openinfra integrations freshservice-asset-sync-plan`
- API :
  - `POST /api/v1/integrations/itsm/glpi/validate`
  - `POST /api/v1/integrations/itsm/glpi/asset-sync-plan`
  - `POST /api/v1/integrations/itsm/freshservice/validate`
  - `POST /api/v1/integrations/itsm/freshservice/asset-sync-plan`
- Web : composant **Intégrations externes** avec opérations GLPI Inventory et Freshservice Assets.
- OpenAPI/discovery : contrats publiés sous `integrations.glpi_*` et `integrations.freshservice_*`.

### Garde-fous

- OpenInfra ne crée aucun ticket, incident, demande ou changement ITSM natif.
- Les secrets GLPI/Freshservice sont référencés par `auth_secret_ref` et ne sont jamais fournis en clair.
- Les URL d’instance doivent être HTTPS et ne peuvent pas contenir d'identifiants embarqués.
- `native_ticketing_enabled` reste systématiquement `false`.

# OpenInfra v0.29.56

## v0.29.56 — connecteur externe Jira Service Management Assets

OpenInfra v0.29.56 étend les intégrations ITSM externes avec **Jira Service Management Assets**, sans introduire de ticketing natif OpenInfra. Les contrats ServiceNow livrés précédemment restent inchangés.

### Surfaces Jira ajoutées

- CLI :
  - `openinfra integrations jira-validate`
  - `openinfra integrations jira-asset-sync-plan`
- API :
  - `POST /api/v1/integrations/itsm/jira/validate`
  - `POST /api/v1/integrations/itsm/jira/asset-sync-plan`
- Web : composant **Intégrations externes** avec opérations Jira Assets.
- OpenAPI/discovery : chemins publiés.

### Garde-fous

- OpenInfra ne crée aucun ticket, incident, demande ou changement ITSM natif.
- Les secrets Jira sont référencés par `auth_secret_ref` et ne sont jamais fournis en clair.
- Les URL Jira doivent être HTTPS et ne peuvent pas contenir d'identifiants embarqués.
- Les types d’objets Assets sont bornés : `object`, `server`, `network_device`, `computer`, `software`.
- Les mappings exigent au minimum `resource_key`, `display_name` et `resource_type`.


## v0.29.56 — connecteur externe ServiceNow + corrections thème Bootstrap

OpenInfra v0.29.56 ajoute les premiers contrats d'intégration **ITSM externe ServiceNow** sans introduire de ticketing natif : politiques de connecteurs, validation de profil ServiceNow et plan déterministe de synchronisation CI depuis RSOT vers une table CMDB externe.

Cette livraison corrige aussi les ajustements UI issus de v0.29.54 :

- les boutons de soumission restent des boutons Bootstrap 5 standards `btn btn-primary` ;
- la classe dédiée `openinfra-submit-btn` est supprimée ;
- `.btn-primary` est surchargée dans le thème OpenInfra avec le turquoise `#24d8ab` et ses états `hover`, `active`, `focus-visible`, `disabled` ;
- le bloc runtime `openinfra-runtime-status` ne reçoit plus de fond, bordure ni padding ajoutés ; seul son texte, y compris les valeurs `<strong>`, utilise le bleu `#003D8F`.

### Surfaces ServiceNow ajoutées

- CLI :
  - `openinfra integrations itsm-providers`
  - `openinfra integrations servicenow-validate`
  - `openinfra integrations servicenow-ci-sync-plan`
- API :
  - `GET /api/v1/integrations/itsm/providers`
  - `POST /api/v1/integrations/itsm/servicenow/validate`
  - `POST /api/v1/integrations/itsm/servicenow/ci-sync-plan`
- Web : composant **Intégrations externes** avec opérations ServiceNow.
- OpenAPI/discovery : chemins publiés.

### Garde-fous

- OpenInfra ne crée aucun ticket, incident, demande ou changement ITSM natif.
- Les secrets ServiceNow sont référencés par `auth_secret_ref` et ne sont jamais fournis en clair.
- Les URL d'instance ServiceNow doivent être HTTPS et ne peuvent pas contenir d'identifiants embarqués.
- Les mappings CI exigent au minimum `resource_key`, `display_name` et `resource_type`.

### Validations recommandées

```bash
ruff format --check src tests scripts docker
ruff check src tests scripts docker
python -m compileall -q src tests scripts docker installers
PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
PYTHONPATH=src:. python -m openinfra version
PYTHONPATH=src:. pytest --collect-only --no-cov
PYTHONPATH=src:. pytest tests/unit tests/architecture --no-cov
PYTHONPATH=src:. pytest tests/integration --no-cov
PYTHONPATH=src:. coverage report --fail-under=98
PYTHONPATH=src:. python scripts/quality_gate.py --project-root .
```

---
### v0.29.53 — exports massifs streaming par chunks signés

- Ajout `openinfra export artifact-chunk` pour lire un artefact exporté signé par offset/taille bornée.
- Ajout `GET /api/v1/exports/artifact-chunk` retournant `content_base64`, `chunk_sha256`, `next_offset`, `final_chunk` et métadonnées d’artefact après vérification SHA-256 + HMAC-SHA256 complète.
- Ajout de l’opération portail `Imports / Exports > Chunk export signé`.
- OpenAPI, discovery, CDC et roadmap alignés sur P13 / EPIC-1302.
- Non-régression : le téléchargement complet `/api/v1/exports/artifact` et `openinfra export artifact` restent inchangés.

## Historique des incréments récents


## v0.29.52 — progression opérable des imports massifs reprenables

OpenInfra v0.29.52 ajoute un incrément P13 / EPIC-1301 dédié à l’exploitation des imports massifs : un opérateur peut consulter l’état d’avancement d’un job bulk sans relire le fichier source et sans recalculer le rapport complet.



### Points clés

- Lecture d’un checkpoint bulk existant par `tenant` et `job_id`.
- Exposition des compteurs opérationnels : ligne suivante, lignes traitées, lignes valides/invalides, créations, mises à jour et batches terminés.
- Indication explicite de reprise possible avec `resumable`.
- Indication explicite de disponibilité du rapport final avec `final_report_available`.
- Conservation de la compatibilité ascendante : `bulk-dataset`, `bulk-report` et `bulk-checkpoint` restent inchangés.
- Publication dans le discovery document et dans OpenAPI.
- Ajout d’une entrée web **Imports / Exports** pour consulter la progression depuis le portail.
- Ajout d’un smoke CI JSON et de tests de non-régression CLI/API/web/service.

### API ajoutée

```http
GET /api/v1/imports/bulk-progress?tenant_id=default&job_id=<job-id>
```

Réponse type :

```json
{
  "job_id": "<job-id>",
  "tenant_id": "default",
  "status": "validated",
  "next_row_number": 3,
  "processed_rows": 2,
  "valid_rows": 2,
  "invalid_rows": 0,
  "create_count": 2,
  "update_count": 0,
  "batches_completed": 2,
  "resumable": true,
  "final_report_available": true
}
```

### CLI ajoutée

```bash
openinfra import bulk-progress \
  --data ./state.json \
  --tenant default \
  --job-id "$JOB_ID"
```

### Validations recommandées

```bash
python -m compileall -q src tests scripts docker installers
PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
PYTHONPATH=src:. python -m openinfra.interfaces.cli version
PYTHONPATH=src:. pytest --collect-only --no-cov
PYTHONPATH=src:. pytest tests/integration/test_import_services.py tests/integration/test_cli_import.py tests/integration/test_http_api.py tests/integration/test_openinfra_web.py --no-cov
PYTHONPATH=src:. coverage run --parallel-mode -m pytest tests/unit tests/architecture --no-cov
PYTHONPATH=src:. coverage run --parallel-mode -m pytest tests/integration --no-cov
PYTHONPATH=src:. coverage combine
PYTHONPATH=src:. coverage report --fail-under=98
PYTHONPATH=src:. python scripts/quality_gate.py --project-root .
```


## v0.29.63 — Enterprise agent bootstrap plan

OpenInfra prepares Enterprise discovery agents through `openinfra discovery agent-bootstrap-plan` and `POST /api/v1/discovery/agent-bootstrap-plan`. The contract renders an operator-reviewed `openinfra-agent.service` systemd unit, an agent configuration document, mTLS requirements, vault-only enrollment references and API result publication endpoints. No installation is executed and no secret is materialized by OpenInfra during plan generation.
