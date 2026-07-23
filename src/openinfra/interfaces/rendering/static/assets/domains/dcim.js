const moduleDefinition = {
  "id": "dcim",
  "label": "DCIM",
  "icon": "home",
  "description": "Sites, salles, zones, racks, ports, câbles, énergie et localisation terrain.",
  "operations": [
    {
      "id": "dcim-sites",
      "label": "Lister les sites DCIM",
      "method": "GET",
      "path": "/v1/dcim/sites",
      "query": [
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "dcim-site",
      "label": "Consulter un site DCIM",
      "method": "GET",
      "path": "/v1/dcim/site",
      "query": [
        {
          "name": "code",
          "label": "Site",
          "required": true,
          "defaultValue": "PAR1"
        }
      ]
    },
    {
      "id": "multisite-grant-upsert",
      "label": "Affecter un accès à un site",
      "method": "POST",
      "path": "/v1/multisite/site-access/grants/upsert",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "subject",
          "label": "Identité",
          "required": true,
          "placeholder": "prenom.nom@example.net"
        },
        {
          "name": "site_code",
          "label": "Site",
          "required": true,
          "defaultValue": "PAR1"
        },
        {
          "name": "access_level",
          "label": "Niveau d’accès",
          "type": "select",
          "required": true,
          "options": [
            {
              "value": "viewer",
              "label": "Lecture"
            },
            {
              "value": "operator",
              "label": "Opérateur"
            },
            {
              "value": "admin",
              "label": "Administrateur local"
            }
          ],
          "defaultValue": "viewer"
        }
      ]
    },
    {
      "id": "multisite-grant-revoke",
      "label": "Révoquer un accès à un site",
      "method": "POST",
      "path": "/v1/multisite/site-access/grants/revoke",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "subject",
          "label": "Identité",
          "required": true
        },
        {
          "name": "site_code",
          "label": "Site",
          "required": true,
          "defaultValue": "PAR1"
        }
      ]
    },
    {
      "id": "multisite-grants",
      "label": "Lister les accès par site",
      "method": "GET",
      "path": "/v1/multisite/site-access/grants",
      "query": [
        {
          "name": "subject",
          "label": "Identité"
        },
        {
          "name": "site_code",
          "label": "Site"
        },
        {
          "name": "active_only",
          "label": "Accès actifs uniquement",
          "type": "boolean",
          "defaultValue": "true"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "multisite-sites",
      "label": "Lister les sites accessibles",
      "method": "GET",
      "path": "/v1/multisite/sites",
      "query": [
        {
          "name": "subject",
          "label": "Identité"
        },
        {
          "name": "required_level",
          "label": "Niveau minimal",
          "type": "select",
          "options": [
            "viewer",
            "operator",
            "admin"
          ],
          "defaultValue": "viewer"
        }
      ]
    },
    {
      "id": "multisite-report-generate",
      "label": "Générer un rapport multisite",
      "method": "POST",
      "path": "/v1/multisite/reports/generate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "subject",
          "label": "Identité"
        },
        {
          "name": "site_codes",
          "label": "Sites (JSON)",
          "type": "json",
          "defaultValue": "[]"
        }
      ]
    },
    {
      "id": "multisite-reports",
      "label": "Lister les rapports multisites",
      "method": "GET",
      "path": "/v1/multisite/reports",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "multisite-report-get",
      "label": "Consulter un rapport multisite",
      "method": "GET",
      "path": "/v1/multisite/reports/get",
      "query": [
        {
          "name": "report_id",
          "label": "ID rapport",
          "required": true
        }
      ]
    },
    {
      "id": "multisite-dr-plan-configure",
      "label": "Configurer un plan de reprise multisite",
      "method": "POST",
      "path": "/v1/multisite/disaster-recovery/plans/configure",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom du plan",
          "required": true,
          "placeholder": "Reprise PAR1 vers LON1"
        },
        {
          "name": "primary_site_code",
          "label": "Site primaire",
          "required": true,
          "defaultValue": "PAR1"
        },
        {
          "name": "recovery_site_code",
          "label": "Site de secours",
          "required": true,
          "placeholder": "LON1"
        },
        {
          "name": "replication_mode",
          "label": "Mode de réplication",
          "type": "select",
          "required": true,
          "options": [
            {
              "value": "asynchronous",
              "label": "Asynchrone"
            },
            {
              "value": "synchronous",
              "label": "Synchrone"
            }
          ],
          "defaultValue": "asynchronous"
        },
        {
          "name": "rpo_seconds",
          "label": "RPO (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "300",
          "min": "1",
          "max": "86400"
        },
        {
          "name": "rto_seconds",
          "label": "RTO (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "1800",
          "min": "1",
          "max": "604800"
        },
        {
          "name": "max_backup_age_seconds",
          "label": "Âge maximal sauvegarde (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "86400",
          "min": "60",
          "max": "2592000"
        }
      ]
    },
    {
      "id": "multisite-dr-plan-disable",
      "label": "Désactiver un plan de reprise multisite",
      "method": "POST",
      "path": "/v1/multisite/disaster-recovery/plans/disable",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "plan_id",
          "label": "ID plan",
          "required": true
        }
      ]
    },
    {
      "id": "multisite-dr-plans",
      "label": "Lister les plans de reprise multisites",
      "method": "GET",
      "path": "/v1/multisite/disaster-recovery/plans",
      "query": [
        {
          "name": "active_only",
          "label": "Plans actifs uniquement",
          "type": "boolean",
          "defaultValue": "true"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "multisite-dr-plan-get",
      "label": "Consulter un plan de reprise multisite",
      "method": "GET",
      "path": "/v1/multisite/disaster-recovery/plans/get",
      "query": [
        {
          "name": "plan_id",
          "label": "ID plan",
          "required": true
        }
      ]
    },
    {
      "id": "multisite-dr-drill-execute",
      "label": "Enregistrer un exercice de perte du site primaire",
      "method": "POST",
      "path": "/v1/multisite/disaster-recovery/drills/execute",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "plan_id",
          "label": "ID plan",
          "required": true
        },
        {
          "name": "replication_lag_seconds",
          "label": "Retard réplication (secondes)",
          "type": "number",
          "required": true,
          "min": "0"
        },
        {
          "name": "backup_age_seconds",
          "label": "Âge sauvegarde (secondes)",
          "type": "number",
          "required": true,
          "min": "0"
        },
        {
          "name": "measured_rto_seconds",
          "label": "RTO mesuré (secondes)",
          "type": "number",
          "required": true,
          "min": "0"
        },
        {
          "name": "restore_verified",
          "label": "Restauration vérifiée",
          "type": "boolean",
          "required": true,
          "defaultValue": "false"
        },
        {
          "name": "recovery_available",
          "label": "Site de secours disponible",
          "type": "boolean",
          "required": true,
          "defaultValue": "false"
        },
        {
          "name": "vip_reachable",
          "label": "DNS/VIP joignable",
          "type": "boolean",
          "required": true,
          "defaultValue": "false"
        },
        {
          "name": "operator_confirmed",
          "label": "Validation opérateur",
          "type": "boolean",
          "required": true,
          "defaultValue": "false"
        }
      ]
    },
    {
      "id": "multisite-dr-drills",
      "label": "Lister les exercices de reprise multisites",
      "method": "GET",
      "path": "/v1/multisite/disaster-recovery/drills",
      "query": [
        {
          "name": "plan_id",
          "label": "ID plan"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "passed",
            "failed"
          ]
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "multisite-dr-drill-get",
      "label": "Consulter un exercice de reprise multisite",
      "method": "GET",
      "path": "/v1/multisite/disaster-recovery/drills/get",
      "query": [
        {
          "name": "drill_id",
          "label": "ID exercice",
          "required": true
        }
      ]
    },
    {
      "id": "multisite-route-configure",
      "label": "Configurer une route Discovery régionale",
      "method": "POST",
      "path": "/v1/multisite/regional-discovery/routes/configure",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "region_code",
          "label": "Région",
          "required": true,
          "placeholder": "EU-WEST"
        },
        {
          "name": "site_code",
          "label": "Site",
          "required": true,
          "defaultValue": "PAR1"
        },
        {
          "name": "vrf_code",
          "label": "VRF",
          "required": true,
          "placeholder": "PROD"
        },
        {
          "name": "collector_id",
          "label": "ID agent régional",
          "required": true
        }
      ]
    },
    {
      "id": "multisite-route-disable",
      "label": "Désactiver une route Discovery régionale",
      "method": "POST",
      "path": "/v1/multisite/regional-discovery/routes/disable",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "route_id",
          "label": "ID route",
          "required": true
        }
      ]
    },
    {
      "id": "multisite-routes",
      "label": "Lister les routes Discovery régionales",
      "method": "GET",
      "path": "/v1/multisite/regional-discovery/routes",
      "query": [
        {
          "name": "region_code",
          "label": "Région"
        },
        {
          "name": "site_code",
          "label": "Site"
        },
        {
          "name": "active_only",
          "label": "Routes actives uniquement",
          "type": "boolean",
          "defaultValue": "true"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "multisite-route-get",
      "label": "Consulter une route Discovery régionale",
      "method": "GET",
      "path": "/v1/multisite/regional-discovery/routes/get",
      "query": [
        {
          "name": "route_id",
          "label": "ID route",
          "required": true
        }
      ]
    },
    {
      "id": "multisite-job-route",
      "label": "Router un job Discovery régional",
      "method": "POST",
      "path": "/v1/multisite/regional-discovery/jobs/route",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "region_code",
          "label": "Région",
          "required": true,
          "placeholder": "EU-WEST"
        },
        {
          "name": "site_code",
          "label": "Site",
          "required": true,
          "defaultValue": "PAR1"
        },
        {
          "name": "vrf_code",
          "label": "VRF",
          "required": true,
          "placeholder": "PROD"
        },
        {
          "name": "job_type",
          "label": "Type de job",
          "required": true,
          "placeholder": "network-inventory"
        },
        {
          "name": "target",
          "label": "Cible",
          "required": true,
          "placeholder": "10.20.0.0/24"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "max_attempts",
          "label": "Tentatives maximales",
          "type": "number",
          "defaultValue": "3",
          "min": "1",
          "max": "10"
        }
      ]
    },
    {
      "id": "dcim-site-create",
      "label": "Créer un site DCIM",
      "method": "POST",
      "path": "/v1/dcim/site/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Code site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "name",
          "label": "Nom site",
          "required": true,
          "placeholder": "Paris 1"
        },
        {
          "name": "country",
          "label": "Pays",
          "type": "country-select",
          "required": true
        },
        {
          "name": "region",
          "label": "Région",
          "placeholder": "Île-de-France"
        },
        {
          "name": "city",
          "label": "Ville",
          "required": true,
          "placeholder": "Paris"
        },
        {
          "name": "street_address",
          "label": "Rue",
          "required": true,
          "placeholder": "111 Quai du Président Roosevelt"
        },
        {
          "name": "postal_code",
          "label": "Code postal",
          "required": true,
          "placeholder": "92130"
        },
        {
          "name": "contact_email",
          "label": "Email",
          "required": true,
          "placeholder": "site-par1@example.net"
        },
        {
          "name": "phone",
          "label": "Téléphone",
          "required": true,
          "placeholder": "+33123456789"
        }
      ]
    },
    {
      "id": "dcim-site-update",
      "label": "Modifier un site DCIM",
      "method": "POST",
      "path": "/v1/dcim/site/update",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Site",
          "required": true,
          "defaultValue": "PAR1"
        },
        {
          "name": "name",
          "label": "Nom site",
          "placeholder": "Paris 1"
        },
        {
          "name": "country",
          "label": "Pays",
          "type": "country-select"
        },
        {
          "name": "region",
          "label": "Région",
          "placeholder": "Île-de-France"
        },
        {
          "name": "city",
          "label": "Ville",
          "placeholder": "Paris"
        },
        {
          "name": "street_address",
          "label": "Rue",
          "placeholder": "111 Quai du Président Roosevelt"
        },
        {
          "name": "postal_code",
          "label": "Code postal",
          "placeholder": "92130"
        },
        {
          "name": "contact_email",
          "label": "Email",
          "placeholder": "site-par1@example.net"
        },
        {
          "name": "phone",
          "label": "Téléphone",
          "placeholder": "+33123456789"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        }
      ]
    },
    {
      "id": "dcim-site-delete",
      "label": "Retirer un site DCIM",
      "method": "POST",
      "path": "/v1/dcim/site/delete",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Site",
          "required": true,
          "defaultValue": "PAR1"
        }
      ]
    },
    {
      "id": "dcim-buildings",
      "label": "Lister les bâtiments",
      "method": "GET",
      "path": "/v1/dcim/buildings",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "dcim-building",
      "label": "Consulter un bâtiment",
      "method": "GET",
      "path": "/v1/dcim/building",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "code",
          "label": "Code bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        }
      ]
    },
    {
      "id": "dcim-building-create",
      "label": "Créer un bâtiment",
      "method": "POST",
      "path": "/v1/dcim/building/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "code",
          "label": "Code bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "name",
          "label": "Nom bâtiment",
          "required": true,
          "placeholder": "Bâtiment A"
        },
        {
          "name": "building_type",
          "label": "Type Batiment",
          "type": "select",
          "required": true,
          "options": [
            {
              "value": "floors",
              "label": "Etages"
            },
            {
              "value": "simple",
              "label": "Simple"
            }
          ],
          "defaultValue": "simple"
        },
        {
          "name": "initial_level",
          "label": "Niveau Initial",
          "type": "number",
          "required": true,
          "defaultValue": "0",
          "min": "-20",
          "max": "0",
          "step": "1",
          "visibleWhen": {
            "field": "building_type",
            "value": "floors"
          }
        },
        {
          "name": "final_level",
          "label": "Niveau Final",
          "type": "number",
          "required": true,
          "defaultValue": "1",
          "min": "1",
          "max": "150",
          "step": "1",
          "visibleWhen": {
            "field": "building_type",
            "value": "floors"
          }
        }
      ]
    },
    {
      "id": "dcim-building-update",
      "label": "Modifier un bâtiment",
      "method": "POST",
      "path": "/v1/dcim/building/update",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "code",
          "label": "Code bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "name",
          "label": "Nom bâtiment",
          "placeholder": "Bâtiment A"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        }
      ]
    },
    {
      "id": "dcim-building-delete",
      "label": "Retirer un bâtiment",
      "method": "POST",
      "path": "/v1/dcim/building/delete",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "code",
          "label": "Code bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        }
      ]
    },
    {
      "id": "dcim-floors",
      "label": "Lister les étages",
      "method": "GET",
      "path": "/v1/dcim/floors",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "dcim-floor",
      "label": "Consulter un étage",
      "method": "GET",
      "path": "/v1/dcim/floor",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "code",
          "label": "Étage",
          "required": true,
          "placeholder": "L01"
        }
      ]
    },
    {
      "id": "dcim-rooms-list",
      "label": "Lister les salles",
      "method": "GET",
      "path": "/v1/dcim/rooms",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "dcim-room",
      "label": "Consulter une salle",
      "method": "GET",
      "path": "/v1/dcim/room",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "code",
          "label": "Code salle",
          "required": true,
          "placeholder": "MMR1"
        }
      ]
    },
    {
      "id": "dcim-room-create",
      "label": "Créer une salle",
      "method": "POST",
      "path": "/v1/dcim/room/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "floor",
          "label": "Étage",
          "placeholder": "Obligatoire si Type Batiment = Etages"
        },
        {
          "name": "code",
          "label": "Code salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "name",
          "label": "Nom salle",
          "required": true,
          "placeholder": "Meet-Me Room"
        },
        {
          "name": "rows",
          "label": "Plage lignes salle",
          "type": "csv",
          "required": true,
          "placeholder": "0-12"
        },
        {
          "name": "columns",
          "label": "Plage colonnes salle",
          "type": "csv",
          "required": true,
          "placeholder": "A-F"
        }
      ]
    },
    {
      "id": "dcim-define-room",
      "label": "Créer une hiérarchie physique",
      "method": "POST",
      "path": "/v1/dcim/rooms",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site_code",
          "label": "Code site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "site_name",
          "label": "Nom site",
          "required": true,
          "placeholder": "Paris 1"
        },
        {
          "name": "country",
          "label": "Pays",
          "type": "country-select",
          "required": true
        },
        {
          "name": "region",
          "label": "Région",
          "placeholder": "Île-de-France"
        },
        {
          "name": "city",
          "label": "Ville",
          "required": true,
          "placeholder": "Paris"
        },
        {
          "name": "building_code",
          "label": "Code bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "building_name",
          "label": "Nom bâtiment",
          "required": true,
          "placeholder": "Bâtiment A"
        },
        {
          "name": "floor_index",
          "label": "Niveau",
          "type": "number",
          "required": true,
          "defaultValue": "1",
          "min": "-20",
          "max": "150",
          "step": "1"
        },
        {
          "name": "room_code",
          "label": "Code salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "room_name",
          "label": "Nom salle",
          "required": true,
          "placeholder": "Meet-Me Room"
        },
        {
          "name": "rows",
          "label": "Plage lignes salle",
          "type": "csv",
          "required": true,
          "placeholder": "0-12"
        },
        {
          "name": "columns",
          "label": "Plage colonnes salle",
          "type": "csv",
          "required": true,
          "placeholder": "A-F"
        },
        {
          "name": "zone_code",
          "label": "Code zone",
          "placeholder": "Z1"
        },
        {
          "name": "zone_name",
          "label": "Nom zone",
          "placeholder": "Zone froide 1"
        },
        {
          "name": "zone_rows",
          "label": "Lignes zone",
          "type": "csv",
          "placeholder": "A"
        },
        {
          "name": "zone_columns",
          "label": "Colonnes zone",
          "type": "csv",
          "placeholder": "01"
        }
      ]
    },
    {
      "id": "dcim-room-update",
      "label": "Modifier une salle",
      "method": "POST",
      "path": "/v1/dcim/room/update",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "code",
          "label": "Code salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "name",
          "label": "Nom salle",
          "placeholder": "Meet-Me Room"
        },
        {
          "name": "rows",
          "label": "Plage lignes salle",
          "type": "csv",
          "placeholder": "0-12"
        },
        {
          "name": "columns",
          "label": "Plage colonnes salle",
          "type": "csv",
          "placeholder": "A-F"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        }
      ]
    },
    {
      "id": "dcim-room-delete",
      "label": "Retirer une salle",
      "method": "POST",
      "path": "/v1/dcim/room/delete",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "code",
          "label": "Code salle",
          "required": true,
          "placeholder": "MMR1"
        }
      ]
    },
    {
      "id": "dcim-racks",
      "label": "Lister les chassis/racks",
      "method": "GET",
      "path": "/v1/dcim/racks",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "dcim-rack",
      "label": "Consulter un chassis/rack",
      "method": "GET",
      "path": "/v1/dcim/rack",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "rack",
          "label": "Chassis/Rack",
          "required": true,
          "placeholder": "R01"
        }
      ]
    },
    {
      "id": "dcim-rack-create",
      "label": "Créer un chassis/rack",
      "method": "POST",
      "path": "/v1/dcim/racks",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "floor",
          "label": "Étage"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "rack",
          "label": "Code chassis/rack",
          "required": true,
          "placeholder": "R01"
        },
        {
          "name": "row",
          "label": "Ligne salle",
          "required": true
        },
        {
          "name": "column",
          "label": "Colonne salle",
          "required": true
        },
        {
          "name": "units",
          "label": "Capacité U",
          "type": "number",
          "required": true,
          "defaultValue": "42"
        },
        {
          "name": "usable_faces",
          "label": "Faces utilisables",
          "type": "csv",
          "defaultValue": "front",
          "placeholder": "front,rear"
        },
        {
          "name": "max_weight_kg",
          "label": "Poids max kg",
          "type": "number"
        },
        {
          "name": "power_capacity_watts",
          "label": "Puissance max watts",
          "type": "number"
        }
      ]
    },
    {
      "id": "dcim-rack-update",
      "label": "Modifier un chassis/rack",
      "method": "POST",
      "path": "/v1/dcim/rack/update",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "rack",
          "label": "Chassis/Rack",
          "required": true
        },
        {
          "name": "row",
          "label": "Ligne salle"
        },
        {
          "name": "column",
          "label": "Colonne salle"
        },
        {
          "name": "units",
          "label": "Capacité U",
          "type": "number"
        },
        {
          "name": "usable_faces",
          "label": "Faces utilisables",
          "type": "csv"
        },
        {
          "name": "max_weight_kg",
          "label": "Poids max kg",
          "type": "number"
        },
        {
          "name": "power_capacity_watts",
          "label": "Puissance max watts",
          "type": "number"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        }
      ]
    },
    {
      "id": "dcim-rack-delete",
      "label": "Retirer un chassis/rack",
      "method": "POST",
      "path": "/v1/dcim/rack/delete",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "rack",
          "label": "Chassis/Rack",
          "required": true
        }
      ]
    },
    {
      "id": "dcim-zones",
      "label": "Lister les zones",
      "method": "GET",
      "path": "/v1/dcim/zones",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "dcim-zone",
      "label": "Consulter une zone",
      "method": "GET",
      "path": "/v1/dcim/zone",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "code",
          "label": "Code zone",
          "required": true,
          "placeholder": "Z1"
        }
      ]
    },
    {
      "id": "dcim-zone-create",
      "label": "Créer une zone",
      "method": "POST",
      "path": "/v1/dcim/zone/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "code",
          "label": "Code zone",
          "required": true,
          "placeholder": "Z1"
        },
        {
          "name": "name",
          "label": "Nom zone",
          "required": true,
          "placeholder": "Zone froide 1"
        },
        {
          "name": "rows",
          "label": "Lignes zone",
          "type": "csv",
          "required": true,
          "placeholder": "A"
        },
        {
          "name": "columns",
          "label": "Colonnes zone",
          "type": "csv",
          "required": true,
          "placeholder": "01"
        }
      ]
    },
    {
      "id": "dcim-zone-update",
      "label": "Modifier une zone",
      "method": "POST",
      "path": "/v1/dcim/zone/update",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "code",
          "label": "Code zone",
          "required": true,
          "placeholder": "Z1"
        },
        {
          "name": "name",
          "label": "Nom zone",
          "placeholder": "Zone froide 1"
        },
        {
          "name": "rows",
          "label": "Lignes zone",
          "type": "csv",
          "placeholder": "A"
        },
        {
          "name": "columns",
          "label": "Colonnes zone",
          "type": "csv",
          "placeholder": "01"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        }
      ]
    },
    {
      "id": "dcim-zone-delete",
      "label": "Retirer une zone",
      "method": "POST",
      "path": "/v1/dcim/zone/delete",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "code",
          "label": "Code zone",
          "required": true,
          "placeholder": "Z1"
        }
      ]
    },
    {
      "id": "dcim-topology-catalog",
      "label": "Catalogue dépendances DCIM",
      "method": "GET",
      "path": "/v1/dcim/topology-catalog",
      "query": [
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "dcim-locate-equipment",
      "label": "Localiser un équipement",
      "method": "POST",
      "path": "/v1/dcim/locations",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "asset_tag",
          "label": "Numéro d’actif",
          "required": true,
          "placeholder": "PAR-SRV-001"
        },
        {
          "name": "equipment_name",
          "label": "Nom équipement",
          "required": true,
          "placeholder": "srv-app-01"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "floor",
          "label": "Étage",
          "placeholder": "L01"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "zone",
          "label": "Zone",
          "placeholder": "Z1"
        },
        {
          "name": "row",
          "label": "Ligne salle",
          "required": true,
          "placeholder": "A"
        },
        {
          "name": "column",
          "label": "Colonne salle",
          "required": true,
          "placeholder": "01"
        },
        {
          "name": "rack",
          "label": "Rack",
          "placeholder": "R01"
        },
        {
          "name": "u_position",
          "label": "Position U",
          "type": "number",
          "placeholder": "12"
        },
        {
          "name": "rack_face",
          "label": "Face rack",
          "type": "select",
          "options": [
            "front",
            "rear"
          ]
        },
        {
          "name": "u_height",
          "label": "Hauteur U",
          "type": "number",
          "placeholder": "2"
        },
        {
          "name": "x",
          "label": "Coordonnée X",
          "type": "number",
          "placeholder": "1.25"
        },
        {
          "name": "y",
          "label": "Coordonnée Y",
          "type": "number",
          "placeholder": "2.50"
        },
        {
          "name": "z",
          "label": "Coordonnée Z",
          "type": "number",
          "placeholder": "0.00"
        }
      ]
    },
    {
      "id": "dcim-locator-sheet",
      "label": "Fiche d’intervention équipement",
      "method": "GET",
      "path": "/v1/dcim/locator-sheet",
      "query": [
        {
          "name": "asset_tag",
          "label": "Numéro d’actif",
          "required": true,
          "placeholder": "PAR-SRV-001"
        },
        {
          "name": "format",
          "label": "Format rendu",
          "type": "select",
          "options": [
            "json",
            "html"
          ]
        }
      ]
    },
    {
      "id": "dcim-rack-capacity",
      "label": "Capacité rack",
      "method": "GET",
      "path": "/v1/dcim/rack-capacity",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "rack",
          "label": "Rack",
          "required": true
        }
      ]
    },
    {
      "id": "dcim-room-plan",
      "label": "Plan de salle",
      "method": "GET",
      "path": "/v1/dcim/room-plan",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "format",
          "label": "Format rendu",
          "type": "select",
          "options": [
            "json",
            "svg",
            "html"
          ],
          "defaultValue": "json"
        }
      ]
    },
    {
      "id": "dcim-rack-elevation",
      "label": "Élévation rack",
      "method": "GET",
      "path": "/v1/dcim/rack-elevation",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true
        },
        {
          "name": "rack",
          "label": "Rack",
          "required": true
        },
        {
          "name": "face",
          "label": "Face rack",
          "type": "select",
          "options": [
            "front",
            "rear"
          ],
          "defaultValue": "front"
        },
        {
          "name": "format",
          "label": "Format rendu",
          "type": "select",
          "options": [
            "json",
            "svg",
            "html"
          ],
          "defaultValue": "json"
        }
      ]
    },
    {
      "id": "dcim-patch-panel",
      "label": "Définir un panneau de brassage",
      "method": "POST",
      "path": "/v1/dcim/patch-panels",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "rack",
          "label": "Rack",
          "required": true,
          "placeholder": "R01"
        },
        {
          "name": "patch_panel",
          "label": "Panneau de brassage",
          "required": true,
          "placeholder": "PP01"
        },
        {
          "name": "rack_face",
          "label": "Face rack",
          "type": "select",
          "options": [
            "front",
            "rear"
          ],
          "defaultValue": "front"
        },
        {
          "name": "u_position",
          "label": "Position U",
          "type": "number",
          "required": true,
          "placeholder": "1"
        },
        {
          "name": "u_height",
          "label": "Hauteur U",
          "type": "number",
          "placeholder": "1"
        },
        {
          "name": "port_count",
          "label": "Nombre de ports",
          "type": "number",
          "required": true,
          "placeholder": "24"
        },
        {
          "name": "connector",
          "label": "Connecteur",
          "type": "select",
          "options": [
            "rj45",
            "lc",
            "sc",
            "mpo",
            "sfp",
            "qsfp"
          ],
          "defaultValue": "rj45"
        },
        {
          "name": "medium",
          "label": "Média câble",
          "type": "select",
          "options": [
            "copper",
            "fiber",
            "dac"
          ],
          "defaultValue": "copper"
        },
        {
          "name": "label",
          "label": "Libellé",
          "placeholder": "Panneau cuivre ToR"
        },
        {
          "name": "port_prefix",
          "label": "Préfixe ports",
          "placeholder": "P"
        }
      ]
    },
    {
      "id": "dcim-port",
      "label": "Définir un port DCIM",
      "method": "POST",
      "path": "/v1/dcim/ports",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "owner_type",
          "label": "Type propriétaire",
          "type": "select",
          "options": [
            "equipment",
            "patch_panel"
          ],
          "defaultValue": "equipment"
        },
        {
          "name": "owner_code",
          "label": "Code propriétaire",
          "required": true,
          "placeholder": "SRV-001"
        },
        {
          "name": "port_name",
          "label": "Nom port",
          "required": true,
          "placeholder": "ETH0"
        },
        {
          "name": "connector",
          "label": "Connecteur",
          "type": "select",
          "options": [
            "rj45",
            "lc",
            "sc",
            "mpo",
            "sfp",
            "qsfp"
          ],
          "defaultValue": "rj45"
        },
        {
          "name": "medium",
          "label": "Média câble",
          "type": "select",
          "options": [
            "copper",
            "fiber",
            "dac"
          ],
          "defaultValue": "copper"
        },
        {
          "name": "site",
          "label": "Site",
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "placeholder": "BAT-A"
        },
        {
          "name": "room",
          "label": "Salle",
          "placeholder": "MMR1"
        },
        {
          "name": "enabled",
          "label": "Port actif",
          "type": "boolean",
          "placeholder": "true"
        }
      ]
    },
    {
      "id": "dcim-cable",
      "label": "Connecter un câble",
      "method": "POST",
      "path": "/v1/dcim/cables",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "cable_id",
          "label": "Identifiant câble",
          "required": true,
          "placeholder": "CAB-000123"
        },
        {
          "name": "a_owner_type",
          "label": "Type propriétaire A",
          "type": "select",
          "options": [
            "equipment",
            "patch_panel"
          ],
          "defaultValue": "equipment"
        },
        {
          "name": "a_owner_code",
          "label": "Code propriétaire A",
          "required": true,
          "placeholder": "SRV-001"
        },
        {
          "name": "a_port_name",
          "label": "Port A",
          "required": true,
          "placeholder": "ETH0"
        },
        {
          "name": "b_owner_type",
          "label": "Type propriétaire B",
          "type": "select",
          "options": [
            "equipment",
            "patch_panel"
          ],
          "defaultValue": "patch_panel"
        },
        {
          "name": "b_owner_code",
          "label": "Code propriétaire B",
          "required": true,
          "placeholder": "PP01"
        },
        {
          "name": "b_port_name",
          "label": "Port B",
          "required": true,
          "placeholder": "P01"
        },
        {
          "name": "medium",
          "label": "Média câble",
          "type": "select",
          "options": [
            "copper",
            "fiber",
            "dac"
          ],
          "defaultValue": "copper"
        },
        {
          "name": "status",
          "label": "Statut câble",
          "type": "select",
          "options": [
            "planned",
            "installed",
            "retired"
          ],
          "defaultValue": "installed"
        },
        {
          "name": "path_segments",
          "label": "Chemin câble",
          "type": "csv",
          "required": true,
          "placeholder": "Rack R01 manager, Panneau PP01"
        },
        {
          "name": "length_m",
          "label": "Longueur m",
          "type": "number",
          "placeholder": "2.5"
        },
        {
          "name": "label",
          "label": "Libellé",
          "placeholder": "Uplink serveur"
        }
      ]
    },
    {
      "id": "dcim-cable-trace",
      "label": "Tracer un câble",
      "method": "GET",
      "path": "/v1/dcim/cable-trace",
      "query": [
        {
          "name": "cable_id",
          "label": "Identifiant câble",
          "required": true,
          "placeholder": "CAB-000123"
        }
      ]
    },
    {
      "id": "dcim-power-device",
      "label": "Définir un équipement électrique",
      "method": "POST",
      "path": "/v1/dcim/power-devices",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Code équipement électrique",
          "required": true,
          "placeholder": "PDU-A-R01"
        },
        {
          "name": "kind",
          "label": "Type équipement électrique",
          "type": "select",
          "options": [
            "pdu",
            "ups"
          ],
          "defaultValue": "pdu"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "rack",
          "label": "Rack",
          "placeholder": "R01"
        },
        {
          "name": "side",
          "label": "Chaîne électrique",
          "type": "select",
          "options": [
            "A",
            "B"
          ]
        },
        {
          "name": "capacity_watts",
          "label": "Capacité watts",
          "type": "number",
          "required": true,
          "placeholder": "5000"
        },
        {
          "name": "derating_percent",
          "label": "Derating %",
          "type": "number",
          "placeholder": "80"
        },
        {
          "name": "input_source",
          "label": "Source amont",
          "placeholder": "utility"
        },
        {
          "name": "output_voltage",
          "label": "Tension sortie V",
          "type": "number",
          "placeholder": "230"
        },
        {
          "name": "label",
          "label": "Libellé",
          "placeholder": "PDU A baie R01"
        }
      ]
    },
    {
      "id": "dcim-power-circuit",
      "label": "Définir un circuit électrique",
      "method": "POST",
      "path": "/v1/dcim/power-circuits",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "circuit_id",
          "label": "Identifiant circuit",
          "required": true,
          "placeholder": "CIR-A-R01"
        },
        {
          "name": "source_device",
          "label": "Source électrique",
          "required": true,
          "placeholder": "PDU-A-R01"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "rack",
          "label": "Rack",
          "required": true,
          "placeholder": "R01"
        },
        {
          "name": "side",
          "label": "Chaîne électrique",
          "type": "select",
          "options": [
            "A",
            "B"
          ],
          "defaultValue": "A"
        },
        {
          "name": "capacity_watts",
          "label": "Capacité watts",
          "type": "number",
          "required": true,
          "placeholder": "2000"
        },
        {
          "name": "breaker_rating_amps",
          "label": "Calibre disjoncteur A",
          "type": "number",
          "required": true,
          "placeholder": "16"
        },
        {
          "name": "redundancy_group",
          "label": "Groupe redondance",
          "placeholder": "default"
        },
        {
          "name": "label",
          "label": "Libellé",
          "placeholder": "Circuit A baie R01"
        }
      ]
    },
    {
      "id": "dcim-cooling-zone",
      "label": "Définir une zone de refroidissement",
      "method": "POST",
      "path": "/v1/dcim/cooling-zones",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site",
          "label": "Site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "zone",
          "label": "Zone froid/chaud",
          "required": true,
          "placeholder": "Z1"
        },
        {
          "name": "role",
          "label": "Rôle refroidissement",
          "type": "select",
          "options": [
            "cold_aisle",
            "hot_aisle",
            "neutral"
          ],
          "defaultValue": "cold_aisle"
        },
        {
          "name": "cooling_capacity_watts",
          "label": "Capacité froid watts",
          "type": "number",
          "required": true,
          "placeholder": "3000"
        },
        {
          "name": "supply_temperature_c",
          "label": "Température soufflage °C",
          "type": "number",
          "required": true,
          "placeholder": "18"
        },
        {
          "name": "return_temperature_c",
          "label": "Température retour °C",
          "type": "number",
          "required": true,
          "placeholder": "30"
        },
        {
          "name": "label",
          "label": "Libellé",
          "placeholder": "Allée froide A"
        }
      ]
    },
    {
      "id": "dcim-power-reservation",
      "label": "Réserver la puissance équipement",
      "method": "POST",
      "path": "/v1/dcim/power-reservations",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "asset_tag",
          "label": "Numéro d’actif",
          "required": true,
          "placeholder": "PAR-SRV-001"
        },
        {
          "name": "circuit_id",
          "label": "Identifiant circuit",
          "required": true,
          "placeholder": "CIR-A-R01"
        },
        {
          "name": "expected_watts",
          "label": "Puissance attendue watts",
          "type": "number",
          "required": true,
          "placeholder": "600"
        },
        {
          "name": "label",
          "label": "Libellé",
          "placeholder": "Réservation alimentation principale"
        }
      ]
    },
    {
      "id": "field-sheet-list",
      "label": "Lister les fiches d’intervention",
      "method": "GET",
      "path": "/v1/field-operation-sheets",
      "query": [
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "ready",
            "in-progress",
            "completed",
            "cancelled"
          ]
        },
        {
          "name": "target_type",
          "label": "Type de cible",
          "type": "select",
          "options": [
            "equipment",
            "rack",
            "cable",
            "power-device",
            "certificate"
          ]
        },
        {
          "name": "site",
          "label": "Site"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100",
          "min": 1,
          "max": 500
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "field-sheet-get",
      "label": "Consulter une fiche d’intervention",
      "method": "GET",
      "path": "/v1/field-operation-sheets/get",
      "query": [
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        }
      ]
    },
    {
      "id": "field-sheet-generate",
      "label": "Générer une fiche d’intervention",
      "method": "POST",
      "path": "/v1/field-operation-sheets/generate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "target_type",
          "label": "Type de cible",
          "type": "select",
          "options": [
            "equipment",
            "rack",
            "cable",
            "power-device",
            "certificate"
          ],
          "required": true
        },
        {
          "name": "target_id",
          "label": "Identifiant cible",
          "required": true
        },
        {
          "name": "title",
          "label": "Titre",
          "required": true
        },
        {
          "name": "purpose",
          "label": "Objet de l’intervention",
          "type": "textarea",
          "rows": 4,
          "required": true
        },
        {
          "name": "owner",
          "label": "Responsable",
          "required": true
        },
        {
          "name": "operator",
          "label": "Intervenant",
          "required": true
        },
        {
          "name": "source_object_key",
          "label": "Clé objet RSOT"
        },
        {
          "name": "site",
          "label": "Site"
        },
        {
          "name": "building",
          "label": "Bâtiment"
        },
        {
          "name": "room",
          "label": "Salle"
        },
        {
          "name": "location_target_type",
          "label": "Type de cible physique",
          "type": "select",
          "options": [
            "equipment",
            "rack",
            "cable",
            "power-device"
          ]
        },
        {
          "name": "location_target_id",
          "label": "Identifiant cible physique"
        }
      ]
    },
    {
      "id": "field-lock-acquire",
      "label": "Verrouiller la cible",
      "method": "POST",
      "path": "/v1/intervention-locks/acquire",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "ttl_seconds",
          "label": "Durée du verrou (secondes)",
          "type": "number",
          "defaultValue": "3600",
          "min": 60,
          "max": 86400
        }
      ]
    },
    {
      "id": "field-operation-start",
      "label": "Démarrer l’intervention",
      "method": "POST",
      "path": "/v1/field-operation-sheets/start",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        }
      ]
    },
    {
      "id": "field-checklist-record",
      "label": "Renseigner une étape de checklist",
      "method": "POST",
      "path": "/v1/field-operation-sheets/checklist",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        },
        {
          "name": "item_id",
          "label": "ID étape",
          "required": true
        },
        {
          "name": "result",
          "label": "Résultat",
          "type": "select",
          "options": [
            "passed",
            "failed",
            "not-applicable"
          ],
          "required": true
        },
        {
          "name": "operator_note",
          "label": "Note intervenant",
          "type": "textarea",
          "rows": 3
        }
      ]
    },
    {
      "id": "field-evidence-attach",
      "label": "Joindre une preuve terrain",
      "method": "POST",
      "path": "/v1/field-evidence/attach",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        },
        {
          "name": "phase",
          "label": "Phase",
          "type": "select",
          "options": [
            "before",
            "after"
          ],
          "required": true
        },
        {
          "name": "evidence_file",
          "label": "Photo ou document",
          "type": "file",
          "accept": "image/jpeg,image/png,image/webp,application/pdf",
          "capture": "environment",
          "required": true
        },
        {
          "name": "caption",
          "label": "Description de la preuve",
          "type": "textarea",
          "rows": 3,
          "required": true
        }
      ]
    },
    {
      "id": "field-evidence-list",
      "label": "Lister les preuves terrain",
      "method": "GET",
      "path": "/v1/field-evidence",
      "query": [
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        }
      ]
    },
    {
      "id": "field-evidence-validate",
      "label": "Valider une preuve terrain",
      "method": "POST",
      "path": "/v1/field-evidence/validate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "evidence_id",
          "label": "ID preuve",
          "required": true
        }
      ]
    },
    {
      "id": "field-operation-complete",
      "label": "Clôturer l’intervention",
      "method": "POST",
      "path": "/v1/field-operation-sheets/complete",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        }
      ]
    },
    {
      "id": "field-operation-cancel",
      "label": "Annuler l’intervention",
      "method": "POST",
      "path": "/v1/field-operation-sheets/cancel",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        }
      ]
    },
    {
      "id": "field-qr-verify",
      "label": "Vérifier un QR code terrain",
      "method": "POST",
      "path": "/v1/qr-codes/verify",
      "body": [
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        },
        {
          "name": "payload",
          "label": "Contenu QR",
          "type": "textarea",
          "rows": 4,
          "required": true
        }
      ]
    },
    {
      "id": "field-lock-release",
      "label": "Libérer le verrou terrain",
      "method": "POST",
      "path": "/v1/intervention-locks/release",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "lock_id",
          "label": "ID verrou",
          "required": true
        }
      ]
    },
    {
      "id": "field-offline-create",
      "label": "Créer un paquet hors ligne",
      "method": "POST",
      "path": "/v1/offline-sync-packages/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "sheet_id",
          "label": "ID fiche",
          "required": true
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "ttl_seconds",
          "label": "Validité hors ligne (secondes)",
          "type": "number",
          "defaultValue": "86400",
          "min": 300,
          "max": 604800
        }
      ]
    },
    {
      "id": "field-offline-list",
      "label": "Lister les paquets hors ligne",
      "method": "GET",
      "path": "/v1/offline-sync-packages",
      "query": [
        {
          "name": "sheet_id",
          "label": "ID fiche"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100",
          "min": 1,
          "max": 500
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "field-offline-get",
      "label": "Consulter un paquet hors ligne",
      "method": "GET",
      "path": "/v1/offline-sync-packages/get",
      "query": [
        {
          "name": "package_id",
          "label": "ID paquet",
          "required": true
        },
        {
          "name": "include_payload",
          "label": "Inclure le contenu",
          "type": "boolean",
          "defaultValue": "true"
        }
      ]
    },
    {
      "id": "field-offline-sync",
      "label": "Synchroniser un paquet hors ligne",
      "method": "POST",
      "path": "/v1/offline-sync-packages/synchronize",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "package_id",
          "label": "ID paquet",
          "required": true
        },
        {
          "name": "payload_sha256",
          "label": "Empreinte SHA-256 du paquet",
          "required": true,
          "maxLength": 64
        }
      ]
    },
    {
      "id": "greenops-source-create",
      "label": "Enregistrer une source de mesure",
      "method": "POST",
      "path": "/v1/greenops/measurement-sources/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Code source",
          "required": true
        },
        {
          "name": "name",
          "label": "Nom source",
          "required": true
        },
        {
          "name": "source_type",
          "label": "Type de source",
          "required": true
        },
        {
          "name": "owner",
          "label": "Responsable",
          "required": true
        },
        {
          "name": "active",
          "label": "Source active",
          "type": "boolean",
          "defaultValue": "true"
        }
      ]
    },
    {
      "id": "greenops-sources",
      "label": "Lister les sources de mesure",
      "method": "GET",
      "path": "/v1/greenops/measurement-sources",
      "query": [
        {
          "name": "active_only",
          "label": "Sources actives uniquement",
          "type": "boolean",
          "defaultValue": "false"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "greenops-policy-upsert",
      "label": "Configurer la politique GreenOps d’un site",
      "method": "POST",
      "path": "/v1/greenops/policies/upsert",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site_code",
          "label": "Site",
          "required": true
        },
        {
          "name": "default_pue",
          "label": "PUE par défaut",
          "type": "number",
          "step": "0.000001",
          "required": true
        },
        {
          "name": "energy_cost_per_kwh",
          "label": "Coût énergie par kWh",
          "type": "number",
          "step": "0.000001",
          "required": true
        },
        {
          "name": "currency",
          "label": "Devise ISO-4217",
          "required": true,
          "maxLength": 3
        },
        {
          "name": "carbon_factor_code",
          "label": "Code facteur carbone",
          "required": true
        },
        {
          "name": "underutilized_percent",
          "label": "Seuil de sous-utilisation (%)",
          "type": "number",
          "defaultValue": "20",
          "min": 0,
          "max": 100
        },
        {
          "name": "warning_capacity_percent",
          "label": "Seuil capacité avertissement (%)",
          "type": "number",
          "defaultValue": "80",
          "min": 0,
          "max": 100
        },
        {
          "name": "critical_capacity_percent",
          "label": "Seuil capacité critique (%)",
          "type": "number",
          "defaultValue": "90",
          "min": 0,
          "max": 100
        },
        {
          "name": "minimum_samples",
          "label": "Échantillons minimaux",
          "type": "number",
          "defaultValue": "3",
          "min": 2,
          "max": 1000
        }
      ]
    },
    {
      "id": "greenops-policy-get",
      "label": "Consulter la politique GreenOps",
      "method": "GET",
      "path": "/v1/greenops/policies/get",
      "query": [
        {
          "name": "site_code",
          "label": "Site",
          "required": true
        }
      ]
    },
    {
      "id": "greenops-factor-create",
      "label": "Enregistrer un facteur carbone",
      "method": "POST",
      "path": "/v1/greenops/carbon-factors/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Code facteur",
          "required": true
        },
        {
          "name": "region",
          "label": "Région",
          "required": true
        },
        {
          "name": "grams_co2e_per_kwh",
          "label": "gCO₂e par kWh",
          "type": "number",
          "step": "0.000001",
          "required": true
        },
        {
          "name": "source_name",
          "label": "Source du facteur",
          "required": true
        },
        {
          "name": "source_uri",
          "label": "URL de provenance",
          "type": "url"
        },
        {
          "name": "period_start",
          "label": "Début de validité",
          "type": "date",
          "required": true
        },
        {
          "name": "period_end",
          "label": "Fin de validité",
          "type": "date",
          "required": true
        }
      ]
    },
    {
      "id": "greenops-factors",
      "label": "Lister les facteurs carbone",
      "method": "GET",
      "path": "/v1/greenops/carbon-factors",
      "query": [
        {
          "name": "code",
          "label": "Code facteur"
        },
        {
          "name": "region",
          "label": "Région"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "greenops-measurement-ingest",
      "label": "Ingérer une mesure énergétique",
      "method": "POST",
      "path": "/v1/greenops/energy-measurements/ingest",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "source_code",
          "label": "Code source",
          "required": true
        },
        {
          "name": "kind",
          "label": "Nature de la mesure",
          "type": "select",
          "options": [
            "observed",
            "estimated"
          ],
          "required": true
        },
        {
          "name": "scope",
          "label": "Périmètre",
          "type": "select",
          "options": [
            "site",
            "room",
            "rack",
            "pdu",
            "asset",
            "application"
          ],
          "required": true
        },
        {
          "name": "scope_key",
          "label": "Identifiant du périmètre",
          "required": true
        },
        {
          "name": "site_code",
          "label": "Site",
          "required": true
        },
        {
          "name": "application_key",
          "label": "Application associée"
        },
        {
          "name": "period_start",
          "label": "Début de mesure",
          "type": "datetime-local",
          "required": true
        },
        {
          "name": "period_end",
          "label": "Fin de mesure",
          "type": "datetime-local",
          "required": true
        },
        {
          "name": "energy_kwh",
          "label": "Énergie (kWh)",
          "type": "number",
          "step": "0.000001",
          "required": true
        },
        {
          "name": "it_energy_kwh",
          "label": "Énergie IT (kWh)",
          "type": "number",
          "step": "0.000001"
        },
        {
          "name": "facility_energy_kwh",
          "label": "Énergie totale site (kWh)",
          "type": "number",
          "step": "0.000001"
        },
        {
          "name": "utilization_percent",
          "label": "Utilisation (%)",
          "type": "number",
          "min": 0,
          "max": 100,
          "step": "0.0001"
        },
        {
          "name": "energy_capacity_percent",
          "label": "Capacité énergie utilisée (%)",
          "type": "number",
          "min": 0,
          "max": 100,
          "step": "0.0001"
        },
        {
          "name": "cooling_capacity_percent",
          "label": "Capacité refroidissement utilisée (%)",
          "type": "number",
          "min": 0,
          "max": 100,
          "step": "0.0001"
        },
        {
          "name": "space_capacity_percent",
          "label": "Capacité espace utilisée (%)",
          "type": "number",
          "min": 0,
          "max": 100,
          "step": "0.0001"
        },
        {
          "name": "weight_capacity_percent",
          "label": "Capacité poids utilisée (%)",
          "type": "number",
          "min": 0,
          "max": 100,
          "step": "0.0001"
        },
        {
          "name": "metadata",
          "label": "Métadonnées JSON sans secret",
          "type": "json",
          "defaultValue": "{}"
        }
      ]
    },
    {
      "id": "greenops-measurements",
      "label": "Lister les mesures énergétiques",
      "method": "GET",
      "path": "/v1/greenops/energy-measurements",
      "query": [
        {
          "name": "period_start",
          "label": "Début de période",
          "type": "datetime-local"
        },
        {
          "name": "period_end",
          "label": "Fin de période",
          "type": "datetime-local"
        },
        {
          "name": "site_code",
          "label": "Site"
        },
        {
          "name": "scope",
          "label": "Périmètre",
          "type": "select",
          "options": [
            "site",
            "room",
            "rack",
            "pdu",
            "asset",
            "application"
          ]
        },
        {
          "name": "scope_key",
          "label": "Identifiant du périmètre"
        },
        {
          "name": "kind",
          "label": "Nature",
          "type": "select",
          "options": [
            "observed",
            "estimated"
          ]
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "greenops-report-generate",
      "label": "Générer un rapport de durabilité",
      "method": "POST",
      "path": "/v1/greenops/reports/generate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "site_code",
          "label": "Site",
          "required": true
        },
        {
          "name": "period_start",
          "label": "Début de période",
          "type": "date",
          "required": true
        },
        {
          "name": "period_end",
          "label": "Fin de période",
          "type": "date",
          "required": true
        },
        {
          "name": "scope",
          "label": "Périmètre",
          "type": "select",
          "options": [
            "site",
            "room",
            "rack",
            "pdu",
            "asset",
            "application"
          ],
          "defaultValue": "site"
        },
        {
          "name": "scope_key",
          "label": "Identifiant du périmètre"
        }
      ]
    },
    {
      "id": "greenops-report-get",
      "label": "Consulter un rapport de durabilité",
      "method": "GET",
      "path": "/v1/greenops/reports/get",
      "query": [
        {
          "name": "report_id",
          "label": "ID rapport",
          "required": true
        }
      ]
    },
    {
      "id": "greenops-reports",
      "label": "Lister les rapports de durabilité",
      "method": "GET",
      "path": "/v1/greenops/reports",
      "query": [
        {
          "name": "site_code",
          "label": "Site"
        },
        {
          "name": "scope",
          "label": "Périmètre"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "greenops-report-export",
      "label": "Exporter un rapport de durabilité",
      "method": "GET",
      "path": "/v1/greenops/reports/export",
      "download": true,
      "downloadFilename": "openinfra-greenops-report.json",
      "query": [
        {
          "name": "report_id",
          "label": "ID rapport",
          "required": true
        },
        {
          "name": "format",
          "label": "Format",
          "type": "select",
          "options": [
            "json",
            "csv"
          ],
          "defaultValue": "json"
        }
      ]
    },
    {
      "id": "greenops-anomalies",
      "label": "Lister les anomalies énergétiques",
      "method": "GET",
      "path": "/v1/greenops/anomalies",
      "query": [
        {
          "name": "site_code",
          "label": "Site"
        },
        {
          "name": "severity",
          "label": "Sévérité",
          "type": "select",
          "options": [
            "info",
            "warning",
            "error",
            "critical"
          ]
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "greenops-forecasts",
      "label": "Lister les prévisions de capacité",
      "method": "GET",
      "path": "/v1/greenops/capacity-forecasts",
      "query": [
        {
          "name": "site_code",
          "label": "Site"
        },
        {
          "name": "dimension",
          "label": "Dimension",
          "type": "select",
          "options": [
            "energy",
            "cooling",
            "space",
            "weight"
          ]
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "greenops-candidates",
      "label": "Lister les recommandations de consolidation",
      "method": "GET",
      "path": "/v1/greenops/consolidation-candidates",
      "query": [
        {
          "name": "site_code",
          "label": "Site"
        },
        {
          "name": "risk_level",
          "label": "Niveau de risque",
          "type": "select",
          "options": [
            "info",
            "warning",
            "error",
            "critical"
          ]
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "greenops-scores",
      "label": "Lister les scores GreenOps",
      "method": "GET",
      "path": "/v1/greenops/green-scores",
      "query": [
        {
          "name": "scope",
          "label": "Périmètre"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "dcim-digital-twin",
      "label": "Jumeau numérique salle",
      "method": "GET",
      "path": "/v1/dcim/digital-twin",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true,
          "placeholder": "MMR1"
        }
      ]
    },
    {
      "id": "dcim-energy-cooling-capacity",
      "label": "Capacité énergie/refroidissement",
      "method": "GET",
      "path": "/v1/dcim/energy-cooling-capacity",
      "query": [
        {
          "name": "site",
          "label": "Site",
          "required": true,
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "required": true,
          "placeholder": "BAT-A"
        },
        {
          "name": "room",
          "label": "Salle",
          "required": true,
          "placeholder": "MMR1"
        },
        {
          "name": "rack",
          "label": "Rack",
          "required": true,
          "placeholder": "R01"
        }
      ]
    },
    {
      "id": "dcim-placement-recommendations",
      "label": "Recommander un placement en rack",
      "method": "GET",
      "path": "/v1/dcim/placement-recommendations",
      "query": [
        {"name": "site", "label": "Site", "required": true, "placeholder": "PAR1"},
        {"name": "building", "label": "Bâtiment", "required": true, "placeholder": "BAT-A"},
        {"name": "room", "label": "Salle", "required": true, "placeholder": "MMR1"},
        {"name": "u_height", "label": "Hauteur requise (U)", "type": "number", "required": true, "min": 1, "max": 60},
        {"name": "required_power_watts", "label": "Puissance requise (W)", "type": "number", "required": true, "min": 1, "max": 1000000},
        {"name": "required_cooling_watts", "label": "Refroidissement requis (W)", "type": "number", "min": 1, "max": 10000000},
        {"name": "required_power_feeds", "label": "Alimentations requises", "type": "select", "options": ["1", "2"], "defaultValue": "1"},
        {"name": "preferred_face", "label": "Face préférée", "type": "select", "options": ["front", "rear"]},
        {"name": "zone", "label": "Zone"},
        {"name": "limit", "label": "Nombre maximal de recommandations", "type": "number", "defaultValue": "10", "min": 1, "max": 100}
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;

export const dcimReferenceLabels = {
  "site": "Site",
  "site_code": "Site",
  "building": "Bâtiment",
  "building_code": "Bâtiment",
  "floor": "Étage",
  "floor_code": "Étage",
  "room": "Salle",
  "room_code": "Salle",
  "zone": "Zone",
  "zone_code": "Zone",
  "rack": "Rack",
  "row": "Ligne salle",
  "column": "Colonne salle"
};
