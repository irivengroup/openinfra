# Rollback conflict-aware des imports massifs

## Objectif

OpenInfra v0.29.59 ajoute un rollback opérable pour les imports massifs appliqués. Le mécanisme annule les effets d’un import traité jusqu’à son checkpoint persistant, sans suppression physique des objets RSOT.

## Principes

- Le rollback est en dry-run par défaut.
- Le dataset source est relu avec le même mapping que l’import initial.
- Seules les lignes réellement traitées avant le checkpoint sont prises en compte.
- Un objet créé par l’import est mis en retrait avec `status=retired`.
- Un objet existant avant l’import est restauré par nouvelle révision depuis le snapshot précédent.
- Une modification concurrente est détectée lorsque l’objet courant ne correspond plus à l’état attendu après import.
- La politique `fail` bloque l’opération dès qu’un conflit existe ; la politique `skip` ignore uniquement les objets conflictuels.

## CLI

Planifier sans mutation :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli import bulk-rollback   --data .openinfra.json   --tenant default   --actor operator   --admin-token "$OPENINFRA_TOKEN"   --job-id "$IMPORT_JOB_ID"   --file /var/lib/openinfra/imports/bulk.csv   --format csv   --mapping-json '{"key":"asset_key","kind":"kind","display_name":"name","source":"source"}'
```

Appliquer explicitement après validation du plan :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli import bulk-rollback   --data .openinfra.json   --tenant default   --actor operator   --admin-token "$OPENINFRA_TOKEN"   --job-id "$IMPORT_JOB_ID"   --file /var/lib/openinfra/imports/bulk.csv   --format csv   --mapping-json '{"key":"asset_key","kind":"kind","display_name":"name","source":"source"}'   --apply
```

Ignorer les objets modifiés après import :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli import bulk-rollback   --data .openinfra.json   --tenant default   --actor operator   --admin-token "$OPENINFRA_TOKEN"   --job-id "$IMPORT_JOB_ID"   --file /var/lib/openinfra/imports/bulk.csv   --format csv   --mapping-json '{"key":"asset_key","kind":"kind","display_name":"name","source":"source"}'   --conflict-policy skip   --apply
```

## API

```http
POST /api/v1/imports/bulk-rollback
Content-Type: application/json
```

```json
{
  "tenant_id": "default",
  "actor": "operator",
  "admin_token": "${OPENINFRA_TOKEN}",
  "job_id": "<import-job-id>",
  "file_path": "/var/lib/openinfra/imports/bulk.csv",
  "format": "csv",
  "apply": false,
  "conflict_policy": "fail",
  "mapping": {
    "key": "asset_key",
    "kind": "kind",
    "display_name": "name",
    "source": "source"
  }
}
```

Réponse attendue : rapport de rollback avec `planned_count`, `applied_count`, `blocked_count`, `skipped_count` et la liste des actions par ligne.

## Sécurité et audit

- Permission requise : `rsot.write`.
- Les opérations appliquées sont tracées par audit `import.bulk_rollback.<status>`.
- Le mécanisme n’accepte pas le rollback d’un import massif exécuté en dry-run.
- Le rollback ne supprime jamais physiquement un objet RSOT.

## Validations ciblées

```bash
PYTHONPATH=src python -m pytest -q   tests/integration/test_import_services.py   tests/integration/test_cli_import.py   tests/integration/test_http_api.py::TestHttpApi::test_bulk_import_rollback_api_endpoint   -o addopts=''

python scripts/validate_frontend.py --project-root .
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
```
