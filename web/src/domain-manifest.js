export const MODULES = [
  {
    "id": "overview",
    "label": "Dashboard",
    "icon": "speedometer2",
    "stats": {
      "operations": 1,
      "readOperations": 1,
      "writeOperations": 0,
      "fields": 0,
      "requiredFields": 0
    },
    "operations": [
      {
        "id": "version",
        "label": "Version runtime",
        "path": "/v1/version",
        "method": "GET",
        "fields": []
      }
    ],
    "loaded": true
  },
  {
    "id": "rsot",
    "label": "RSOT (Ressource Source of Truth)",
    "shortLabel": "RSOT",
    "icon": "reference",
    "stats": {
      "operations": 30,
      "readOperations": 19,
      "writeOperations": 11,
      "fields": 146,
      "requiredFields": 28
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "ipam",
    "label": "IPAM",
    "icon": "grid",
    "stats": {
      "operations": 34,
      "readOperations": 13,
      "writeOperations": 21,
      "fields": 174,
      "requiredFields": 0
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "dcim",
    "label": "DCIM",
    "icon": "home",
    "stats": {
      "operations": 88,
      "readOperations": 42,
      "writeOperations": 46,
      "fields": 425,
      "requiredFields": 120
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "itam",
    "label": "IT Asset Management",
    "shortLabel": "ITAM",
    "icon": "asset",
    "stats": {
      "operations": 40,
      "readOperations": 20,
      "writeOperations": 20,
      "fields": 207,
      "requiredFields": 28
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "discovery",
    "label": "Discovery",
    "icon": "activity",
    "stats": {
      "operations": 29,
      "readOperations": 21,
      "writeOperations": 8,
      "fields": 69,
      "requiredFields": 10
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "data",
    "label": "Imports / Exports",
    "shortLabel": "Data",
    "icon": "table",
    "stats": {
      "operations": 4,
      "readOperations": 3,
      "writeOperations": 1,
      "fields": 12,
      "requiredFields": 0
    },
    "operations": [],
    "loaded": false
  },
  {
    "id": "integrations",
    "label": "Intégrations externes",
    "shortLabel": "Intégrations",
    "icon": "grid",
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
    "stats": {
      "operations": 25,
      "readOperations": 17,
      "writeOperations": 8,
      "fields": 96,
      "requiredFields": 21
    },
    "operations": [],
    "loaded": false
  }
];

export const SIDEBAR_CONTEXTS = {
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
        "dcim-zones",
        "dcim-zone",
        "dcim-zone-create",
        "dcim-zone-update",
        "dcim-zone-delete",
        "dcim-topology-catalog"
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
        "dcim-placement-recommendations",
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
        "itam-organization-delete"
      ]
    },
    {
      "label": "Tenants",
      "operationIds": [
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
    {
      "label": "Kubernetes et cloud-native",
      "operationIdPrefix": "kubernetes-"
    },
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

const DOMAIN_LOADERS = {
  'rsot': () => import('./domains/rsot.js'),
  'ipam': () => import('./domains/ipam.js'),
  'dcim': () => import('./domains/dcim.js'),
  'itam': () => import('./domains/itam.js'),
  'discovery': () => import('./domains/discovery.js'),
  'data': () => import('./domains/data.js'),
  'integrations': () => import('./domains/integrations.js'),
  'security': () => import('./domains/security.js'),
};

const inflight = new Map();
export async function loadDomain(moduleId) {
  const existing = MODULES.find((module) => module.id === moduleId);
  if (!existing) throw new Error(`Unknown OpenInfra domain: ${moduleId}`);
  if (existing.loaded) return existing;
  if (!DOMAIN_LOADERS[moduleId]) return existing;
  if (!inflight.has(moduleId)) {
    inflight.set(moduleId, DOMAIN_LOADERS[moduleId]().then((loaded) => {
      const index = MODULES.findIndex((module) => module.id === moduleId);
      const definition = { ...loaded.default, stats: MODULES[index].stats, loaded: true };
      MODULES.splice(index, 1, definition);
      return definition;
    }).finally(() => inflight.delete(moduleId)));
  }
  return inflight.get(moduleId);
}
