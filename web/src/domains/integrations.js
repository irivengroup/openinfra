const moduleDefinition = {
  "id": "integrations",
  "label": "Intégrations externes",
  "shortLabel": "Intégrations",
  "icon": "grid",
  "operations": [
    {
      "id": "itsm-providers",
      "label": "Politiques connecteurs ITSM",
      "path": "/v1/integrations/itsm/providers",
      "method": "GET",
      "fields": []
    },
    {
      "id": "servicenow-validate",
      "label": "Valider connecteur ServiceNow",
      "path": "/v1/integrations/itsm/servicenow/validate",
      "method": "POST",
      "fields": [
        "Opérateur",
        "URL instance HTTPS",
        "Table CI",
        "Référence secret",
        "Connecteur actif"
      ]
    },
    {
      "id": "servicenow-ci-sync-plan",
      "label": "Plan synchro CI ServiceNow",
      "path": "/v1/integrations/itsm/servicenow/ci-sync-plan",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé ressource RSOT",
        "Direction",
        "Table cible"
      ]
    },
    {
      "id": "jira-validate",
      "label": "Valider connecteur Jira Assets",
      "path": "/v1/integrations/itsm/jira/validate",
      "method": "POST",
      "fields": [
        "Opérateur",
        "URL Jira HTTPS",
        "Type objet Assets",
        "Référence secret",
        "Connecteur actif"
      ]
    },
    {
      "id": "jira-asset-sync-plan",
      "label": "Plan synchro Assets Jira",
      "path": "/v1/integrations/itsm/jira/asset-sync-plan",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé ressource RSOT",
        "Direction",
        "Type objet Assets"
      ]
    },
    {
      "id": "glpi-validate",
      "label": "Valider connecteur GLPI Inventory",
      "path": "/v1/integrations/itsm/glpi/validate",
      "method": "POST",
      "fields": [
        "Opérateur",
        "URL GLPI HTTPS",
        "Type élément GLPI",
        "Référence secret",
        "Connecteur actif"
      ]
    },
    {
      "id": "glpi-asset-sync-plan",
      "label": "Plan synchro inventaire GLPI",
      "path": "/v1/integrations/itsm/glpi/asset-sync-plan",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé ressource RSOT",
        "Direction",
        "Type élément GLPI"
      ]
    },
    {
      "id": "freshservice-validate",
      "label": "Valider connecteur Freshservice Assets",
      "path": "/v1/integrations/itsm/freshservice/validate",
      "method": "POST",
      "fields": [
        "Opérateur",
        "URL Freshservice HTTPS",
        "Type asset Freshservice",
        "Référence secret",
        "Connecteur actif"
      ]
    },
    {
      "id": "freshservice-asset-sync-plan",
      "label": "Plan synchro Assets Freshservice",
      "path": "/v1/integrations/itsm/freshservice/asset-sync-plan",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé ressource RSOT",
        "Direction",
        "Type asset Freshservice"
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
