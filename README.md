# OpenInfra v0.29.54

## v0.29.54 — renommage ITRM en RSOT et correction Ruff/UI

OpenInfra v0.29.54 rend **RSOT (Ressource Source of Truth)** canonique à la place de l’ancien composant public **ITRM (IT Ressource Management)**. Les surfaces publiques utilisent désormais `rsot` : CLI, API HTTP, OpenAPI, discovery, portail web, recherche globale, rôles RBAC et documentation.

Les alias historiques `itrm`, `sot` et `ri` restent disponibles uniquement pour compatibilité ascendante, sont documentés comme dépréciés, et doivent être retirés progressivement des automatisations clientes au profit de `rsot`.

### Points clés

- Commande canonique : `openinfra rsot`.
- API canonique : `/api/v1/rsot/*`.
- Composant web canonique : **RSOT**.
- Groupes de recherche globale : `rsot`.
- Rôles RBAC canoniques : `rsot:reader`, `rsot:operator`, `rsot:governance-admin`.
- Capability canonique : `core_rsot`.
- Alias dépréciés conservés : `openinfra itrm`, `openinfra sot`, `openinfra ri`, `/api/v1/itrm/*`, `/api/v1/sot/*`, `/api/v1/ri/*`.
- Bloc statut runtime web rendu en bleu léger et discret.
- Boutons de soumission des formulaires web rendus en bleu turquoise dédié, distinct de Bootstrap `primary`.
- Correction Ruff : `ruff format --check src tests scripts docker` repasse sans reformater de fichier.

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
