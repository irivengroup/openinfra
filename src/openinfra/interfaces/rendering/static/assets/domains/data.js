const moduleDefinition = {
  "id": "data",
  "label": "Imports / Exports",
  "shortLabel": "Data",
  "icon": "table",
  "description": "Imports massifs reprenables, rollback conflict-aware, exports asynchrones signés et lecture streaming par chunks.",
  "operations": [
    {
      "id": "import-async-bulk-submit",
      "label": "Soumettre un import massif asynchrone",
      "method": "POST",
      "path": "/v1/imports/async-bulk-datasets",
      "binaryUpload": true,
      "authField": "admin_token",
      "query": [
        {"name":"actor","label":"Opérateur","required":true,"defaultValue":"web"},
        {"name":"format","label":"Format","type":"select","options":["csv","xlsx"],"defaultValue":"csv","required":true},
        {"name":"mapping_json","label":"Mapping JSON","type":"json","required":true,"defaultValue":"{\"key\":\"asset_key\",\"kind\":\"kind\",\"display_name\":\"name\",\"source\":\"source\"}"},
        {"name":"apply","label":"Appliquer l’import","type":"boolean","defaultValue":"false"},
        {"name":"idempotency_key","label":"Clé d’idempotence","required":true,"placeholder":"import-cmdb-2026-07-22"},
        {"name":"batch_size","label":"Taille de lot","type":"number","min":1,"max":100000,"defaultValue":"5000"},
        {"name":"checkpoint_interval","label":"Intervalle checkpoint","type":"number","min":1,"max":1000000,"defaultValue":"25000"},
        {"name":"sample_limit","label":"Limite échantillon","type":"number","min":0,"max":10000,"defaultValue":"100"},
        {"name":"max_attempts","label":"Tentatives maximum","type":"number","min":1,"max":20,"defaultValue":"3"},
        {"name":"resume_job_id","label":"Job à reprendre","placeholder":"optionnel"}
      ],
      "body": [
        {"name":"admin_token","label":"Jeton administrateur","type":"password","required":true},
        {"name":"source_file","label":"Fichier CSV ou XLSX","type":"file","required":true,"accept":".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","maxSizeBytes":536870912,"help":"CSV — 512 Mio maximum ; XLSX — 50 Mio maximum."}
      ]
    },
    {
      "id": "import-async-bulk-status",
      "label": "Suivre un import massif asynchrone",
      "method": "GET",
      "path": "/v1/imports/async-bulk-status",
      "authField": "admin_token",
      "query": [
        {"name":"job_id","label":"Job asynchrone","required":true}
      ],
      "body": [
        {"name":"admin_token","label":"Jeton administrateur","type":"password","required":true}
      ]
    },
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
