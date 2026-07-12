const moduleDefinition = {
  "id": "security",
  "label": "Sécurité / RBAC / Audit",
  "shortLabel": "Sécurité",
  "icon": "shield",
  "operations": [
    {
      "id": "edition-policies",
      "label": "Politiques éditions et quotas",
      "path": "/v1/editions/policies",
      "method": "GET",
      "fields": []
    },
    {
      "id": "edition-feature-check",
      "label": "Vérifier une capacité édition",
      "path": "/v1/editions/feature-check",
      "method": "GET",
      "fields": [
        "Édition",
        "Capacité"
      ]
    },
    {
      "id": "edition-quota-check",
      "label": "Vérifier un quota édition",
      "path": "/v1/editions/quota-check",
      "method": "GET",
      "fields": [
        "Édition",
        "Ressource quota",
        "Incrément demandé"
      ]
    },
    {
      "id": "audit-events",
      "label": "Événements d’audit",
      "path": "/v1/audit/events",
      "method": "GET",
      "fields": [
        "Action",
        "Type cible",
        "Limite"
      ]
    },
    {
      "id": "certificate-import",
      "label": "Importer une chaîne PEM",
      "path": "/v1/certificates/import",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Chaîne de certificats PEM",
        "Propriétaire",
        "Environnement",
        "Source certificat",
        "Objet RSOT associé"
      ]
    },
    {
      "id": "certificate-get",
      "label": "Consulter un certificat",
      "path": "/v1/certificates/get",
      "method": "GET",
      "fields": [
        "Empreinte SHA-256"
      ]
    },
    {
      "id": "certificate-list",
      "label": "Lister les certificats",
      "path": "/v1/certificates",
      "method": "GET",
      "fields": [
        "Limite",
        "Curseur",
        "Inclure retirés"
      ]
    },
    {
      "id": "certificate-retire",
      "label": "Retirer un certificat",
      "path": "/v1/certificates/retire",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Empreinte SHA-256"
      ]
    },
    {
      "id": "certificate-endpoint-observe",
      "label": "Observer un endpoint TLS",
      "path": "/v1/certificates/endpoints/observe",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé d’idempotence",
        "Protocole endpoint",
        "Hôte endpoint",
        "Port",
        "Service",
        "Empreinte certificat",
        "Observé le (ISO-8601)",
        "Source observation",
        "Collecteur",
        "Objet RSOT associé",
        "Version TLS",
        "Suite cryptographique"
      ]
    },
    {
      "id": "certificate-endpoint-list",
      "label": "Lister les endpoints TLS",
      "path": "/v1/certificates/endpoints",
      "method": "GET",
      "fields": [
        "Empreinte certificat",
        "Limite",
        "Curseur"
      ]
    },
    {
      "id": "certificate-assessment",
      "label": "Évaluer l’état PKI",
      "path": "/v1/certificates/assessment",
      "method": "GET",
      "fields": [
        "Date de référence",
        "Seuil critique (jours)",
        "Seuil avertissement (jours)",
        "État certificat",
        "Limite",
        "Curseur"
      ]
    },
    {
      "id": "sbom-import",
      "label": "Importer une SBOM",
      "path": "/v1/sbom/documents/import",
      "method": "POST",
      "fields": [
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
      "path": "/v1/sbom/documents",
      "method": "GET",
      "fields": [
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
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "sbom-document-get",
      "label": "Consulter une SBOM",
      "path": "/v1/sbom/documents/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/sbom/vulnerabilities/import",
      "method": "POST",
      "fields": [
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
      "path": "/v1/sbom/vulnerabilities",
      "method": "GET",
      "fields": [
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
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "sbom-exposure-upsert",
      "label": "Définir le contexte d’exposition",
      "path": "/v1/sbom/exposures/upsert",
      "method": "POST",
      "fields": [
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
      "path": "/v1/sbom/exposures",
      "method": "GET",
      "fields": [
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
      "id": "sbom-exposure-get",
      "label": "Consulter un contexte d’exposition",
      "path": "/v1/sbom/exposures/get",
      "method": "GET",
      "fields": [
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
      "path": "/v1/sbom/risk/assess",
      "method": "POST",
      "fields": [
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
      "path": "/v1/sbom/findings",
      "method": "GET",
      "fields": [
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
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "sbom-risk-export",
      "label": "Exporter le risque SBOM",
      "path": "/v1/sbom/risk/export",
      "method": "GET",
      "download": true,
      "fields": [
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
      "path": "/v1/sbom/comparisons/create",
      "method": "POST",
      "fields": [
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
      "path": "/v1/sbom/comparisons",
      "method": "GET",
      "fields": [
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
      "id": "sbom-comparison-get",
      "label": "Consulter une comparaison SBOM",
      "path": "/v1/sbom/comparisons/get",
      "method": "GET",
      "fields": [
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
