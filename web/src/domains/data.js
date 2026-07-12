const moduleDefinition = {
  "id": "data",
  "label": "Imports / Exports",
  "shortLabel": "Data",
  "icon": "table",
  "operations": [
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
