const OPENINFRA_MODULES = [
  {
    "id": "overview",
    "label": "Dashboard",
    "icon": "speedometer2",
    "description": "Vue de synthèse, readiness backend, version package, trust web-backend et opérations rapides.",
    "stats": {
      "operations": 2,
      "readOperations": 2,
      "writeOperations": 0,
      "fields": 0,
      "requiredFields": 0
    },
    "operations": [
      {
        "id": "version",
        "label": "Version runtime",
        "method": "GET",
        "path": "/v1/version",
        "query": []
      },
      {
        "id": "schema",
        "label": "Statut schéma DB",
        "method": "GET",
        "path": "/v1/database/schema",
        "query": []
      }
    ],
    "loaded": true
  },
  {
    "id": "rsot",
    "label": "RSOT (Ressource Source of Truth)",
    "shortLabel": "RSOT",
    "icon": "reference",
    "description": "Inventaire canonique, relations, versions, gouvernance et certification.",
    "stats": {
      "operations": 34,
      "readOperations": 22,
      "writeOperations": 12,
      "fields": 162,
      "requiredFields": 52
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "ipam",
    "label": "IPAM",
    "icon": "grid",
    "description": "IPv4/IPv6, VRF, préfixes, plages, VLAN/VXLAN, ASN/BGP, DNS/DHCP, DDI, conflits, capacité et allocations.",
    "stats": {
      "operations": 34,
      "readOperations": 13,
      "writeOperations": 21,
      "fields": 174,
      "requiredFields": 99
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "dcim",
    "label": "DCIM",
    "icon": "home",
    "description": "Sites, salles, zones, racks, ports, câbles, énergie et localisation terrain.",
    "stats": {
      "operations": 95,
      "readOperations": 45,
      "writeOperations": 50,
      "fields": 491,
      "requiredFields": 309
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "itam",
    "label": "IT Asset Management",
    "shortLabel": "ITAM",
    "icon": "asset",
    "description": "Inventaire financier et opérationnel des actifs, garanties constructeur, supports tiers et couverture renouvellement.",
    "stats": {
      "operations": 41,
      "readOperations": 21,
      "writeOperations": 20,
      "fields": 221,
      "requiredFields": 112
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "discovery",
    "label": "Discovery",
    "icon": "activity",
    "description": "Collecte backend locale en Lite/Pro ; agents proxy collectors Enterprise uniquement en topologie étoile.",
    "stats": {
      "operations": 47,
      "readOperations": 26,
      "writeOperations": 21,
      "fields": 163,
      "requiredFields": 107
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "data",
    "label": "Imports / Exports",
    "shortLabel": "Data",
    "icon": "table",
    "description": "Imports massifs reprenables, rollback conflict-aware, exports asynchrones signés et lecture streaming par chunks.",
    "stats": {
      "operations": 4,
      "readOperations": 3,
      "writeOperations": 1,
      "fields": 12,
      "requiredFields": 6
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "integrations",
    "label": "Intégrations externes",
    "shortLabel": "Intégrations",
    "icon": "grid",
    "description": "Connecteurs externes ITSM sans ticketing natif : ServiceNow CMDB, Jira Service Management Assets, GLPI Inventory, Freshservice Assets, enrichissement et liens externes auditables.",
    "stats": {
      "operations": 9,
      "readOperations": 1,
      "writeOperations": 8,
      "fields": 36,
      "requiredFields": 20
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "security",
    "label": "Sécurité / RBAC / Audit",
    "shortLabel": "Sécurité",
    "icon": "shield",
    "description": "Identité, RBAC, tokens, politiques d’accès, audit, éditions et quotas runtime.",
    "stats": {
      "operations": 29,
      "readOperations": 21,
      "writeOperations": 8,
      "fields": 102,
      "requiredFields": 37
    },
    "operations": [],
    "loaded": false
  }
];

const OPENINFRA_SIDEBAR_CONTEXTS = {
  "rsot": [
    {
      "label": "Référentiel",
      "operationIds": [
        "rsot-taxonomy",
        "rsot-list",
        "rsot-upsert"
      ]
    },
    {
      "label": "Relations & historique",
      "operationIds": [
        "rsot-relations",
        "rsot-as-of",
        "rsot-object-audit"
      ]
    },
    {
      "label": "Qualité & gouvernance",
      "operationIds": [
        "rsot-quality-object",
        "rsot-quality-summary",
        "rsot-governance",
        "rsot-reconcile"
      ]
    },
    {
      "label": "Exploration",
      "operationIds": [
        "graph-traverse",
        "graph-path"
      ]
    },
    {
      "label": "Analyse d’impact",
      "operationIds": [
        "graph-impact",
        "graph-spof"
      ]
    },
    {
      "label": "Exports",
      "operationIds": [
        "graph-export"
      ]
    },
    {
      "label": "Simulation & migrations",
      "operationIds": [
        "simulation-create",
        "simulation-list",
        "simulation-run",
        "simulation-reports",
        "simulation-compare",
        "simulation-comparisons"
      ]
    },
    {
      "label": "Assistant gouverné",
      "operationIds": [
        "rag-query",
        "rag-answers",
        "rag-answer-get"
      ]
    },
    {
      "label": "Index de connaissances",
      "operationIds": [
        "rag-document-upsert",
        "rag-documents",
        "rag-document-get",
        "rag-document-deactivate",
        "rag-rsot-sync"
      ]
    },
    {
      "label": "Imports / exports RAG",
      "operationIds": [
        "rag-job-create",
        "rag-jobs",
        "rag-job-get",
        "rag-job-run",
        "rag-job-artifact"
      ]
    }
  ],
  "ipam": [
    {
      "label": "Vue & recherche",
      "operationIds": [
        "ipam-dashboard",
        "ipam-search"
      ]
    },
    {
      "label": "Adressage IP",
      "operationIds": [
        "ipam-define-vrf",
        "ipam-define-aggregate",
        "ipam-define-prefix",
        "ipam-list-prefixes",
        "ipam-define-range",
        "ipam-register-address",
        "ipam-allocate",
        "ipam-reservation-wizard",
        "ipam-capacity"
      ]
    },
    {
      "label": "Réseau L2/L3",
      "operationIds": [
        "ipam-network-bindings",
        "ipam-topology",
        "ipam-define-vlan-group",
        "ipam-define-vxlan-vni",
        "ipam-define-vlan",
        "ipam-define-asn",
        "ipam-define-bgp-peer"
      ]
    },
    {
      "label": "Observations & DDI",
      "operationIds": [
        "ipam-observe-dns",
        "ipam-observe-dhcp",
        "ipam-conflicts",
        "ipam-ddi-preview"
      ]
    },
    {
      "label": "Conformité réseau",
      "operationIds": [
        "network-config-baseline-upsert",
        "network-config-baseline-list",
        "network-config-baseline-retire",
        "network-config-observation-submit",
        "network-config-observation-list",
        "network-config-assessment"
      ]
    },
    {
      "label": "Flux déclarés",
      "operationIds": [
        "flow-declaration-upsert",
        "flow-declaration-list",
        "flow-declaration-retire"
      ]
    },
    {
      "label": "Flux observés",
      "operationIds": [
        "flow-observation-submit",
        "flow-observation-list"
      ]
    },
    {
      "label": "Conformité des flux",
      "operationIds": [
        "flow-matrix"
      ]
    }
  ],
  "dcim": [
    {
      "label": "Sites & dépendances",
      "operationIds": [
        "dcim-sites",
        "dcim-site",
        "dcim-site-create",
        "dcim-site-update",
        "dcim-site-delete",
        "dcim-buildings",
        "dcim-building",
        "dcim-building-create",
        "dcim-building-update",
        "dcim-building-delete",
        "dcim-floors",
        "dcim-floor",
        "dcim-rooms-list",
        "dcim-room",
        "dcim-room-create",
        "dcim-room-update",
        "dcim-room-delete",
        "dcim-racks",
        "dcim-rack",
        "dcim-rack-create",
        "dcim-rack-update",
        "dcim-rack-delete",
        "dcim-zones",
        "dcim-zone",
        "dcim-zone-create",
        "dcim-zone-update",
        "dcim-zone-delete",
        "dcim-topology-catalog",
        "dcim-define-room"
      ]
    },
    {
      "label": "Pilotage multisite",
      "operationIds": [
        "multisite-sites",
        "multisite-grants",
        "multisite-grant-upsert",
        "multisite-grant-revoke",
        "multisite-report-generate",
        "multisite-reports",
        "multisite-report-get",
        "multisite-dr-plan-configure",
        "multisite-dr-plan-disable",
        "multisite-dr-plans",
        "multisite-dr-plan-get",
        "multisite-dr-drill-execute",
        "multisite-dr-drills",
        "multisite-dr-drill-get",
        "multisite-routes",
        "multisite-route-get",
        "multisite-route-configure",
        "multisite-route-disable",
        "multisite-job-route"
      ]
    },
    {
      "label": "Localisation & capacité",
      "operationIds": [
        "dcim-locate-equipment",
        "dcim-rack-capacity",
        "dcim-room-plan",
        "dcim-rack-elevation"
      ]
    },
    {
      "label": "Connectivité",
      "operationIds": [
        "dcim-patch-panel",
        "dcim-port",
        "dcim-cable",
        "dcim-cable-trace"
      ]
    },
    {
      "label": "Énergie & refroidissement",
      "operationIds": [
        "dcim-power-device",
        "dcim-power-circuit",
        "dcim-cooling-zone",
        "dcim-power-reservation",
        "dcim-energy-cooling-capacity"
      ]
    },
    {
      "label": "GreenOps — sources & politiques",
      "operationIds": [
        "greenops-source-create",
        "greenops-sources",
        "greenops-policy-upsert",
        "greenops-policy-get",
        "greenops-factor-create",
        "greenops-factors"
      ]
    },
    {
      "label": "GreenOps — mesures",
      "operationIds": [
        "greenops-measurement-ingest",
        "greenops-measurements"
      ]
    },
    {
      "label": "GreenOps — rapports & empreinte",
      "operationIds": [
        "greenops-report-generate",
        "greenops-report-get",
        "greenops-reports",
        "greenops-report-export",
        "greenops-scores"
      ]
    },
    {
      "label": "GreenOps — capacité & recommandations",
      "operationIds": [
        "greenops-anomalies",
        "greenops-forecasts",
        "greenops-candidates"
      ]
    },
    {
      "label": "Opérations terrain",
      "operationIds": [
        "field-sheet-list",
        "field-sheet-get",
        "field-sheet-generate",
        "field-lock-acquire",
        "field-operation-start",
        "field-checklist-record",
        "field-evidence-attach",
        "field-evidence-list",
        "field-evidence-validate",
        "field-operation-complete",
        "field-operation-cancel",
        "field-qr-verify",
        "field-lock-release",
        "field-offline-create",
        "field-offline-list",
        "field-offline-get",
        "field-offline-sync"
      ]
    },
    {
      "label": "Jumeau numérique",
      "operationIds": [
        "dcim-digital-twin"
      ]
    }
  ],
  "itam": [
    {
      "label": "Organisations",
      "operationIds": [
        "itam-organizations",
        "itam-organization",
        "itam-organization-create",
        "itam-organization-update",
        "itam-organization-delete",
        "itam-tenants",
        "itam-tenant",
        "itam-tenant-create",
        "itam-tenant-update",
        "itam-tenant-delete"
      ]
    },
    {
      "label": "Partenaires",
      "operationIds": [
        "itam-partners",
        "itam-partner",
        "itam-partner-create",
        "itam-partner-update",
        "itam-partner-delete"
      ]
    },
    {
      "label": "Support matériel",
      "operationIds": [
        "itam-support-profile",
        "itam-support-coverage",
        "itam-register-manufacturer",
        "itam-add-third-party"
      ]
    },
    {
      "label": "Licences logicielles",
      "operationIds": [
        "itam-software-license",
        "itam-software-compliance",
        "itam-register-software",
        "itam-update-license-assignment"
      ]
    },
    {
      "label": "Règles d’allocation",
      "operationIds": [
        "finops-rule-create",
        "finops-rules"
      ]
    },
    {
      "label": "Imports & coûts",
      "operationIds": [
        "finops-import-submit",
        "finops-import-get",
        "finops-imports",
        "finops-import-run",
        "finops-import-cancel",
        "finops-costs"
      ]
    },
    {
      "label": "Budgets & périodes",
      "operationIds": [
        "finops-budget-upsert",
        "finops-budgets",
        "finops-period-close",
        "finops-periods"
      ]
    },
    {
      "label": "Showback / chargeback",
      "operationIds": [
        "finops-report-generate",
        "finops-report-get",
        "finops-reports",
        "finops-report-export"
      ]
    },
    {
      "label": "Prévisions & anomalies",
      "operationIds": [
        "finops-anomalies",
        "finops-forecasts"
      ]
    }
  ],
  "discovery": [
{"label":"Kubernetes et cloud-native","operationIdPrefix":"kubernetes-"},
    {
      "label": "Locale Lite/Pro",
      "operationIds": [
        "local-discovery-plan"
      ]
    },
    {
      "label": "Agents Enterprise",
      "operationIds": [
        "agent-bootstrap-plan",
        "collectors-list",
        "collectors-register",
        "job-authorize"
      ]
    }
  ],
  "data": [
    {
      "label": "Imports",
      "operationIds": [
        "import-bulk-progress",
        "import-bulk-rollback"
      ]
    },
    {
      "label": "Migration",
      "operationIds": [
        "import-migration-guide"
      ]
    },
    {
      "label": "Exports",
      "operationIds": [
        "export-artifact-chunk"
      ]
    }
  ],
  "integrations": [
    {
      "label": "Gouvernance ITSM",
      "operationIds": [
        "itsm-providers"
      ]
    },
    {
      "label": "ServiceNow",
      "operationIds": [
        "servicenow-validate",
        "servicenow-ci-sync-plan"
      ]
    },
    {
      "label": "Jira Assets",
      "operationIds": [
        "jira-validate",
        "jira-asset-sync-plan"
      ]
    },
    {
      "label": "GLPI Inventory",
      "operationIds": [
        "glpi-validate",
        "glpi-asset-sync-plan"
      ]
    },
    {
      "label": "Freshservice Assets",
      "operationIds": [
        "freshservice-validate",
        "freshservice-asset-sync-plan"
      ]
    }
  ],
  "security": [
    {
      "label": "Éditions & quotas",
      "operationIds": [
        "edition-policies",
        "edition-feature-check",
        "edition-quota-check"
      ]
    },
    {
      "label": "Identité & accès",
      "operationIds": [
        "tokens-list",
        "effective-identity",
        "access-rules"
      ]
    },
    {
      "label": "Audit",
      "operationIds": [
        "audit-events",
        "audit-integrity"
      ]
    },
    {
      "label": "Inventaire PKI",
      "operationIds": [
        "certificate-import",
        "certificate-get",
        "certificate-list",
        "certificate-retire"
      ]
    },
    {
      "label": "Endpoints TLS",
      "operationIds": [
        "certificate-endpoint-observe",
        "certificate-endpoint-list"
      ]
    },
    {
      "label": "Conformité PKI",
      "operationIds": [
        "certificate-assessment"
      ]
    },
    {
      "label": "SBOM — inventaire & versions",
      "operationIds": [
        "sbom-import",
        "sbom-documents",
        "sbom-document-get",
        "sbom-compare",
        "sbom-comparisons",
        "sbom-comparison-get"
      ]
    },
    {
      "label": "Vulnérabilités & exposition",
      "operationIds": [
        "sbom-vulnerability-import",
        "sbom-vulnerabilities",
        "sbom-exposure-upsert",
        "sbom-exposures",
        "sbom-exposure-get"
      ]
    },
    {
      "label": "Risque contextualisé",
      "operationIds": [
        "sbom-risk-assess",
        "sbom-findings",
        "sbom-risk-export"
      ]
    }
  ]
};

const OPENINFRA_DOMAIN_LOADERS={
"rsot":()=>import("./domains/rsot.js?v=0.34.5"),
"ipam":()=>import("./domains/ipam.js?v=0.34.5"),
"dcim":()=>import("./domains/dcim.js?v=0.34.5"),
"itam":()=>import("./domains/itam.js?v=0.34.5"),
"discovery":()=>import("./domains/discovery.js?v=0.34.5"),
"data":()=>import("./domains/data.js?v=0.34.5"),
"integrations":()=>import("./domains/integrations.js?v=0.34.5"),
"security":()=>import("./domains/security.js?v=0.34.5")
};

export { OPENINFRA_DOMAIN_LOADERS, OPENINFRA_MODULES, OPENINFRA_SIDEBAR_CONTEXTS };
