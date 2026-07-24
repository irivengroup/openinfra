const moduleDefinition = {
  "id": "data",
  "label": "Imports / Exports",
  "shortLabel": "Data",
  "icon": "table",
  "operations": [
    {
      "id": "import-async-bulk-submit",
      "label": "Soumettre un import massif asynchrone",
      "path": "/v1/imports/async-bulk-datasets",
      "method": "POST",
      "binaryUpload": true,
      "fields": [
        {"name":"source_file","label":"Fichier CSV ou XLSX","type":"file","required":true,"accept":".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","maxSizeBytes":536870912,"help":"CSV — 512 Mio maximum ; XLSX — 50 Mio maximum."},
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
      ]
    },
    {
      "id": "import-async-bulk-status",
      "label": "Suivre un import massif asynchrone",
      "path": "/v1/imports/async-bulk-status",
      "method": "GET",
      "fields": [
        {"name":"job_id","label":"Job asynchrone","required":true}
      ]
    },
    {
      "id": "import-bulk-progress",
      "label": "Progression import massif",
      "path": "/v1/imports/bulk-progress",
      "method": "GET",
      "fields": [
        "Job ID"
      ]
    },
    {
      "id": "import-bulk-rollback",
      "label": "Rollback import massif",
      "path": "/v1/imports/bulk-rollback",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Job ID",
        "Fichier source",
        "Format",
        "Mapping JSON",
        "Appliquer",
        "Politique conflit"
      ]
    },
    {
      "id": "import-migration-guide",
      "label": "Guide migration données",
      "path": "/v1/imports/migration-guide",
      "method": "GET",
      "fields": [
        "Source migration"
      ]
    },
    {
      "id": "export-artifact-chunk",
      "label": "Chunk export signé",
      "path": "/v1/exports/artifact-chunk",
      "method": "GET",
      "fields": [
        "Job export",
        "Offset octets",
        "Taille chunk"
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
