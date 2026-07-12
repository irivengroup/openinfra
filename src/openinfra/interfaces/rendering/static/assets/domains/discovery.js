const moduleDefinition = {
  "id": "discovery",
  "label": "Discovery",
  "icon": "activity",
  "description": "Collecte backend locale en Lite/Pro ; agents proxy collectors Enterprise uniquement en topologie étoile.",
  "operations": [
    {
      "id": "discovery-evidence-list",
      "label": "Lister les preuves immuables",
      "method": "GET",
      "path": "/v1/discovery/evidence-list",
      "query": [
        {
          "name": "object_key",
          "label": "Clé objet"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "discovery-evidence",
      "label": "Voir une preuve immuable",
      "method": "GET",
      "path": "/v1/discovery/evidence",
      "query": [
        {
          "name": "evidence_id",
          "label": "ID preuve",
          "required": true
        }
      ]
    },
    {
      "id": "discovery-evidence-submit",
      "label": "Enregistrer une preuve Discovery",
      "method": "POST",
      "path": "/v1/discovery/evidence",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "evidence_id",
          "label": "ID preuve imposé"
        },
        {
          "name": "object_key",
          "label": "Clé objet",
          "required": true,
          "placeholder": "server/srv-app-01"
        },
        {
          "name": "object_kind",
          "label": "Type objet",
          "required": true,
          "placeholder": "server"
        },
        {
          "name": "source",
          "label": "Source",
          "required": true,
          "type": "select",
          "options": [
            "snmp",
            "ssh",
            "winrm",
            "vmware",
            "proxmox",
            "hyperv",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "openstack",
            "cloud",
            "import",
            "manual"
          ]
        },
        {
          "name": "source_ref",
          "label": "Référence source",
          "required": true,
          "placeholder": "vcenter-par1"
        },
        {
          "name": "scope",
          "label": "Scope",
          "required": true,
          "placeholder": "site/par1"
        },
        {
          "name": "external_id",
          "label": "ID externe",
          "required": true
        },
        {
          "name": "confidence",
          "label": "Confiance (0 à 1)",
          "required": true,
          "type": "number",
          "defaultValue": "0.9"
        },
        {
          "name": "observed_at",
          "label": "Observé le (ISO-8601)"
        },
        {
          "name": "payload",
          "label": "Preuve JSON sans secret",
          "required": true,
          "type": "json",
          "defaultValue": "{}"
        }
      ]
    },
    {
      "id": "discovery-reconciliation-list",
      "label": "Lister les rapprochements",
      "method": "GET",
      "path": "/v1/discovery/reconciliation-list",
      "query": [
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "ready",
            "conflict",
            "resolved"
          ]
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "discovery-reconciliation",
      "label": "Voir un rapprochement",
      "method": "GET",
      "path": "/v1/discovery/reconciliation",
      "query": [
        {
          "name": "case_id",
          "label": "ID rapprochement",
          "required": true
        }
      ]
    },
    {
      "id": "discovery-reconcile",
      "label": "Rapprocher plusieurs preuves",
      "method": "POST",
      "path": "/v1/discovery/reconciliation",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "object_key",
          "label": "Clé objet",
          "required": true
        },
        {
          "name": "evidence_ids",
          "label": "IDs preuves",
          "required": true,
          "type": "csv"
        },
        {
          "name": "max_age_seconds",
          "label": "Âge maximal (secondes)",
          "type": "number",
          "defaultValue": "86400"
        }
      ]
    },
    {
      "id": "discovery-reconciliation-resolve",
      "label": "Résoudre les conflits",
      "method": "POST",
      "path": "/v1/discovery/reconciliation/resolve",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "case_id",
          "label": "ID rapprochement",
          "required": true
        },
        {
          "name": "selected_evidence_by_path",
          "label": "Sélections par chemin JSON",
          "required": true,
          "type": "json",
          "defaultValue": "{}"
        },
        {
          "name": "justification",
          "label": "Justification",
          "required": true
        }
      ]
    },
    {
      "id": "discovery-protocol-profiles",
      "label": "Lister les profils protocoles",
      "method": "GET",
      "path": "/v1/discovery/protocol-profiles",
      "query": [
        {
          "name": "include_inactive",
          "label": "Inclure inactifs",
          "type": "boolean"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "discovery-protocol-profile-create",
      "label": "Créer un profil SNMP/SSH/WinRM",
      "method": "POST",
      "path": "/v1/discovery/protocol-profile/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom profil",
          "required": true,
          "placeholder": "SNMPv3 PAR1 Core"
        },
        {
          "name": "protocol",
          "label": "Protocole",
          "required": true,
          "type": "select",
          "options": [
            "snmp",
            "ssh",
            "winrm"
          ]
        },
        {
          "name": "scope",
          "label": "Scope",
          "required": true,
          "placeholder": "site/par1"
        },
        {
          "name": "credential_secret_ref",
          "label": "Référence secret vault",
          "required": true,
          "placeholder": "vault://openinfra/discovery/snmp/par1"
        },
        {
          "name": "port",
          "label": "Port",
          "type": "number"
        },
        {
          "name": "timeout_seconds",
          "label": "Timeout secondes",
          "type": "number",
          "defaultValue": "30"
        },
        {
          "name": "max_concurrency",
          "label": "Concurrence max",
          "type": "number",
          "defaultValue": "4"
        },
        {
          "name": "rate_limit_per_minute",
          "label": "Rate limit/min",
          "type": "number",
          "defaultValue": "120"
        },
        {
          "name": "retry_count",
          "label": "Tentatives",
          "type": "number",
          "defaultValue": "1"
        }
      ]
    },
    {
      "id": "discovery-protocol-profile-update",
      "label": "Modifier un profil protocole",
      "method": "POST",
      "path": "/v1/discovery/protocol-profile/update",
      "body": [
        {
          "name": "profile_id",
          "label": "Profil",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom profil"
        },
        {
          "name": "scope",
          "label": "Scope"
        },
        {
          "name": "credential_secret_ref",
          "label": "Référence secret vault"
        },
        {
          "name": "port",
          "label": "Port",
          "type": "number"
        },
        {
          "name": "timeout_seconds",
          "label": "Timeout secondes",
          "type": "number"
        },
        {
          "name": "max_concurrency",
          "label": "Concurrence max",
          "type": "number"
        },
        {
          "name": "rate_limit_per_minute",
          "label": "Rate limit/min",
          "type": "number"
        },
        {
          "name": "retry_count",
          "label": "Tentatives",
          "type": "number"
        }
      ]
    },
    {
      "id": "discovery-protocol-profile-delete",
      "label": "Désactiver un profil protocole",
      "method": "POST",
      "path": "/v1/discovery/protocol-profile/delete",
      "body": [
        {
          "name": "profile_id",
          "label": "Profil",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "reason",
          "label": "Motif",
          "required": true,
          "placeholder": "rotation secret"
        }
      ]
    },
    {
      "id": "discovery-integration-profiles",
      "label": "Lister profils virtualisation/cloud",
      "method": "GET",
      "path": "/v1/discovery/integration-profiles",
      "query": [
        {
          "name": "include_inactive",
          "label": "Inclure inactifs",
          "type": "boolean"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "discovery-integration-profile-create",
      "label": "Créer profil VMware/Cloud/Kubernetes",
      "method": "POST",
      "path": "/v1/discovery/integration-profile/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom profil",
          "required": true,
          "placeholder": "vCenter PAR1"
        },
        {
          "name": "kind",
          "label": "Type plateforme",
          "required": true,
          "type": "select",
          "options": [
            "vmware",
            "proxmox",
            "hyperv",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "openstack"
          ]
        },
        {
          "name": "scope",
          "label": "Scope",
          "required": true,
          "placeholder": "site/par1"
        },
        {
          "name": "endpoint_url",
          "label": "Endpoint HTTPS",
          "placeholder": "https://vcenter.example.local"
        },
        {
          "name": "credential_secret_ref",
          "label": "Référence secret vault",
          "required": true,
          "placeholder": "vault://openinfra/discovery/vcenter/par1"
        },
        {
          "name": "verify_tls",
          "label": "Vérifier TLS",
          "type": "boolean",
          "defaultValue": "true"
        },
        {
          "name": "inventory_enabled",
          "label": "Inventaire activé",
          "type": "boolean",
          "defaultValue": "true"
        },
        {
          "name": "max_concurrency",
          "label": "Concurrence max",
          "type": "number",
          "defaultValue": "4"
        },
        {
          "name": "rate_limit_per_minute",
          "label": "Rate limit/min",
          "type": "number",
          "defaultValue": "120"
        }
      ]
    },
    {
      "id": "discovery-integration-profile-update",
      "label": "Modifier profil virtualisation/cloud",
      "method": "POST",
      "path": "/v1/discovery/integration-profile/update",
      "body": [
        {
          "name": "profile_id",
          "label": "Profil",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom profil"
        },
        {
          "name": "scope",
          "label": "Scope"
        },
        {
          "name": "endpoint_url",
          "label": "Endpoint HTTPS"
        },
        {
          "name": "credential_secret_ref",
          "label": "Référence secret vault"
        },
        {
          "name": "verify_tls",
          "label": "Vérifier TLS",
          "type": "boolean"
        },
        {
          "name": "inventory_enabled",
          "label": "Inventaire activé",
          "type": "boolean"
        },
        {
          "name": "max_concurrency",
          "label": "Concurrence max",
          "type": "number"
        },
        {
          "name": "rate_limit_per_minute",
          "label": "Rate limit/min",
          "type": "number"
        }
      ]
    },
    {
      "id": "discovery-integration-profile-delete",
      "label": "Désactiver profil virtualisation/cloud",
      "method": "POST",
      "path": "/v1/discovery/integration-profile/delete",
      "body": [
        {
          "name": "profile_id",
          "label": "Profil",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "reason",
          "label": "Motif",
          "required": true,
          "placeholder": "rotation secret"
        }
      ]
    },
    {
      "id": "local-discovery-plan",
      "label": "Plan discovery locale Lite/Pro",
      "method": "POST",
      "path": "/v1/discovery/local-plan",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom plan",
          "required": true,
          "placeholder": "Discovery locale PAR1"
        },
        {
          "name": "scope",
          "label": "Scope",
          "required": true,
          "placeholder": "site/par1"
        },
        {
          "name": "protocol",
          "label": "Protocole",
          "required": true,
          "type": "select",
          "options": [
            "snmp",
            "ssh",
            "winrm"
          ]
        },
        {
          "name": "targets",
          "label": "Cibles",
          "type": "csv",
          "required": true,
          "placeholder": "10.20.30.20,srv-app-01"
        },
        {
          "name": "credential_secret_ref",
          "label": "Référence secret",
          "required": true,
          "placeholder": "vault://openinfra/discovery/local/par1"
        },
        {
          "name": "protocol_profile_id",
          "label": "Profil protocole"
        },
        {
          "name": "max_concurrency",
          "label": "Concurrence max",
          "type": "number",
          "defaultValue": "4"
        },
        {
          "name": "rate_limit_per_minute",
          "label": "Rate limit/min",
          "type": "number",
          "defaultValue": "120"
        }
      ]
    },
    {
      "id": "agent-bootstrap-plan",
      "label": "Plan bootstrap agent Enterprise",
      "method": "POST",
      "path": "/v1/discovery/agent-bootstrap-plan",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom agent",
          "required": true,
          "placeholder": "Agent Enterprise PAR1"
        },
        {
          "name": "role",
          "label": "Rôle agent",
          "required": true,
          "type": "select",
          "options": [
            "site",
            "regional",
            "datacenter"
          ],
          "defaultValue": "site"
        },
        {
          "name": "scopes",
          "label": "Scopes autorisés",
          "type": "csv",
          "required": true,
          "placeholder": "site/paris,network/core"
        },
        {
          "name": "backend_url",
          "label": "URL backend HTTPS",
          "required": true,
          "placeholder": "https://openinfra-api.example.com"
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte certificat",
          "required": true
        },
        {
          "name": "enrollment_secret_ref",
          "label": "Référence secret enrollment",
          "required": true,
          "placeholder": "vault://openinfra/discovery/agent/par1"
        },
        {
          "name": "agent_version",
          "label": "Version agent",
          "required": true,
          "defaultValue": "0.29.68"
        },
        {
          "name": "service_user",
          "label": "Compte service",
          "defaultValue": "openinfra-agent"
        },
        {
          "name": "config_path",
          "label": "Chemin configuration",
          "defaultValue": "/etc/openinfra/agent.yaml"
        },
        {
          "name": "state_directory",
          "label": "Répertoire état",
          "defaultValue": "/var/lib/openinfra-agent"
        },
        {
          "name": "log_directory",
          "label": "Répertoire logs",
          "defaultValue": "/var/log/openinfra-agent"
        }
      ]
    },
    {
      "id": "collectors-list",
      "label": "Lister les agents proxy Enterprise",
      "method": "GET",
      "path": "/v1/discovery/collectors",
      "query": [
        {
          "name": "scope",
          "label": "Scope autorisé"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "collectors-register",
      "label": "Enregistrer un agent proxy Enterprise",
      "method": "POST",
      "path": "/v1/discovery/collectors",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom agent proxy",
          "required": true
        },
        {
          "name": "kind",
          "label": "Type",
          "required": true,
          "type": "select",
          "options": [
            "site-proxy",
            "network-proxy",
            "datacenter-proxy"
          ]
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte certificat",
          "required": true
        },
        {
          "name": "scopes",
          "label": "Scopes autorisés",
          "type": "csv",
          "required": true,
          "placeholder": "site/paris,network/core"
        },
        {
          "name": "version",
          "label": "Version agent",
          "required": true,
          "defaultValue": "1.0.0"
        },
        {
          "name": "endpoint_url",
          "label": "Endpoint mTLS",
          "required": true,
          "placeholder": "https://collector-paris.openinfra.local"
        }
      ]
    },
    {
      "id": "discovery-job-list",
      "label": "Lister les jobs Discovery",
      "method": "GET",
      "path": "/v1/discovery/jobs",
      "query": [
        {
          "name": "status",
          "label": "État",
          "type": "select",
          "options": [
            "",
            "queued",
            "leased",
            "retry-wait",
            "completed",
            "dead-letter"
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
      "id": "discovery-job",
      "label": "Voir un job Discovery",
      "method": "GET",
      "path": "/v1/discovery/job",
      "query": [
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        }
      ]
    },
    {
      "id": "discovery-job-submit",
      "label": "Soumettre un job idempotent",
      "method": "POST",
      "path": "/v1/discovery/jobs",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "collector_id",
          "label": "ID agent proxy",
          "required": true
        },
        {
          "name": "requested_scope",
          "label": "Scope demandé",
          "required": true,
          "placeholder": "site/par1"
        },
        {
          "name": "job_type",
          "label": "Type de job",
          "required": true,
          "type": "select",
          "options": [
            "snmp",
            "ssh",
            "winrm",
            "vmware",
            "proxmox",
            "hyperv",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "openstack"
          ]
        },
        {
          "name": "target",
          "label": "Cible",
          "required": true,
          "placeholder": "10.20.30.20"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true,
          "placeholder": "scan-par1-core-20260710"
        },
        {
          "name": "max_attempts",
          "label": "Tentatives maximales",
          "type": "number",
          "required": true,
          "defaultValue": "3"
        }
      ]
    },
    {
      "id": "discovery-job-claim",
      "label": "Réserver le prochain job",
      "method": "POST",
      "path": "/v1/discovery/jobs/claim",
      "body": [
        {
          "name": "collector_id",
          "label": "ID agent proxy",
          "required": true
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte certificat",
          "required": true
        },
        {
          "name": "worker_id",
          "label": "ID worker",
          "required": true,
          "placeholder": "worker-par1-01"
        },
        {
          "name": "lease_seconds",
          "label": "Durée du bail (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "60"
        }
      ]
    },
    {
      "id": "discovery-job-renew",
      "label": "Renouveler le bail d’un job",
      "method": "POST",
      "path": "/v1/discovery/jobs/renew",
      "body": [
        {
          "name": "collector_id",
          "label": "ID agent proxy",
          "required": true
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte certificat",
          "required": true
        },
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        },
        {
          "name": "worker_id",
          "label": "ID worker",
          "required": true
        },
        {
          "name": "lease_token",
          "label": "Jeton de fencing",
          "type": "number",
          "required": true
        },
        {
          "name": "lease_seconds",
          "label": "Durée du bail (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "60"
        }
      ]
    },
    {
      "id": "discovery-job-complete",
      "label": "Terminer un job",
      "method": "POST",
      "path": "/v1/discovery/jobs/complete",
      "body": [
        {
          "name": "collector_id",
          "label": "ID agent proxy",
          "required": true
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte certificat",
          "required": true
        },
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        },
        {
          "name": "worker_id",
          "label": "ID worker",
          "required": true
        },
        {
          "name": "lease_token",
          "label": "Jeton de fencing",
          "type": "number",
          "required": true
        },
        {
          "name": "result_hash",
          "label": "Empreinte SHA-256 du résultat",
          "required": true,
          "placeholder": "64 caractères hexadécimaux"
        }
      ]
    },
    {
      "id": "discovery-job-fail",
      "label": "Déclarer l’échec d’un job",
      "method": "POST",
      "path": "/v1/discovery/jobs/fail",
      "body": [
        {
          "name": "collector_id",
          "label": "ID agent proxy",
          "required": true
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte certificat",
          "required": true
        },
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        },
        {
          "name": "worker_id",
          "label": "ID worker",
          "required": true
        },
        {
          "name": "lease_token",
          "label": "Jeton de fencing",
          "type": "number",
          "required": true
        },
        {
          "name": "error",
          "label": "Erreur",
          "required": true
        },
        {
          "name": "retry_delay_seconds",
          "label": "Délai avant reprise (secondes)",
          "type": "number",
          "required": true,
          "defaultValue": "30"
        }
      ]
    },
    {
      "id": "discovery-job-replay",
      "label": "Réexécuter un job en DLQ",
      "method": "POST",
      "path": "/v1/discovery/jobs/replay",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        }
      ]
    },
    {
      "id": "job-authorize",
      "label": "Autoriser un job collector",
      "method": "POST",
      "path": "/v1/discovery/jobs/authorize",
      "body": [
        {
          "name": "collector_id",
          "label": "ID agent proxy",
          "required": true
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte certificat",
          "required": true
        },
        {
          "name": "requested_scope",
          "label": "Scope demandé",
          "required": true
        },
        {
          "name": "job_type",
          "label": "Type de job",
          "required": true,
          "type": "select",
          "options": [
            "snmp",
            "ssh",
            "winrm",
            "vmware",
            "kubernetes"
          ]
        },
        {
          "name": "target",
          "label": "Cible",
          "required": true,
          "placeholder": "10.20.30.20"
        }
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
