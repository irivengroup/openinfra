const moduleDefinition = {
  "id": "security",
  "label": "Sécurité / RBAC / Audit",
  "shortLabel": "Sécurité",
  "icon": "shield",
  "description": "Identité, RBAC, tokens, politiques d’accès, audit, éditions et quotas runtime.",
  "operations": [
    {
      "id": "edition-policies",
      "label": "Politiques éditions et quotas",
      "method": "GET",
      "path": "/v1/editions/policies",
      "query": []
    },
    {
      "id": "edition-feature-check",
      "label": "Vérifier une capacité édition",
      "method": "GET",
      "path": "/v1/editions/feature-check",
      "query": [
        {
          "name": "edition",
          "label": "Édition",
          "type": "select",
          "options": [
            "lite",
            "pro",
            "enterprise"
          ],
          "defaultValue": "enterprise"
        },
        {
          "name": "capability",
          "label": "Capacité",
          "type": "select",
          "options": [
            "core_rsot",
            "dcim",
            "ipam",
            "rbac",
            "audit",
            "import_export",
            "distributed_discovery_agents",
            "installer_agent_scope"
          ],
          "defaultValue": "ipam"
        }
      ]
    },
    {
      "id": "edition-quota-check",
      "label": "Vérifier un quota édition",
      "method": "GET",
      "path": "/v1/editions/quota-check",
      "query": [
        {
          "name": "edition",
          "label": "Édition",
          "type": "select",
          "options": [
            "lite",
            "pro",
            "enterprise"
          ],
          "defaultValue": "enterprise"
        },
        {
          "name": "resource",
          "label": "Ressource quota",
          "type": "select",
          "options": [
            "equipment",
            "subnet_vlan",
            "ip_dns_record",
            "user",
            "discovery_collector"
          ],
          "defaultValue": "equipment"
        },
        {
          "name": "requested_increment",
          "label": "Incrément demandé",
          "type": "number",
          "defaultValue": "1",
          "placeholder": "1"
        }
      ]
    },
    {
      "id": "tokens-list",
      "label": "Lister les tokens techniques",
      "method": "GET",
      "path": "/v1/security/tokens",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "include_inactive",
          "label": "Inclure inactifs",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "effective-identity",
      "label": "Identité effective",
      "method": "GET",
      "path": "/v1/identity/effective",
      "query": [
        {
          "name": "subject",
          "label": "Sujet",
          "placeholder": "user@example.com"
        }
      ]
    },
    {
      "id": "access-rules",
      "label": "Politiques d’accès",
      "method": "GET",
      "path": "/v1/access/rules",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "include_inactive",
          "label": "Inclure inactives",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "audit-events",
      "label": "Événements d’audit",
      "method": "GET",
      "path": "/v1/audit/events",
      "query": [
        {
          "name": "action",
          "label": "Action"
        },
        {
          "name": "target_type",
          "label": "Type cible"
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
      "id": "audit-integrity",
      "label": "Intégrité audit",
      "method": "GET",
      "path": "/v1/audit/integrity",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "certificate-import",
      "label": "Importer une chaîne PEM",
      "method": "POST",
      "path": "/v1/certificates/import",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "pem_bundle",
          "label": "Chaîne PEM",
          "type": "textarea",
          "required": true,
          "placeholder": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
        },
        {
          "name": "owner",
          "label": "Propriétaire",
          "required": true,
          "placeholder": "Équipe PKI"
        },
        {
          "name": "environment",
          "label": "Environnement",
          "required": true,
          "placeholder": "production"
        },
        {
          "name": "source",
          "label": "Source",
          "type": "select",
          "options": [
            "manual",
            "discovery",
            "import",
            "acme",
            "internal-pki",
            "external-pki"
          ],
          "defaultValue": "manual"
        },
        {
          "name": "object_key",
          "label": "Objet RSOT",
          "placeholder": "application/portail"
        }
      ]
    },
    {
      "id": "certificate-get",
      "label": "Consulter un certificat",
      "method": "GET",
      "path": "/v1/certificates/get",
      "query": [
        {
          "name": "fingerprint",
          "label": "Empreinte SHA-256",
          "required": true,
          "placeholder": "64 caractères hexadécimaux"
        }
      ]
    },
    {
      "id": "certificate-list",
      "label": "Lister les certificats",
      "method": "GET",
      "path": "/v1/certificates",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "certificate-retire",
      "label": "Retirer un certificat",
      "method": "POST",
      "path": "/v1/certificates/retire",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "fingerprint",
          "label": "Empreinte SHA-256",
          "required": true
        }
      ]
    },
    {
      "id": "certificate-endpoint-observe",
      "label": "Observer un endpoint TLS",
      "method": "POST",
      "path": "/v1/certificates/endpoints/observe",
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
          "required": true,
          "placeholder": "scanner-01:20260710:443"
        },
        {
          "name": "protocol",
          "label": "Protocole",
          "type": "select",
          "options": [
            "https",
            "tls",
            "ldaps",
            "smtps",
            "imaps",
            "pop3s",
            "mqtts",
            "custom"
          ],
          "defaultValue": "https"
        },
        {
          "name": "host",
          "label": "Hôte",
          "required": true,
          "placeholder": "portal.example.net"
        },
        {
          "name": "port",
          "label": "Port",
          "type": "number",
          "required": true,
          "defaultValue": "443"
        },
        {
          "name": "service",
          "label": "Service",
          "required": true,
          "placeholder": "Portail OpenInfra"
        },
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte du certificat",
          "required": true
        },
        {
          "name": "observed_at",
          "label": "Observé le",
          "required": true,
          "placeholder": "2026-07-10T12:00:00Z"
        },
        {
          "name": "source",
          "label": "Source observation",
          "required": true,
          "placeholder": "tls-scanner"
        },
        {
          "name": "collector",
          "label": "Collecteur",
          "required": true,
          "placeholder": "scanner-par-01"
        },
        {
          "name": "object_key",
          "label": "Objet RSOT",
          "placeholder": "application/portail"
        },
        {
          "name": "tls_version",
          "label": "Version TLS",
          "placeholder": "TLSv1.3"
        },
        {
          "name": "cipher",
          "label": "Suite cryptographique",
          "placeholder": "TLS_AES_256_GCM_SHA384"
        }
      ]
    },
    {
      "id": "certificate-endpoint-list",
      "label": "Lister les endpoints TLS",
      "method": "GET",
      "path": "/v1/certificates/endpoints",
      "query": [
        {
          "name": "certificate_fingerprint",
          "label": "Empreinte du certificat"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "certificate-assessment",
      "label": "Évaluer la conformité PKI",
      "method": "GET",
      "path": "/v1/certificates/assessment",
      "query": [
        {
          "name": "as_of",
          "label": "Date de référence",
          "placeholder": "2026-07-10T12:00:00Z"
        },
        {
          "name": "critical_days",
          "label": "Seuil critique (jours)",
          "type": "number",
          "defaultValue": "14"
        },
        {
          "name": "warning_days",
          "label": "Seuil avertissement (jours)",
          "type": "number",
          "defaultValue": "30"
        },
        {
          "name": "health",
          "label": "État de santé",
          "type": "select",
          "options": [
            "",
            "retired",
            "not-yet-valid",
            "expired",
            "critical",
            "warning",
            "healthy"
          ]
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "sbom-import",
      "label": "Importer une SBOM",
      "method": "POST",
      "path": "/v1/sbom/documents/import",
      "body": [
        {
          "name": "application",
          "label": "Application",
          "required": true
        },
        {
          "name": "release",
          "label": "Version / release",
          "required": true
        },
        {
          "name": "environment",
          "label": "Environnement",
          "required": true
        },
        {
          "name": "source_name",
          "label": "Source",
          "required": true,
          "defaultValue": "ci-cd"
        },
        {
          "name": "source_uri",
          "label": "URI de provenance",
          "type": "url"
        },
        {
          "name": "sbom",
          "label": "Document CycloneDX ou SPDX (JSON)",
          "type": "json",
          "required": true
        }
      ]
    },
    {
      "id": "sbom-documents",
      "label": "Lister les SBOM",
      "method": "GET",
      "path": "/v1/sbom/documents",
      "query": [
        {
          "name": "application",
          "label": "Application"
        },
        {
          "name": "environment",
          "label": "Environnement"
        },
        {
          "name": "format",
          "label": "Format",
          "type": "select",
          "options": [
            "",
            "cyclonedx",
            "spdx"
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
      "id": "sbom-document-get",
      "label": "Consulter une SBOM",
      "method": "GET",
      "path": "/v1/sbom/documents/get",
      "query": [
        {
          "name": "document_id",
          "label": "ID SBOM",
          "required": true
        }
      ]
    },
    {
      "id": "sbom-vulnerability-import",
      "label": "Importer une vulnérabilité",
      "method": "POST",
      "path": "/v1/sbom/vulnerabilities/import",
      "body": [
        {
          "name": "cve_id",
          "label": "Identifiant CVE",
          "required": true,
          "placeholder": "CVE-2026-12345"
        },
        {
          "name": "component_name",
          "label": "Composant",
          "required": true
        },
        {
          "name": "component_version",
          "label": "Version",
          "required": true
        },
        {
          "name": "component_purl",
          "label": "Package URL (PURL)",
          "placeholder": "pkg:pypi/example@1.0.0"
        },
        {
          "name": "cvss_score",
          "label": "Score CVSS",
          "type": "number",
          "required": true,
          "min": "0",
          "max": "10",
          "step": "0.1"
        },
        {
          "name": "known_exploited",
          "label": "Exploitation connue",
          "type": "boolean"
        },
        {
          "name": "exploit_maturity",
          "label": "Maturité de l’exploit",
          "type": "select",
          "options": [
            "unknown",
            "proof-of-concept",
            "functional",
            "weaponized"
          ],
          "defaultValue": "unknown"
        },
        {
          "name": "source_name",
          "label": "Source",
          "required": true,
          "defaultValue": "external-scanner"
        },
        {
          "name": "published_at",
          "label": "Publication",
          "type": "datetime-local"
        },
        {
          "name": "modified_at",
          "label": "Modification",
          "type": "datetime-local"
        },
        {
          "name": "references",
          "label": "Références (JSON)",
          "type": "json",
          "defaultValue": "[]"
        },
        {
          "name": "metadata",
          "label": "Métadonnées (JSON)",
          "type": "json",
          "defaultValue": "{}"
        }
      ]
    },
    {
      "id": "sbom-vulnerabilities",
      "label": "Lister les vulnérabilités",
      "method": "GET",
      "path": "/v1/sbom/vulnerabilities",
      "query": [
        {
          "name": "cve_id",
          "label": "Identifiant CVE"
        },
        {
          "name": "component",
          "label": "Composant ou PURL"
        },
        {
          "name": "known_exploited",
          "label": "Exploitation connue",
          "type": "boolean"
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
      "id": "sbom-exposure-upsert",
      "label": "Définir le contexte d’exposition",
      "method": "POST",
      "path": "/v1/sbom/exposures/upsert",
      "body": [
        {
          "name": "application",
          "label": "Application",
          "required": true
        },
        {
          "name": "environment",
          "label": "Environnement",
          "required": true
        },
        {
          "name": "internet_exposed",
          "label": "Exposé à Internet",
          "type": "boolean"
        },
        {
          "name": "flow_exposed",
          "label": "Accessible par les flux",
          "type": "boolean"
        },
        {
          "name": "business_criticality",
          "label": "Criticité métier (1-5)",
          "type": "number",
          "required": true,
          "min": "1",
          "max": "5",
          "defaultValue": "3"
        },
        {
          "name": "compensating_controls",
          "label": "Contrôles compensatoires (JSON)",
          "type": "json",
          "defaultValue": "[]"
        },
        {
          "name": "asset_ids",
          "label": "Actifs associés (JSON)",
          "type": "json",
          "defaultValue": "[]"
        },
        {
          "name": "service_ids",
          "label": "Services associés (JSON)",
          "type": "json",
          "defaultValue": "[]"
        }
      ]
    },
    {
      "id": "sbom-exposures",
      "label": "Lister les contextes d’exposition",
      "method": "GET",
      "path": "/v1/sbom/exposures",
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
      "id": "sbom-exposure-get",
      "label": "Consulter un contexte d’exposition",
      "method": "GET",
      "path": "/v1/sbom/exposures/get",
      "query": [
        {
          "name": "application",
          "label": "Application",
          "required": true
        },
        {
          "name": "environment",
          "label": "Environnement",
          "required": true
        }
      ]
    },
    {
      "id": "sbom-risk-assess",
      "label": "Évaluer le risque contextualisé",
      "method": "POST",
      "path": "/v1/sbom/risk/assess",
      "body": [
        {
          "name": "document_id",
          "label": "ID SBOM",
          "required": true
        }
      ]
    },
    {
      "id": "sbom-findings",
      "label": "Lister les constats de risque",
      "method": "GET",
      "path": "/v1/sbom/findings",
      "query": [
        {
          "name": "document_id",
          "label": "ID SBOM"
        },
        {
          "name": "priority",
          "label": "Priorité",
          "type": "select",
          "options": [
            "",
            "critical",
            "high",
            "medium",
            "low"
          ]
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "open",
            "accepted",
            "mitigated",
            "false-positive"
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
      "id": "sbom-risk-export",
      "label": "Exporter le risque SBOM",
      "method": "GET",
      "path": "/v1/sbom/risk/export",
      "download": true,
      "query": [
        {
          "name": "document_id",
          "label": "ID SBOM",
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
      "id": "sbom-compare",
      "label": "Comparer deux releases SBOM",
      "method": "POST",
      "path": "/v1/sbom/comparisons/create",
      "body": [
        {
          "name": "base_document_id",
          "label": "SBOM de référence",
          "required": true
        },
        {
          "name": "target_document_id",
          "label": "SBOM cible",
          "required": true
        }
      ]
    },
    {
      "id": "sbom-comparisons",
      "label": "Lister les comparaisons SBOM",
      "method": "GET",
      "path": "/v1/sbom/comparisons",
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
      "id": "sbom-comparison-get",
      "label": "Consulter une comparaison SBOM",
      "method": "GET",
      "path": "/v1/sbom/comparisons/get",
      "query": [
        {
          "name": "comparison_id",
          "label": "ID comparaison",
          "required": true
        }
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
