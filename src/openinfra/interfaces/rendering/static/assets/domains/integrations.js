const moduleDefinition = {
  "id": "integrations",
  "label": "Intégrations externes",
  "shortLabel": "Intégrations",
  "icon": "grid",
  "description": "Connecteurs externes ITSM sans ticketing natif : ServiceNow CMDB, Jira Service Management Assets, GLPI Inventory, Freshservice Assets, enrichissement et liens externes auditables.",
  "operations": [
    {
      "id": "itsm-providers",
      "label": "Politiques connecteurs ITSM",
      "method": "GET",
      "path": "/v1/integrations/itsm/providers",
      "query": []
    },
    {
      "id": "servicenow-validate",
      "label": "Valider connecteur ServiceNow",
      "method": "POST",
      "path": "/v1/integrations/itsm/servicenow/validate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "instance_url",
          "label": "URL instance HTTPS",
          "required": true,
          "placeholder": "https://instance.service-now.com"
        },
        {
          "name": "table_name",
          "label": "Table CI",
          "type": "select",
          "options": [
            "cmdb_ci",
            "cmdb_ci_server",
            "cmdb_ci_netgear",
            "cmdb_ci_computer"
          ],
          "defaultValue": "cmdb_ci"
        },
        {
          "name": "auth_secret_ref",
          "label": "Référence secret",
          "required": true,
          "placeholder": "vault://openinfra/servicenow/oauth"
        },
        {
          "name": "enabled",
          "label": "Connecteur actif",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "servicenow-ci-sync-plan",
      "label": "Plan synchro CI ServiceNow",
      "method": "POST",
      "path": "/v1/integrations/itsm/servicenow/ci-sync-plan",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "resource_key",
          "label": "Clé ressource RSOT",
          "required": true,
          "placeholder": "SRV-PAR1-001"
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "push_ci",
            "enrich_external_ticket",
            "link_external_ticket"
          ],
          "defaultValue": "push_ci"
        },
        {
          "name": "target_table",
          "label": "Table cible",
          "type": "select",
          "options": [
            "cmdb_ci",
            "cmdb_ci_server",
            "cmdb_ci_netgear",
            "cmdb_ci_computer"
          ],
          "defaultValue": "cmdb_ci"
        }
      ]
    },
    {
      "id": "jira-validate",
      "label": "Valider connecteur Jira Assets",
      "method": "POST",
      "path": "/v1/integrations/itsm/jira/validate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "instance_url",
          "label": "URL Jira HTTPS",
          "required": true,
          "placeholder": "https://tenant.atlassian.net"
        },
        {
          "name": "object_type",
          "label": "Type objet Assets",
          "type": "select",
          "options": [
            "object",
            "server",
            "network_device",
            "computer",
            "software"
          ],
          "defaultValue": "object"
        },
        {
          "name": "auth_secret_ref",
          "label": "Référence secret",
          "required": true,
          "placeholder": "vault://openinfra/jira/api-token"
        },
        {
          "name": "enabled",
          "label": "Connecteur actif",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "jira-asset-sync-plan",
      "label": "Plan synchro Assets Jira",
      "method": "POST",
      "path": "/v1/integrations/itsm/jira/asset-sync-plan",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "resource_key",
          "label": "Clé ressource RSOT",
          "required": true,
          "placeholder": "SRV-PAR1-001"
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "push_ci",
            "enrich_external_ticket",
            "link_external_ticket"
          ],
          "defaultValue": "push_ci"
        },
        {
          "name": "object_type",
          "label": "Type objet Assets",
          "type": "select",
          "options": [
            "object",
            "server",
            "network_device",
            "computer",
            "software"
          ],
          "defaultValue": "object"
        }
      ]
    },
    {
      "id": "glpi-validate",
      "label": "Valider connecteur GLPI Inventory",
      "method": "POST",
      "path": "/v1/integrations/itsm/glpi/validate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "instance_url",
          "label": "URL GLPI HTTPS",
          "required": true,
          "placeholder": "https://glpi.example.com"
        },
        {
          "name": "item_type",
          "label": "Type élément GLPI",
          "type": "select",
          "options": [
            "computer",
            "network_equipment",
            "monitor",
            "printer",
            "software",
            "rack"
          ],
          "defaultValue": "computer"
        },
        {
          "name": "auth_secret_ref",
          "label": "Référence secret",
          "required": true,
          "placeholder": "vault://openinfra/glpi/tokens"
        },
        {
          "name": "enabled",
          "label": "Connecteur actif",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "glpi-asset-sync-plan",
      "label": "Plan synchro inventaire GLPI",
      "method": "POST",
      "path": "/v1/integrations/itsm/glpi/asset-sync-plan",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "resource_key",
          "label": "Clé ressource RSOT",
          "required": true,
          "placeholder": "SRV-PAR1-001"
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "push_ci",
            "enrich_external_ticket",
            "link_external_ticket"
          ],
          "defaultValue": "push_ci"
        },
        {
          "name": "item_type",
          "label": "Type élément GLPI",
          "type": "select",
          "options": [
            "computer",
            "network_equipment",
            "monitor",
            "printer",
            "software",
            "rack"
          ],
          "defaultValue": "computer"
        }
      ]
    },
    {
      "id": "freshservice-validate",
      "label": "Valider connecteur Freshservice Assets",
      "method": "POST",
      "path": "/v1/integrations/itsm/freshservice/validate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "instance_url",
          "label": "URL Freshservice HTTPS",
          "required": true,
          "placeholder": "https://tenant.freshservice.com"
        },
        {
          "name": "asset_type",
          "label": "Type asset Freshservice",
          "type": "select",
          "options": [
            "asset",
            "hardware",
            "server",
            "network_device",
            "software"
          ],
          "defaultValue": "asset"
        },
        {
          "name": "auth_secret_ref",
          "label": "Référence secret",
          "required": true,
          "placeholder": "vault://openinfra/freshservice/api-token"
        },
        {
          "name": "enabled",
          "label": "Connecteur actif",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "freshservice-asset-sync-plan",
      "label": "Plan synchro Assets Freshservice",
      "method": "POST",
      "path": "/v1/integrations/itsm/freshservice/asset-sync-plan",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "resource_key",
          "label": "Clé ressource RSOT",
          "required": true,
          "placeholder": "SRV-PAR1-001"
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "push_ci",
            "enrich_external_ticket",
            "link_external_ticket"
          ],
          "defaultValue": "push_ci"
        },
        {
          "name": "asset_type",
          "label": "Type asset Freshservice",
          "type": "select",
          "options": [
            "asset",
            "hardware",
            "server",
            "network_device",
            "software"
          ],
          "defaultValue": "asset"
        }
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
