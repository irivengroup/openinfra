const OPENINFRA_SEARCH_INDEX = [
  {
    "moduleId": "overview",
    "moduleLabel": "Dashboard",
    "id": "version",
    "label": "Version runtime",
    "method": "GET",
    "path": "/v1/version"
  },
  {
    "moduleId": "overview",
    "moduleLabel": "Dashboard",
    "id": "schema",
    "label": "Statut schéma DB",
    "method": "GET",
    "path": "/v1/database/schema"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-taxonomy",
    "label": "Catalogue catégories / types",
    "method": "GET",
    "path": "/v1/rsot/resource-taxonomy"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-list",
    "label": "Lister les objets RSOT",
    "method": "GET",
    "path": "/v1/rsot/objects"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-upsert",
    "label": "Créer / mettre à jour une ressource",
    "method": "POST",
    "path": "/v1/rsot/objects"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-relations",
    "label": "Lister les relations",
    "method": "GET",
    "path": "/v1/rsot/relations"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-as-of",
    "label": "Restituer une ressource à date",
    "method": "GET",
    "path": "/v1/rsot/object-as-of"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-object-audit",
    "label": "Audit d’une ressource",
    "method": "GET",
    "path": "/v1/rsot/object-audit"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-quality-object",
    "label": "Évaluer la qualité d’une ressource",
    "method": "GET",
    "path": "/v1/rsot/quality/object"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-quality-summary",
    "label": "Synthèse qualité / certification",
    "method": "GET",
    "path": "/v1/rsot/quality/summary"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-governance",
    "label": "Évaluer une règle de gouvernance",
    "method": "POST",
    "path": "/v1/rsot/governance/evaluate"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rsot-reconcile",
    "label": "Réconcilier une ressource",
    "method": "POST",
    "path": "/v1/rsot/reconcile-object"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "graph-traverse",
    "label": "Explorer le graphe de dépendances",
    "method": "GET",
    "path": "/v1/graph/traverse"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "graph-impact",
    "label": "Analyser les impacts",
    "method": "GET",
    "path": "/v1/graph/impact"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "graph-path",
    "label": "Trouver le chemin le plus court",
    "method": "GET",
    "path": "/v1/graph/path"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "graph-spof",
    "label": "Détecter les points uniques de défaillance",
    "method": "GET",
    "path": "/v1/graph/spof"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "graph-export",
    "label": "Exporter le graphe de dépendances",
    "method": "GET",
    "path": "/v1/graph/export"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "simulation-create",
    "label": "Créer un scénario de changement",
    "method": "POST",
    "path": "/v1/simulation-scenarios/create"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "simulation-list",
    "label": "Lister les scénarios",
    "method": "GET",
    "path": "/v1/simulation-scenarios"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "simulation-run",
    "label": "Calculer l’impact d’un scénario",
    "method": "POST",
    "path": "/v1/simulation-scenarios/run"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "simulation-reports",
    "label": "Lister les rapports d’impact",
    "method": "GET",
    "path": "/v1/impact-reports"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "simulation-compare",
    "label": "Comparer deux rapports",
    "method": "POST",
    "path": "/v1/scenario-comparisons/create"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "simulation-comparisons",
    "label": "Lister les comparaisons",
    "method": "GET",
    "path": "/v1/scenario-comparisons"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-document-upsert",
    "label": "Indexer un document gouverné",
    "method": "POST",
    "path": "/v1/rag/documents/upsert"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-documents",
    "label": "Lister les documents gouvernés",
    "method": "GET",
    "path": "/v1/rag/documents"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-document-get",
    "label": "Consulter un document gouverné",
    "method": "GET",
    "path": "/v1/rag/documents/get"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-document-deactivate",
    "label": "Désactiver un document gouverné",
    "method": "POST",
    "path": "/v1/rag/documents/deactivate"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-rsot-sync",
    "label": "Synchroniser l’index depuis RSOT",
    "method": "POST",
    "path": "/v1/rag/index/rsot"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-query",
    "label": "Interroger l’assistant gouverné",
    "method": "POST",
    "path": "/v1/rag/query"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-answers",
    "label": "Lister les réponses citées",
    "method": "GET",
    "path": "/v1/rag/answers"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-answer-get",
    "label": "Consulter une réponse citée",
    "method": "GET",
    "path": "/v1/rag/answers/get"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-job-create",
    "label": "Créer un job RAG",
    "method": "POST",
    "path": "/v1/rag/jobs/create"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-jobs",
    "label": "Lister les jobs RAG",
    "method": "GET",
    "path": "/v1/rag/jobs"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-job-get",
    "label": "Consulter un job RAG",
    "method": "GET",
    "path": "/v1/rag/jobs/get"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-job-run",
    "label": "Exécuter une tranche de job RAG",
    "method": "POST",
    "path": "/v1/rag/jobs/run"
  },
  {
    "moduleId": "rsot",
    "moduleLabel": "RSOT",
    "id": "rag-job-artifact",
    "label": "Télécharger un export RAG",
    "method": "GET",
    "path": "/v1/rag/jobs/artifact"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-dashboard",
    "label": "Dashboard IPAM",
    "method": "GET",
    "path": "/v1/ipam/ui-dashboard"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-search",
    "label": "Rechercher dans l’IPAM",
    "method": "GET",
    "path": "/v1/ipam/ui-search"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-vrf",
    "label": "Définir une VRF",
    "method": "POST",
    "path": "/v1/ipam/vrfs"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-aggregate",
    "label": "Définir un agrégat IP",
    "method": "POST",
    "path": "/v1/ipam/aggregates"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-prefix",
    "label": "Définir un préfixe IP",
    "method": "POST",
    "path": "/v1/ipam/prefixes"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-list-prefixes",
    "label": "Lister les préfixes",
    "method": "GET",
    "path": "/v1/ipam/prefixes"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-range",
    "label": "Définir une plage IP",
    "method": "POST",
    "path": "/v1/ipam/ranges"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-register-address",
    "label": "Enregistrer une adresse IP",
    "method": "POST",
    "path": "/v1/ipam/addresses"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-allocate",
    "label": "Allouer une adresse IP",
    "method": "POST",
    "path": "/v1/ipam/allocate"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-reservation-wizard",
    "label": "Assistant de réservation IP",
    "method": "POST",
    "path": "/v1/ipam/reservation-wizard"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-capacity",
    "label": "Calculer la capacité d’un préfixe",
    "method": "GET",
    "path": "/v1/ipam/capacity"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-network-bindings",
    "label": "Afficher les bindings réseau",
    "method": "GET",
    "path": "/v1/ipam/network-bindings"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-topology",
    "label": "Topologie opérationnelle IPAM",
    "method": "GET",
    "path": "/v1/ipam/topology"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-vlan-group",
    "label": "Définir un groupe VLAN",
    "method": "POST",
    "path": "/v1/ipam/vlan-groups"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-vxlan-vni",
    "label": "Définir un VXLAN VNI",
    "method": "POST",
    "path": "/v1/ipam/vxlan-vnis"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-vlan",
    "label": "Définir un VLAN",
    "method": "POST",
    "path": "/v1/ipam/vlans"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-asn",
    "label": "Définir un ASN",
    "method": "POST",
    "path": "/v1/ipam/asns"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-define-bgp-peer",
    "label": "Définir un peer BGP",
    "method": "POST",
    "path": "/v1/ipam/bgp-peers"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-observe-dns",
    "label": "Observer un enregistrement DNS",
    "method": "POST",
    "path": "/v1/ipam/dns-observations"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-observe-dhcp",
    "label": "Observer un bail DHCP",
    "method": "POST",
    "path": "/v1/ipam/dhcp-leases"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-conflicts",
    "label": "Détecter les conflits",
    "method": "GET",
    "path": "/v1/ipam/conflicts"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "ipam-ddi-preview",
    "label": "Prévisualiser DDI",
    "method": "POST",
    "path": "/v1/ipam/ddi-preview"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "network-config-baseline-upsert",
    "label": "Créer ou réviser une golden configuration",
    "method": "POST",
    "path": "/v1/network-config/baselines/upsert"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "network-config-baseline-list",
    "label": "Lister les golden configurations",
    "method": "GET",
    "path": "/v1/network-config/baselines"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "network-config-baseline-retire",
    "label": "Retirer une golden configuration",
    "method": "POST",
    "path": "/v1/network-config/baselines/retire"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "network-config-observation-submit",
    "label": "Ingérer une configuration découverte",
    "method": "POST",
    "path": "/v1/network-config/observations/submit"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "network-config-observation-list",
    "label": "Lister les configurations découvertes",
    "method": "GET",
    "path": "/v1/network-config/observations"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "network-config-assessment",
    "label": "Évaluer la dérive réseau",
    "method": "GET",
    "path": "/v1/network-config/assessment"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "flow-declaration-upsert",
    "label": "Créer ou réviser un flux déclaré",
    "method": "POST",
    "path": "/v1/flows/declarations/upsert"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "flow-declaration-list",
    "label": "Lister les flux déclarés",
    "method": "GET",
    "path": "/v1/flows/declarations"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "flow-declaration-retire",
    "label": "Retirer un flux déclaré",
    "method": "POST",
    "path": "/v1/flows/declarations/retire"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "flow-observation-submit",
    "label": "Ingérer un flux observé",
    "method": "POST",
    "path": "/v1/flows/observations/submit"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "flow-observation-list",
    "label": "Lister les flux observés",
    "method": "GET",
    "path": "/v1/flows/observations"
  },
  {
    "moduleId": "ipam",
    "moduleLabel": "IPAM",
    "id": "flow-matrix",
    "label": "Comparer flux déclarés et observés",
    "method": "GET",
    "path": "/v1/flows/matrix"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-sites",
    "label": "Lister les sites DCIM",
    "method": "GET",
    "path": "/v1/dcim/sites"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-site",
    "label": "Consulter un site DCIM",
    "method": "GET",
    "path": "/v1/dcim/site"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-grant-upsert",
    "label": "Affecter un accès à un site",
    "method": "POST",
    "path": "/v1/multisite/site-access/grants/upsert"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-grant-revoke",
    "label": "Révoquer un accès à un site",
    "method": "POST",
    "path": "/v1/multisite/site-access/grants/revoke"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-grants",
    "label": "Lister les accès par site",
    "method": "GET",
    "path": "/v1/multisite/site-access/grants"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-sites",
    "label": "Lister les sites accessibles",
    "method": "GET",
    "path": "/v1/multisite/sites"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-report-generate",
    "label": "Générer un rapport multisite",
    "method": "POST",
    "path": "/v1/multisite/reports/generate"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-reports",
    "label": "Lister les rapports multisites",
    "method": "GET",
    "path": "/v1/multisite/reports"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-report-get",
    "label": "Consulter un rapport multisite",
    "method": "GET",
    "path": "/v1/multisite/reports/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-dr-plan-configure",
    "label": "Configurer un plan de reprise multisite",
    "method": "POST",
    "path": "/v1/multisite/disaster-recovery/plans/configure"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-dr-plan-disable",
    "label": "Désactiver un plan de reprise multisite",
    "method": "POST",
    "path": "/v1/multisite/disaster-recovery/plans/disable"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-dr-plans",
    "label": "Lister les plans de reprise multisites",
    "method": "GET",
    "path": "/v1/multisite/disaster-recovery/plans"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-dr-plan-get",
    "label": "Consulter un plan de reprise multisite",
    "method": "GET",
    "path": "/v1/multisite/disaster-recovery/plans/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-dr-drill-execute",
    "label": "Enregistrer un exercice de perte du site primaire",
    "method": "POST",
    "path": "/v1/multisite/disaster-recovery/drills/execute"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-dr-drills",
    "label": "Lister les exercices de reprise multisites",
    "method": "GET",
    "path": "/v1/multisite/disaster-recovery/drills"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-dr-drill-get",
    "label": "Consulter un exercice de reprise multisite",
    "method": "GET",
    "path": "/v1/multisite/disaster-recovery/drills/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-route-configure",
    "label": "Configurer une route Discovery régionale",
    "method": "POST",
    "path": "/v1/multisite/regional-discovery/routes/configure"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-route-disable",
    "label": "Désactiver une route Discovery régionale",
    "method": "POST",
    "path": "/v1/multisite/regional-discovery/routes/disable"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-routes",
    "label": "Lister les routes Discovery régionales",
    "method": "GET",
    "path": "/v1/multisite/regional-discovery/routes"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-route-get",
    "label": "Consulter une route Discovery régionale",
    "method": "GET",
    "path": "/v1/multisite/regional-discovery/routes/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "multisite-job-route",
    "label": "Router un job Discovery régional",
    "method": "POST",
    "path": "/v1/multisite/regional-discovery/jobs/route"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-site-create",
    "label": "Créer un site DCIM",
    "method": "POST",
    "path": "/v1/dcim/site/create"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-site-update",
    "label": "Modifier un site DCIM",
    "method": "POST",
    "path": "/v1/dcim/site/update"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-site-delete",
    "label": "Retirer un site DCIM",
    "method": "POST",
    "path": "/v1/dcim/site/delete"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-buildings",
    "label": "Lister les bâtiments",
    "method": "GET",
    "path": "/v1/dcim/buildings"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-building",
    "label": "Consulter un bâtiment",
    "method": "GET",
    "path": "/v1/dcim/building"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-building-create",
    "label": "Créer un bâtiment",
    "method": "POST",
    "path": "/v1/dcim/building/create"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-building-update",
    "label": "Modifier un bâtiment",
    "method": "POST",
    "path": "/v1/dcim/building/update"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-building-delete",
    "label": "Retirer un bâtiment",
    "method": "POST",
    "path": "/v1/dcim/building/delete"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-floors",
    "label": "Lister les étages",
    "method": "GET",
    "path": "/v1/dcim/floors"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-floor",
    "label": "Consulter un étage",
    "method": "GET",
    "path": "/v1/dcim/floor"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-rooms-list",
    "label": "Lister les salles",
    "method": "GET",
    "path": "/v1/dcim/rooms"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-room",
    "label": "Consulter une salle",
    "method": "GET",
    "path": "/v1/dcim/room"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-room-create",
    "label": "Créer une salle",
    "method": "POST",
    "path": "/v1/dcim/room/create"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-define-room",
    "label": "Créer une hiérarchie physique",
    "method": "POST",
    "path": "/v1/dcim/rooms"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-room-update",
    "label": "Modifier une salle",
    "method": "POST",
    "path": "/v1/dcim/room/update"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-room-delete",
    "label": "Retirer une salle",
    "method": "POST",
    "path": "/v1/dcim/room/delete"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-racks",
    "label": "Lister les chassis/racks",
    "method": "GET",
    "path": "/v1/dcim/racks"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-rack",
    "label": "Consulter un chassis/rack",
    "method": "GET",
    "path": "/v1/dcim/rack"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-rack-create",
    "label": "Créer un chassis/rack",
    "method": "POST",
    "path": "/v1/dcim/racks"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-rack-update",
    "label": "Modifier un chassis/rack",
    "method": "POST",
    "path": "/v1/dcim/rack/update"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-rack-delete",
    "label": "Retirer un chassis/rack",
    "method": "POST",
    "path": "/v1/dcim/rack/delete"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-zones",
    "label": "Lister les zones",
    "method": "GET",
    "path": "/v1/dcim/zones"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-zone",
    "label": "Consulter une zone",
    "method": "GET",
    "path": "/v1/dcim/zone"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-zone-create",
    "label": "Créer une zone",
    "method": "POST",
    "path": "/v1/dcim/zone/create"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-zone-update",
    "label": "Modifier une zone",
    "method": "POST",
    "path": "/v1/dcim/zone/update"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-zone-delete",
    "label": "Retirer une zone",
    "method": "POST",
    "path": "/v1/dcim/zone/delete"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-topology-catalog",
    "label": "Catalogue dépendances DCIM",
    "method": "GET",
    "path": "/v1/dcim/topology-catalog"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-locate-equipment",
    "label": "Localiser un équipement",
    "method": "POST",
    "path": "/v1/dcim/locations"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-rack-capacity",
    "label": "Capacité rack",
    "method": "GET",
    "path": "/v1/dcim/rack-capacity"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-room-plan",
    "label": "Plan de salle",
    "method": "GET",
    "path": "/v1/dcim/room-plan"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-rack-elevation",
    "label": "Élévation rack",
    "method": "GET",
    "path": "/v1/dcim/rack-elevation"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-patch-panel",
    "label": "Définir un panneau de brassage",
    "method": "POST",
    "path": "/v1/dcim/patch-panels"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-port",
    "label": "Définir un port DCIM",
    "method": "POST",
    "path": "/v1/dcim/ports"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-cable",
    "label": "Connecter un câble",
    "method": "POST",
    "path": "/v1/dcim/cables"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-cable-trace",
    "label": "Tracer un câble",
    "method": "GET",
    "path": "/v1/dcim/cable-trace"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-power-device",
    "label": "Définir un équipement électrique",
    "method": "POST",
    "path": "/v1/dcim/power-devices"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-power-circuit",
    "label": "Définir un circuit électrique",
    "method": "POST",
    "path": "/v1/dcim/power-circuits"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-cooling-zone",
    "label": "Définir une zone de refroidissement",
    "method": "POST",
    "path": "/v1/dcim/cooling-zones"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-power-reservation",
    "label": "Réserver la puissance équipement",
    "method": "POST",
    "path": "/v1/dcim/power-reservations"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-sheet-list",
    "label": "Lister les fiches d’intervention",
    "method": "GET",
    "path": "/v1/field-operation-sheets"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-sheet-get",
    "label": "Consulter une fiche d’intervention",
    "method": "GET",
    "path": "/v1/field-operation-sheets/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-sheet-generate",
    "label": "Générer une fiche d’intervention",
    "method": "POST",
    "path": "/v1/field-operation-sheets/generate"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-lock-acquire",
    "label": "Verrouiller la cible",
    "method": "POST",
    "path": "/v1/intervention-locks/acquire"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-operation-start",
    "label": "Démarrer l’intervention",
    "method": "POST",
    "path": "/v1/field-operation-sheets/start"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-checklist-record",
    "label": "Renseigner une étape de checklist",
    "method": "POST",
    "path": "/v1/field-operation-sheets/checklist"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-evidence-attach",
    "label": "Joindre une preuve terrain",
    "method": "POST",
    "path": "/v1/field-evidence/attach"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-evidence-list",
    "label": "Lister les preuves terrain",
    "method": "GET",
    "path": "/v1/field-evidence"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-evidence-validate",
    "label": "Valider une preuve terrain",
    "method": "POST",
    "path": "/v1/field-evidence/validate"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-operation-complete",
    "label": "Clôturer l’intervention",
    "method": "POST",
    "path": "/v1/field-operation-sheets/complete"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-operation-cancel",
    "label": "Annuler l’intervention",
    "method": "POST",
    "path": "/v1/field-operation-sheets/cancel"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-qr-verify",
    "label": "Vérifier un QR code terrain",
    "method": "POST",
    "path": "/v1/qr-codes/verify"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-lock-release",
    "label": "Libérer le verrou terrain",
    "method": "POST",
    "path": "/v1/intervention-locks/release"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-offline-create",
    "label": "Créer un paquet hors ligne",
    "method": "POST",
    "path": "/v1/offline-sync-packages/create"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-offline-list",
    "label": "Lister les paquets hors ligne",
    "method": "GET",
    "path": "/v1/offline-sync-packages"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-offline-get",
    "label": "Consulter un paquet hors ligne",
    "method": "GET",
    "path": "/v1/offline-sync-packages/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "field-offline-sync",
    "label": "Synchroniser un paquet hors ligne",
    "method": "POST",
    "path": "/v1/offline-sync-packages/synchronize"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-source-create",
    "label": "Enregistrer une source de mesure",
    "method": "POST",
    "path": "/v1/greenops/measurement-sources/create"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-sources",
    "label": "Lister les sources de mesure",
    "method": "GET",
    "path": "/v1/greenops/measurement-sources"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-policy-upsert",
    "label": "Configurer la politique GreenOps d’un site",
    "method": "POST",
    "path": "/v1/greenops/policies/upsert"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-policy-get",
    "label": "Consulter la politique GreenOps",
    "method": "GET",
    "path": "/v1/greenops/policies/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-factor-create",
    "label": "Enregistrer un facteur carbone",
    "method": "POST",
    "path": "/v1/greenops/carbon-factors/create"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-factors",
    "label": "Lister les facteurs carbone",
    "method": "GET",
    "path": "/v1/greenops/carbon-factors"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-measurement-ingest",
    "label": "Ingérer une mesure énergétique",
    "method": "POST",
    "path": "/v1/greenops/energy-measurements/ingest"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-measurements",
    "label": "Lister les mesures énergétiques",
    "method": "GET",
    "path": "/v1/greenops/energy-measurements"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-report-generate",
    "label": "Générer un rapport de durabilité",
    "method": "POST",
    "path": "/v1/greenops/reports/generate"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-report-get",
    "label": "Consulter un rapport de durabilité",
    "method": "GET",
    "path": "/v1/greenops/reports/get"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-reports",
    "label": "Lister les rapports de durabilité",
    "method": "GET",
    "path": "/v1/greenops/reports"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-report-export",
    "label": "Exporter un rapport de durabilité",
    "method": "GET",
    "path": "/v1/greenops/reports/export"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-anomalies",
    "label": "Lister les anomalies énergétiques",
    "method": "GET",
    "path": "/v1/greenops/anomalies"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-forecasts",
    "label": "Lister les prévisions de capacité",
    "method": "GET",
    "path": "/v1/greenops/capacity-forecasts"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-candidates",
    "label": "Lister les recommandations de consolidation",
    "method": "GET",
    "path": "/v1/greenops/consolidation-candidates"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "greenops-scores",
    "label": "Lister les scores GreenOps",
    "method": "GET",
    "path": "/v1/greenops/green-scores"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-digital-twin",
    "label": "Jumeau numérique salle",
    "method": "GET",
    "path": "/v1/dcim/digital-twin"
  },
  {
    "moduleId": "dcim",
    "moduleLabel": "DCIM",
    "id": "dcim-energy-cooling-capacity",
    "label": "Capacité énergie/refroidissement",
    "method": "GET",
    "path": "/v1/dcim/energy-cooling-capacity"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-organizations",
    "label": "Lister les organisations",
    "method": "GET",
    "path": "/v1/itam/organizations"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-organization",
    "label": "Voir une organisation",
    "method": "GET",
    "path": "/v1/itam/organization"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-organization-create",
    "label": "Créer une organisation",
    "method": "POST",
    "path": "/v1/itam/organization/create"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-organization-update",
    "label": "Modifier une organisation",
    "method": "POST",
    "path": "/v1/itam/organization/update"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-organization-delete",
    "label": "Retirer une organisation",
    "method": "POST",
    "path": "/v1/itam/organization/delete"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-partners",
    "label": "Lister les partenaires",
    "method": "GET",
    "path": "/v1/itam/partners"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-partner",
    "label": "Voir un partenaire",
    "method": "GET",
    "path": "/v1/itam/partner"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-partner-create",
    "label": "Créer un partenaire",
    "method": "POST",
    "path": "/v1/itam/partner/create"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-partner-update",
    "label": "Modifier un partenaire",
    "method": "POST",
    "path": "/v1/itam/partner/update"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-partner-delete",
    "label": "Retirer un partenaire",
    "method": "POST",
    "path": "/v1/itam/partner/delete"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-tenants",
    "label": "Lister les filiales/subdivisions",
    "method": "GET",
    "path": "/v1/itam/tenants"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-tenant",
    "label": "Voir une filiale/subdivision",
    "method": "GET",
    "path": "/v1/itam/tenant"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-tenant-create",
    "label": "Créer une filiale/subdivision",
    "method": "POST",
    "path": "/v1/itam/tenant/create"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-tenant-update",
    "label": "Modifier une filiale/subdivision",
    "method": "POST",
    "path": "/v1/itam/tenant/update"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-tenant-delete",
    "label": "Retirer une filiale/subdivision",
    "method": "POST",
    "path": "/v1/itam/tenant/delete"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-support-profile",
    "label": "Profil support actif",
    "method": "GET",
    "path": "/v1/itam/support-profile"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-support-coverage",
    "label": "Couverture support actif",
    "method": "GET",
    "path": "/v1/itam/support-coverage"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-register-manufacturer",
    "label": "Déclarer garantie constructeur",
    "method": "POST",
    "path": "/v1/itam/support-profile/manufacturer"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-add-third-party",
    "label": "Ajouter support tiers",
    "method": "POST",
    "path": "/v1/itam/support-profile/third-party"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-software-license",
    "label": "Licence logicielle",
    "method": "GET",
    "path": "/v1/itam/software-license"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-software-compliance",
    "label": "Conformité licence",
    "method": "GET",
    "path": "/v1/itam/software-license/compliance"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-register-software",
    "label": "Déclarer licence logicielle",
    "method": "POST",
    "path": "/v1/itam/software-license"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "itam-update-license-assignment",
    "label": "Mettre à jour affectation licence",
    "method": "POST",
    "path": "/v1/itam/software-license/assignment"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-rule-create",
    "label": "Créer une règle d’allocation",
    "method": "POST",
    "path": "/v1/finops/allocation-rules/create"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-rules",
    "label": "Lister les règles d’allocation",
    "method": "GET",
    "path": "/v1/finops/allocation-rules"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-import-submit",
    "label": "Importer des coûts",
    "method": "POST",
    "path": "/v1/finops/import-jobs/submit"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-import-get",
    "label": "Consulter un import de coûts",
    "method": "GET",
    "path": "/v1/finops/import-jobs/get"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-imports",
    "label": "Lister les imports de coûts",
    "method": "GET",
    "path": "/v1/finops/import-jobs"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-import-run",
    "label": "Exécuter un import de coûts",
    "method": "POST",
    "path": "/v1/finops/import-jobs/run"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-import-cancel",
    "label": "Annuler un import de coûts",
    "method": "POST",
    "path": "/v1/finops/import-jobs/cancel"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-costs",
    "label": "Lister les coûts normalisés",
    "method": "GET",
    "path": "/v1/finops/cost-records"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-budget-upsert",
    "label": "Créer ou modifier un budget",
    "method": "POST",
    "path": "/v1/finops/budgets/upsert"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-budgets",
    "label": "Lister les budgets",
    "method": "GET",
    "path": "/v1/finops/budgets"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-period-close",
    "label": "Clôturer une période financière",
    "method": "POST",
    "path": "/v1/finops/periods/close"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-periods",
    "label": "Lister les périodes financières",
    "method": "GET",
    "path": "/v1/finops/periods"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-report-generate",
    "label": "Générer un showback / chargeback",
    "method": "POST",
    "path": "/v1/finops/reports/generate"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-report-get",
    "label": "Consulter un rapport financier",
    "method": "GET",
    "path": "/v1/finops/reports/get"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-reports",
    "label": "Lister les rapports financiers",
    "method": "GET",
    "path": "/v1/finops/reports"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-report-export",
    "label": "Exporter un rapport financier",
    "method": "GET",
    "path": "/v1/finops/reports/export"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-anomalies",
    "label": "Lister les anomalies de coûts",
    "method": "GET",
    "path": "/v1/finops/anomalies"
  },
  {
    "moduleId": "itam",
    "moduleLabel": "ITAM",
    "id": "finops-forecasts",
    "label": "Lister les prévisions de coûts",
    "method": "GET",
    "path": "/v1/finops/forecasts"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-evidence-list",
    "label": "Lister les preuves immuables",
    "method": "GET",
    "path": "/v1/discovery/evidence-list"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-evidence",
    "label": "Voir une preuve immuable",
    "method": "GET",
    "path": "/v1/discovery/evidence"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-evidence-submit",
    "label": "Enregistrer une preuve Discovery",
    "method": "POST",
    "path": "/v1/discovery/evidence"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-reconciliation-list",
    "label": "Lister les rapprochements",
    "method": "GET",
    "path": "/v1/discovery/reconciliation-list"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-reconciliation",
    "label": "Voir un rapprochement",
    "method": "GET",
    "path": "/v1/discovery/reconciliation"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-reconcile",
    "label": "Rapprocher plusieurs preuves",
    "method": "POST",
    "path": "/v1/discovery/reconciliation"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-reconciliation-resolve",
    "label": "Résoudre les conflits",
    "method": "POST",
    "path": "/v1/discovery/reconciliation/resolve"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-protocol-profiles",
    "label": "Lister les profils protocoles",
    "method": "GET",
    "path": "/v1/discovery/protocol-profiles"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-protocol-profile-create",
    "label": "Créer un profil SNMP/SSH/WinRM",
    "method": "POST",
    "path": "/v1/discovery/protocol-profile/create"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-protocol-profile-update",
    "label": "Modifier un profil protocole",
    "method": "POST",
    "path": "/v1/discovery/protocol-profile/update"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-protocol-profile-delete",
    "label": "Désactiver un profil protocole",
    "method": "POST",
    "path": "/v1/discovery/protocol-profile/delete"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-integration-profiles",
    "label": "Lister profils virtualisation/cloud",
    "method": "GET",
    "path": "/v1/discovery/integration-profiles"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-integration-profile-create",
    "label": "Créer profil VMware/Cloud/Kubernetes",
    "method": "POST",
    "path": "/v1/discovery/integration-profile/create"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-integration-profile-update",
    "label": "Modifier profil virtualisation/cloud",
    "method": "POST",
    "path": "/v1/discovery/integration-profile/update"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-integration-profile-delete",
    "label": "Désactiver profil virtualisation/cloud",
    "method": "POST",
    "path": "/v1/discovery/integration-profile/delete"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "local-discovery-plan",
    "label": "Plan discovery locale Lite/Pro",
    "method": "POST",
    "path": "/v1/discovery/local-plan"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "agent-bootstrap-plan",
    "label": "Plan bootstrap agent Enterprise",
    "method": "POST",
    "path": "/v1/discovery/agent-bootstrap-plan"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "collectors-list",
    "label": "Lister les agents proxy Enterprise",
    "method": "GET",
    "path": "/v1/discovery/collectors"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "collectors-register",
    "label": "Enregistrer un agent proxy Enterprise",
    "method": "POST",
    "path": "/v1/discovery/collectors"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job-list",
    "label": "Lister les jobs Discovery",
    "method": "GET",
    "path": "/v1/discovery/jobs"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job",
    "label": "Voir un job Discovery",
    "method": "GET",
    "path": "/v1/discovery/job"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job-submit",
    "label": "Soumettre un job idempotent",
    "method": "POST",
    "path": "/v1/discovery/jobs"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job-claim",
    "label": "Réserver le prochain job",
    "method": "POST",
    "path": "/v1/discovery/jobs/claim"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job-renew",
    "label": "Renouveler le bail d’un job",
    "method": "POST",
    "path": "/v1/discovery/jobs/renew"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job-complete",
    "label": "Terminer un job",
    "method": "POST",
    "path": "/v1/discovery/jobs/complete"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job-fail",
    "label": "Déclarer l’échec d’un job",
    "method": "POST",
    "path": "/v1/discovery/jobs/fail"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "discovery-job-replay",
    "label": "Réexécuter un job en DLQ",
    "method": "POST",
    "path": "/v1/discovery/jobs/replay"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "job-authorize",
    "label": "Autoriser un job collector",
    "method": "POST",
    "path": "/v1/discovery/jobs/authorize"
  },
  {
    "moduleId": "data",
    "moduleLabel": "Data",
    "id": "import-bulk-progress",
    "label": "Progression import massif",
    "method": "GET",
    "path": "/v1/imports/bulk-progress"
  },
  {
    "moduleId": "data",
    "moduleLabel": "Data",
    "id": "import-bulk-rollback",
    "label": "Rollback import massif",
    "method": "POST",
    "path": "/v1/imports/bulk-rollback"
  },
  {
    "moduleId": "data",
    "moduleLabel": "Data",
    "id": "import-migration-guide",
    "label": "Guide migration données",
    "method": "GET",
    "path": "/v1/imports/migration-guide"
  },
  {
    "moduleId": "data",
    "moduleLabel": "Data",
    "id": "export-artifact-chunk",
    "label": "Chunk export signé",
    "method": "GET",
    "path": "/v1/exports/artifact-chunk"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "itsm-providers",
    "label": "Politiques connecteurs ITSM",
    "method": "GET",
    "path": "/v1/integrations/itsm/providers"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "servicenow-validate",
    "label": "Valider connecteur ServiceNow",
    "method": "POST",
    "path": "/v1/integrations/itsm/servicenow/validate"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "servicenow-ci-sync-plan",
    "label": "Plan synchro CI ServiceNow",
    "method": "POST",
    "path": "/v1/integrations/itsm/servicenow/ci-sync-plan"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "jira-validate",
    "label": "Valider connecteur Jira Assets",
    "method": "POST",
    "path": "/v1/integrations/itsm/jira/validate"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "jira-asset-sync-plan",
    "label": "Plan synchro Assets Jira",
    "method": "POST",
    "path": "/v1/integrations/itsm/jira/asset-sync-plan"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "glpi-validate",
    "label": "Valider connecteur GLPI Inventory",
    "method": "POST",
    "path": "/v1/integrations/itsm/glpi/validate"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "glpi-asset-sync-plan",
    "label": "Plan synchro inventaire GLPI",
    "method": "POST",
    "path": "/v1/integrations/itsm/glpi/asset-sync-plan"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "freshservice-validate",
    "label": "Valider connecteur Freshservice Assets",
    "method": "POST",
    "path": "/v1/integrations/itsm/freshservice/validate"
  },
  {
    "moduleId": "integrations",
    "moduleLabel": "Intégrations",
    "id": "freshservice-asset-sync-plan",
    "label": "Plan synchro Assets Freshservice",
    "method": "POST",
    "path": "/v1/integrations/itsm/freshservice/asset-sync-plan"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "edition-policies",
    "label": "Politiques éditions et quotas",
    "method": "GET",
    "path": "/v1/editions/policies"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "edition-feature-check",
    "label": "Vérifier une capacité édition",
    "method": "GET",
    "path": "/v1/editions/feature-check"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "edition-quota-check",
    "label": "Vérifier un quota édition",
    "method": "GET",
    "path": "/v1/editions/quota-check"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "tokens-list",
    "label": "Lister les tokens techniques",
    "method": "GET",
    "path": "/v1/security/tokens"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "effective-identity",
    "label": "Identité effective",
    "method": "GET",
    "path": "/v1/identity/effective"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "access-rules",
    "label": "Politiques d’accès",
    "method": "GET",
    "path": "/v1/access/rules"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "audit-events",
    "label": "Événements d’audit",
    "method": "GET",
    "path": "/v1/audit/events"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "audit-integrity",
    "label": "Intégrité audit",
    "method": "GET",
    "path": "/v1/audit/integrity"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "certificate-import",
    "label": "Importer une chaîne PEM",
    "method": "POST",
    "path": "/v1/certificates/import"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "certificate-get",
    "label": "Consulter un certificat",
    "method": "GET",
    "path": "/v1/certificates/get"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "certificate-list",
    "label": "Lister les certificats",
    "method": "GET",
    "path": "/v1/certificates"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "certificate-retire",
    "label": "Retirer un certificat",
    "method": "POST",
    "path": "/v1/certificates/retire"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "certificate-endpoint-observe",
    "label": "Observer un endpoint TLS",
    "method": "POST",
    "path": "/v1/certificates/endpoints/observe"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "certificate-endpoint-list",
    "label": "Lister les endpoints TLS",
    "method": "GET",
    "path": "/v1/certificates/endpoints"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "certificate-assessment",
    "label": "Évaluer la conformité PKI",
    "method": "GET",
    "path": "/v1/certificates/assessment"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-import",
    "label": "Importer une SBOM",
    "method": "POST",
    "path": "/v1/sbom/documents/import"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-documents",
    "label": "Lister les SBOM",
    "method": "GET",
    "path": "/v1/sbom/documents"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-document-get",
    "label": "Consulter une SBOM",
    "method": "GET",
    "path": "/v1/sbom/documents/get"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-vulnerability-import",
    "label": "Importer une vulnérabilité",
    "method": "POST",
    "path": "/v1/sbom/vulnerabilities/import"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-vulnerabilities",
    "label": "Lister les vulnérabilités",
    "method": "GET",
    "path": "/v1/sbom/vulnerabilities"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-exposure-upsert",
    "label": "Définir le contexte d’exposition",
    "method": "POST",
    "path": "/v1/sbom/exposures/upsert"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-exposures",
    "label": "Lister les contextes d’exposition",
    "method": "GET",
    "path": "/v1/sbom/exposures"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-exposure-get",
    "label": "Consulter un contexte d’exposition",
    "method": "GET",
    "path": "/v1/sbom/exposures/get"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-risk-assess",
    "label": "Évaluer le risque contextualisé",
    "method": "POST",
    "path": "/v1/sbom/risk/assess"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-findings",
    "label": "Lister les constats de risque",
    "method": "GET",
    "path": "/v1/sbom/findings"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-risk-export",
    "label": "Exporter le risque SBOM",
    "method": "GET",
    "path": "/v1/sbom/risk/export"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-compare",
    "label": "Comparer deux releases SBOM",
    "method": "POST",
    "path": "/v1/sbom/comparisons/create"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-comparisons",
    "label": "Lister les comparaisons SBOM",
    "method": "GET",
    "path": "/v1/sbom/comparisons"
  },
  {
    "moduleId": "security",
    "moduleLabel": "Sécurité",
    "id": "sbom-comparison-get",
    "label": "Consulter une comparaison SBOM",
    "method": "GET",
    "path": "/v1/sbom/comparisons/get"
  }
,
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-topologies-list",
    "label": "Lister les instantanés Kubernetes",
    "method": "GET",
    "path": "/v1/kubernetes/topologies"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-topology-latest",
    "label": "Consulter le dernier inventaire Kubernetes",
    "method": "GET",
    "path": "/v1/kubernetes/topologies/latest"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-topology-graph",
    "label": "Afficher la topologie Kubernetes et physique",
    "method": "GET",
    "path": "/v1/kubernetes/topologies/latest-topology"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-exposure-latest",
    "label": "Analyser les expositions réseau cloud-native",
    "method": "GET",
    "path": "/v1/kubernetes/topologies/latest-exposure"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-exposure-snapshot",
    "label": "Analyser les expositions d’un instantané Kubernetes",
    "method": "GET",
    "path": "/v1/kubernetes/topologies/exposure"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-security-latest",
    "label": "Corréler la sécurité cloud-native du cluster",
    "method": "GET",
    "path": "/v1/kubernetes/topologies/latest-security"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-security-snapshot",
    "label": "Corréler la sécurité d’un instantané Kubernetes",
    "method": "GET",
    "path": "/v1/kubernetes/topologies/security"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-topology-import",
    "label": "Importer un inventaire Kubernetes",
    "method": "POST",
    "path": "/v1/kubernetes/topologies/import"
  }
  ,
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-gitops-states-list",
    "label": "Lister les états attendus GitOps Kubernetes",
    "method": "GET",
    "path": "/v1/kubernetes/gitops-states"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-gitops-state-get",
    "label": "Consulter un état attendu GitOps Kubernetes",
    "method": "GET",
    "path": "/v1/kubernetes/gitops-states/get"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-gitops-state-latest",
    "label": "Consulter le dernier état attendu GitOps",
    "method": "GET",
    "path": "/v1/kubernetes/gitops-states/latest"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-gitops-drift-snapshot",
    "label": "Évaluer la dérive GitOps entre deux états",
    "method": "GET",
    "path": "/v1/kubernetes/gitops-states/drift"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-gitops-drift-latest",
    "label": "Évaluer la dérive GitOps actuelle du cluster",
    "method": "GET",
    "path": "/v1/kubernetes/gitops-states/latest-drift"
  },
  {
    "moduleId": "discovery",
    "moduleLabel": "Discovery",
    "id": "kubernetes-gitops-state-import",
    "label": "Importer un état attendu GitOps Kubernetes",
    "method": "POST",
    "path": "/v1/kubernetes/gitops-states/import"
  }
,
{
  "moduleId": "discovery",
  "moduleLabel": "Discovery",
  "id": "kubernetes-capacity-latest",
  "label": "Analyser la capacité actuelle du cluster",
  "method": "GET",
  "path": "/v1/kubernetes/topologies/latest-capacity"
},
{
  "moduleId": "discovery",
  "moduleLabel": "Discovery",
  "id": "kubernetes-capacity-snapshot",
  "label": "Analyser la capacité d’un instantané Kubernetes",
  "method": "GET",
  "path": "/v1/kubernetes/topologies/capacity"
},
{
  "moduleId": "discovery",
  "moduleLabel": "Discovery",
  "id": "kubernetes-capacity-trend",
  "label": "Afficher la tendance de capacité Kubernetes",
  "method": "GET",
  "path": "/v1/kubernetes/topologies/capacity-trend"
},
{
  "moduleId": "discovery",
  "moduleLabel": "Discovery",
  "id": "kubernetes-capacity-export",
  "label": "Exporter la capacité d’un instantané Kubernetes",
  "method": "GET",
  "path": "/v1/kubernetes/topologies/capacity-export"
},
{
  "moduleId": "discovery",
  "moduleLabel": "Discovery",
  "id": "kubernetes-capacity-latest-export",
  "label": "Exporter la capacité actuelle du cluster",
  "method": "GET",
  "path": "/v1/kubernetes/topologies/latest-capacity-export"
}

];

export { OPENINFRA_SEARCH_INDEX };
export default OPENINFRA_SEARCH_INDEX;
