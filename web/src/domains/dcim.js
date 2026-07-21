const moduleDefinition = {
  "id": "dcim",
  "label": "DCIM",
  "icon": "home",
  "operations": [
    {
      "id": "dcim-sites",
      "label": "Lister les sites DCIM",
      "path": "/v1/dcim/sites",
      "method": "GET",
      "fields": [
        "Inclure retirés"
      ]
    },
    {
      "id": "dcim-site",
      "label": "Consulter un site DCIM",
      "path": "/v1/dcim/site",
      "method": "GET",
      "fields": [
        "Site"
      ]
    },
    {
      "id": "multisite-grant-upsert",
      "label": "Affecter un accès à un site",
      "path": "/v1/multisite/site-access/grants/upsert",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/multisite/site-access/grants/revoke",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/multisite/site-access/grants",
      "method": "GET",
      "fields": [
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
      "id": "multisite-sites",
      "label": "Lister les sites accessibles",
      "path": "/v1/multisite/sites",
      "method": "GET",
      "fields": [
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
      "path": "/v1/multisite/reports/generate",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/multisite/reports",
      "method": "GET",
      "fields": [
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
      "id": "multisite-report-get",
      "label": "Consulter un rapport multisite",
      "path": "/v1/multisite/reports/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/multisite/disaster-recovery/plans/configure",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
          "min": 1,
          "max": 86400
        },
        {
          "name": "rto_seconds",
          "label": "RTO (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "1800",
          "min": 1,
          "max": 604800
        },
        {
          "name": "max_backup_age_seconds",
          "label": "Âge maximal sauvegarde (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "86400",
          "min": 60,
          "max": 2592000
        }
      ]
    },
    {
      "id": "multisite-dr-plan-disable",
      "label": "Désactiver un plan de reprise multisite",
      "path": "/v1/multisite/disaster-recovery/plans/disable",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/multisite/disaster-recovery/plans",
      "method": "GET",
      "fields": [
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
      "id": "multisite-dr-plan-get",
      "label": "Consulter un plan de reprise multisite",
      "path": "/v1/multisite/disaster-recovery/plans/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/multisite/disaster-recovery/drills/execute",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
          "min": 0
        },
        {
          "name": "backup_age_seconds",
          "label": "Âge sauvegarde (secondes)",
          "type": "number",
          "required": true,
          "min": 0
        },
        {
          "name": "measured_rto_seconds",
          "label": "RTO mesuré (secondes)",
          "type": "number",
          "required": true,
          "min": 0
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
      "path": "/v1/multisite/disaster-recovery/drills",
      "method": "GET",
      "fields": [
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
      "id": "multisite-dr-drill-get",
      "label": "Consulter un exercice de reprise multisite",
      "path": "/v1/multisite/disaster-recovery/drills/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/multisite/regional-discovery/routes/configure",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/multisite/regional-discovery/routes/disable",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/multisite/regional-discovery/routes",
      "method": "GET",
      "fields": [
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
      "id": "multisite-route-get",
      "label": "Consulter une route Discovery régionale",
      "path": "/v1/multisite/regional-discovery/routes/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/multisite/regional-discovery/jobs/route",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
          "min": 1,
          "max": 10
        }
      ]
    },
    {
      "id": "dcim-site-create",
      "label": "Créer un site DCIM",
      "path": "/v1/dcim/site/create",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Code site",
        "Nom site",
        "Pays ISO-2",
        "Ville",
        "Région"
      ]
    },
    {
      "id": "dcim-site-update",
      "label": "Modifier un site DCIM",
      "path": "/v1/dcim/site/update",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Nom site",
        "Pays ISO-2",
        "Ville",
        "Région",
        "Statut"
      ]
    },
    {
      "id": "dcim-site-delete",
      "label": "Retirer un site DCIM",
      "path": "/v1/dcim/site/delete",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site"
      ]
    },
    {
      "id": "dcim-buildings",
      "label": "Lister les bâtiments",
      "path": "/v1/dcim/buildings",
      "method": "GET",
      "fields": [
        "Site",
        "Inclure retirés"
      ]
    },
    {
      "id": "dcim-building",
      "label": "Consulter un bâtiment",
      "path": "/v1/dcim/building",
      "method": "GET",
      "fields": [
        "Site",
        "Code bâtiment"
      ]
    },
    {
      "id": "dcim-building-create",
      "label": "Créer un bâtiment",
      "path": "/v1/dcim/building/create",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Code bâtiment",
        "Nom bâtiment"
      ]
    },
    {
      "id": "dcim-building-update",
      "label": "Modifier un bâtiment",
      "path": "/v1/dcim/building/update",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Code bâtiment",
        "Nom bâtiment",
        "Statut"
      ]
    },
    {
      "id": "dcim-building-delete",
      "label": "Retirer un bâtiment",
      "path": "/v1/dcim/building/delete",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Code bâtiment"
      ]
    },
    {
      "id": "dcim-floors",
      "label": "Lister les étages",
      "path": "/v1/dcim/floors",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Inclure retirés"
      ]
    },
    {
      "id": "dcim-floor",
      "label": "Consulter un étage",
      "path": "/v1/dcim/floor",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Code étage"
      ]
    },
    {
      "id": "dcim-rooms-list",
      "label": "Lister les salles",
      "path": "/v1/dcim/rooms",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Inclure retirés"
      ]
    },
    {
      "id": "dcim-room",
      "label": "Consulter une salle",
      "path": "/v1/dcim/room",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Code salle"
      ]
    },
    {
      "id": "dcim-room-create",
      "label": "Créer une salle",
      "path": "/v1/dcim/room/create",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Étage",
        "Code salle",
        "Nom salle",
        "Lignes salle",
        "Colonnes salle"
      ]
    },
    {
      "id": "dcim-room-update",
      "label": "Modifier une salle",
      "path": "/v1/dcim/room/update",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Code salle",
        "Nom salle",
        "Lignes salle",
        "Colonnes salle",
        "Statut"
      ]
    },
    {
      "id": "dcim-room-delete",
      "label": "Retirer une salle",
      "path": "/v1/dcim/room/delete",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Code salle"
      ]
    },
    {
      "id": "dcim-zones",
      "label": "Lister les zones",
      "path": "/v1/dcim/zones",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Salle",
        "Inclure retirés"
      ]
    },
    {
      "id": "dcim-zone",
      "label": "Consulter une zone",
      "path": "/v1/dcim/zone",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Salle",
        "Code zone"
      ]
    },
    {
      "id": "dcim-zone-create",
      "label": "Créer une zone",
      "path": "/v1/dcim/zone/create",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Salle",
        "Code zone",
        "Nom zone",
        "Lignes zone",
        "Colonnes zone"
      ]
    },
    {
      "id": "dcim-zone-update",
      "label": "Modifier une zone",
      "path": "/v1/dcim/zone/update",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Salle",
        "Code zone",
        "Nom zone",
        "Lignes zone",
        "Colonnes zone",
        "Statut"
      ]
    },
    {
      "id": "dcim-zone-delete",
      "label": "Retirer une zone",
      "path": "/v1/dcim/zone/delete",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Salle",
        "Code zone"
      ]
    },
    {
      "id": "dcim-topology-catalog",
      "label": "Catalogue dépendances DCIM",
      "path": "/v1/dcim/topology-catalog",
      "method": "GET",
      "fields": [
        "Inclure retirés"
      ]
    },
    {
      "id": "dcim-locate-equipment",
      "label": "Localiser un équipement",
      "path": "/v1/dcim/locations",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Numéro d’actif",
        "Nom équipement",
        "Site",
        "Bâtiment",
        "Étage",
        "Salle",
        "Zone",
        "Ligne salle",
        "Colonne salle",
        "Rack",
        "Position U",
        "Face rack",
        "Hauteur U",
        "Coordonnée X",
        "Coordonnée Y",
        "Coordonnée Z"
      ]
    },
    {
      "id": "dcim-rack-capacity",
      "label": "Capacité rack",
      "path": "/v1/dcim/rack-capacity",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Salle",
        "Rack"
      ]
    },
    {
      "id": "dcim-room-plan",
      "label": "Plan de salle",
      "path": "/v1/dcim/room-plan",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Salle",
        "Format rendu"
      ]
    },
    {
      "id": "dcim-rack-elevation",
      "label": "Élévation rack",
      "path": "/v1/dcim/rack-elevation",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Salle",
        "Rack",
        "Face rack",
        "Format rendu"
      ]
    },
    {
      "id": "dcim-patch-panel",
      "label": "Définir un panneau de brassage",
      "path": "/v1/dcim/patch-panels",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Salle",
        "Rack",
        "Panneau de brassage",
        "Face rack",
        "Position U",
        "Hauteur U",
        "Nombre de ports",
        "Connecteur",
        "Média câble",
        "Libellé",
        "Préfixe ports"
      ]
    },
    {
      "id": "dcim-port",
      "label": "Définir un port DCIM",
      "path": "/v1/dcim/ports",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Type propriétaire",
        "Code propriétaire",
        "Nom port",
        "Connecteur",
        "Média câble",
        "Site",
        "Bâtiment",
        "Salle",
        "Port actif"
      ]
    },
    {
      "id": "dcim-cable",
      "label": "Connecter un câble",
      "path": "/v1/dcim/cables",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Identifiant câble",
        "Type propriétaire A",
        "Code propriétaire A",
        "Port A",
        "Type propriétaire B",
        "Code propriétaire B",
        "Port B",
        "Média câble",
        "Statut câble",
        "Chemin câble",
        "Longueur m",
        "Libellé"
      ]
    },
    {
      "id": "dcim-power-device",
      "label": "Définir un équipement électrique",
      "path": "/v1/dcim/power-devices",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Code équipement électrique",
        "Type équipement électrique",
        "Site",
        "Bâtiment",
        "Salle",
        "Rack",
        "Chaîne électrique",
        "Capacité watts",
        "Derating %",
        "Source amont",
        "Tension sortie V",
        "Libellé"
      ]
    },
    {
      "id": "dcim-power-circuit",
      "label": "Définir un circuit électrique",
      "path": "/v1/dcim/power-circuits",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Identifiant circuit",
        "Source électrique",
        "Site",
        "Bâtiment",
        "Salle",
        "Rack",
        "Chaîne électrique",
        "Capacité watts",
        "Calibre disjoncteur A",
        "Groupe redondance",
        "Libellé"
      ]
    },
    {
      "id": "dcim-cooling-zone",
      "label": "Définir une zone de refroidissement",
      "path": "/v1/dcim/cooling-zones",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Site",
        "Bâtiment",
        "Salle",
        "Zone froid/chaud",
        "Rôle refroidissement",
        "Capacité froid watts",
        "Température soufflage °C",
        "Température retour °C",
        "Libellé"
      ]
    },
    {
      "id": "dcim-power-reservation",
      "label": "Réserver la puissance équipement",
      "path": "/v1/dcim/power-reservations",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Numéro d’actif",
        "Identifiant circuit",
        "Puissance attendue watts",
        "Libellé"
      ]
    },
    {
      "id": "field-sheet-list",
      "label": "Lister les fiches d’intervention",
      "path": "/v1/field-operation-sheets",
      "method": "GET",
      "fields": [
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
      "path": "/v1/field-operation-sheets/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/field-operation-sheets/generate",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/intervention-locks/acquire",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/field-operation-sheets/start",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/field-operation-sheets/checklist",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/field-evidence/attach",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/field-evidence",
      "method": "GET",
      "fields": [
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
      "path": "/v1/field-evidence/validate",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/field-operation-sheets/complete",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/field-operation-sheets/cancel",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/qr-codes/verify",
      "method": "POST",
      "fields": [
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
      "path": "/v1/intervention-locks/release",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/offline-sync-packages/create",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/offline-sync-packages",
      "method": "GET",
      "fields": [
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
      "path": "/v1/offline-sync-packages/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/offline-sync-packages/synchronize",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/greenops/measurement-sources/create",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/greenops/measurement-sources",
      "method": "GET",
      "fields": [
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
      "id": "greenops-policy-upsert",
      "label": "Configurer la politique GreenOps d’un site",
      "path": "/v1/greenops/policies/upsert",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/greenops/policies/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/greenops/carbon-factors/create",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/greenops/carbon-factors",
      "method": "GET",
      "fields": [
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
      "id": "greenops-measurement-ingest",
      "label": "Ingérer une mesure énergétique",
      "path": "/v1/greenops/energy-measurements/ingest",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/greenops/energy-measurements",
      "method": "GET",
      "fields": [
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
      "id": "greenops-report-generate",
      "label": "Générer un rapport de durabilité",
      "path": "/v1/greenops/reports/generate",
      "method": "POST",
      "fields": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true
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
      "path": "/v1/greenops/reports/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/greenops/reports",
      "method": "GET",
      "fields": [
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
      "id": "greenops-report-export",
      "label": "Exporter un rapport de durabilité",
      "path": "/v1/greenops/reports/export",
      "method": "GET",
      "download": true,
      "fields": [
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
      "path": "/v1/greenops/anomalies",
      "method": "GET",
      "fields": [
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
      "id": "greenops-forecasts",
      "label": "Lister les prévisions de capacité",
      "path": "/v1/greenops/capacity-forecasts",
      "method": "GET",
      "fields": [
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
      "id": "greenops-candidates",
      "label": "Lister les recommandations de consolidation",
      "path": "/v1/greenops/consolidation-candidates",
      "method": "GET",
      "fields": [
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
      "id": "greenops-scores",
      "label": "Lister les scores GreenOps",
      "path": "/v1/greenops/green-scores",
      "method": "GET",
      "fields": [
        {
          "name": "scope",
          "label": "Périmètre"
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
      "id": "dcim-digital-twin",
      "label": "Jumeau numérique salle",
      "path": "/v1/dcim/digital-twin",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Salle"
      ]
    },
    {
      "id": "dcim-energy-cooling-capacity",
      "label": "Capacité énergie/refroidissement",
      "path": "/v1/dcim/energy-cooling-capacity",
      "method": "GET",
      "fields": [
        "Site",
        "Bâtiment",
        "Salle",
        "Rack"
      ]
    },
    {
      "id": "dcim-placement-recommendations",
      "label": "Recommander un placement en rack",
      "path": "/v1/dcim/placement-recommendations",
      "method": "GET",
      "fields": [
        {"name": "site", "label": "Site", "required": true},
        {"name": "building", "label": "Bâtiment", "required": true},
        {"name": "room", "label": "Salle", "required": true},
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
