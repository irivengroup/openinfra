const moduleDefinition = {
  "id": "data",
  "label": "Imports / Exports",
  "shortLabel": "Data",
  "icon": "table",
  "description": "Imports massifs reprenables, rollback conflict-aware, exports asynchrones signés et lecture streaming par chunks.",
  "operations": [
    {
      "id": "import-bulk-progress",
      "label": "Progression import massif",
      "method": "GET",
      "path": "/v1/imports/bulk-progress",
      "query": [
        {
          "name": "job_id",
          "label": "Job ID",
          "required": true,
          "placeholder": "job import massif"
        }
      ]
    },
    {
      "id": "import-bulk-rollback",
      "label": "Rollback import massif",
      "method": "POST",
      "path": "/v1/imports/bulk-rollback",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "job_id",
          "label": "Job ID",
          "required": true,
          "placeholder": "job import massif"
        },
        {
          "name": "file_path",
          "label": "Fichier source relu",
          "required": true,
          "placeholder": "/var/lib/openinfra/imports/bulk.csv"
        },
        {
          "name": "format",
          "label": "Format",
          "type": "select",
          "options": [
            "csv",
            "json",
            "xlsx"
          ],
          "defaultValue": "csv"
        },
        {
          "name": "mapping",
          "label": "Mapping JSON",
          "type": "json",
          "required": true,
          "placeholder": "{\"key\":\"asset_key\",\"kind\":\"kind\",\"display_name\":\"name\",\"source\":\"source\"}"
        },
        {
          "name": "apply",
          "label": "Appliquer le rollback",
          "type": "boolean"
        },
        {
          "name": "conflict_policy",
          "label": "Politique conflit",
          "type": "select",
          "options": [
            "fail",
            "skip"
          ],
          "defaultValue": "fail"
        }
      ]
    },
    {
      "id": "import-migration-guide",
      "label": "Guide migration données",
      "method": "GET",
      "path": "/v1/imports/migration-guide",
      "query": [
        {
          "name": "source",
          "label": "Source migration",
          "type": "select",
          "options": [
            "device42",
            "netbox",
            "nautobot",
            "glpi",
            "csv"
          ],
          "defaultValue": "device42"
        }
      ]
    },
    {
      "id": "export-artifact-chunk",
      "label": "Chunk export signé",
      "method": "GET",
      "path": "/v1/exports/artifact-chunk",
      "query": [
        {
          "name": "job_id",
          "label": "Job export",
          "required": true,
          "placeholder": "job export signé"
        },
        {
          "name": "offset",
          "label": "Offset octets",
          "type": "number",
          "defaultValue": "0",
          "placeholder": "0"
        },
        {
          "name": "size",
          "label": "Taille chunk",
          "type": "number",
          "defaultValue": "65536",
          "placeholder": "65536"
        }
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
