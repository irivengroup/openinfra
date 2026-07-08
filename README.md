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
