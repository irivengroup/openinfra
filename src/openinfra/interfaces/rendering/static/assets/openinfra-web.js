class OpenInfraApiClient {
  constructor(apiBaseUrl, tenantProvider) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
    this.tenantProvider = tenantProvider;
  }

  async request(operation, payload) {
    const path = this.interpolatePath(operation.path, payload);
    const query = this.buildQuery(operation.query || [], payload);
    const headers = { Accept: "application/json" };
    if (operation.method !== "GET") {
      headers["Content-Type"] = "application/json";
    }
    const body = operation.method === "GET" ? undefined : JSON.stringify(this.buildBody(operation, payload));
    const response = await fetch(`${this.apiBaseUrl}${path}${query}`, {
      method: operation.method,
      credentials: "same-origin",
      headers,
      body
    });
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      throw new Error(typeof data === "string" ? data : JSON.stringify(data));
    }
    return data;
  }

  async getJson(path) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { Accept: "application/json" }
    });
    if (!response.ok) {
      throw new Error(`${path} returned ${response.status}`);
    }
    return response.json();
  }

  interpolatePath(path, payload) {
    return path.replace(/\{([^}]+)\}/g, (_, key) => encodeURIComponent(payload[key] || ""));
  }

  buildQuery(fields, payload) {
    const query = new URLSearchParams();
    for (const field of fields) {
      const value = this.normalizedFieldValue(field, payload[field.name]);
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        query.set(field.name, String(value));
      }
    }
    const tenant = this.tenantProvider();
    if (tenant && !query.has("tenant_id")) {
      query.set("tenant_id", tenant);
    }
    return query.toString() ? `?${query.toString()}` : "";
  }

  buildBody(operation, payload) {
    const body = {};
    for (const field of operation.body || []) {
      const raw = payload[field.name];
      const value = this.normalizedFieldValue(field, raw);
      if (value === undefined || value === null || String(value).trim?.() === "") {
        if (field.required) {
          throw new Error(`Champ obligatoire manquant: ${field.label || field.name}`);
        }
        continue;
      }
      this.assignBodyValue(body, field.target || field.name, value);
    }
    const tenant = this.tenantProvider();
    if (tenant && operation.body && !Object.prototype.hasOwnProperty.call(body, "tenant_id")) {
      body.tenant_id = tenant;
    }
    return body;
  }

  normalizedFieldValue(field, raw) {
    if (raw === undefined || raw === null) {
      return undefined;
    }
    const value = String(raw).trim();
    if (!value) {
      return undefined;
    }
    if (field.type === "number") {
      const parsed = Number(value);
      if (Number.isNaN(parsed)) {
        throw new Error(`Valeur numérique invalide: ${field.label || field.name}`);
      }
      return parsed;
    }
    if (field.type === "boolean") {
      return ["1", "true", "yes", "oui"].includes(value.toLowerCase());
    }
    if (field.type === "csv") {
      return value.split(",").map((item) => item.trim()).filter(Boolean);
    }
    if (field.type === "json") {
      return JSON.parse(value);
    }
    return value;
  }

  assignBodyValue(body, target, value) {
    const parts = target.split(".");
    let current = body;
    for (const part of parts.slice(0, -1)) {
      if (!Object.prototype.hasOwnProperty.call(current, part)) {
        current[part] = {};
      }
      current = current[part];
    }
    current[parts[parts.length - 1]] = value;
  }
}

const OPENINFRA_ICONS = {
  home: "M8 3.293l6 6V15a1 1 0 0 1-1 1h-3v-4H6v4H3a1 1 0 0 1-1-1V9.293l6-6zm5-.793V6l-2-2V2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5z",
  speedometer2: "M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4zM3.732 5.732a.5.5 0 0 1 .707 0l.915.914a.5.5 0 1 1-.708.708l-.914-.915a.5.5 0 0 1 0-.707zM2 10a.5.5 0 0 1 .5-.5h1.586a.5.5 0 0 1 0 1H2.5A.5.5 0 0 1 2 10zm9.5 0a.5.5 0 0 1 .5-.5h1.5a.5.5 0 0 1 0 1H12a.5.5 0 0 1-.5-.5zm.754-4.246a.5.5 0 0 1 0 .707l-.94.94a.5.5 0 1 1-.707-.708l.94-.94a.5.5 0 0 1 .707 0zM9.67 11.71a2 2 0 1 1-3.34-2.19l3.95-3.95a.5.5 0 0 1 .8.6l-1.41 5.54zM8 1a7 7 0 0 0-7 7c0 1.71.61 3.28 1.63 4.5a.5.5 0 0 0 .38.17h9.98a.5.5 0 0 0 .38-.17A6.97 6.97 0 0 0 15 8a7 7 0 0 0-7-7z",
  table: "M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm15 2h-4v3h4V4zm0 4h-4v3h4V8zm0 4h-4v3h3a1 1 0 0 0 1-1v-2zm-5 3v-3H6v3h4zm-5 0v-3H1v2a1 1 0 0 0 1 1h3zm-4-4h4V8H1v3zm0-4h4V4H1v3zm5-3v3h4V4H6zm4 4H6v3h4V8z",
  grid: "M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z",
  people: "M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm-1.559 4.27A4.985 4.985 0 0 0 8 10c-2.67 0-4.9 2.1-4.99 4.71A1 1 0 0 0 4 15h8a1 1 0 0 0 .99-1.29 5.002 5.002 0 0 0-3.549-3.44zM13.5 7a2.5 2.5 0 0 1-1.18 2.12 6.01 6.01 0 0 1 2.2 2.56A1 1 0 0 0 15.5 10.5 3.5 3.5 0 0 0 12 7h1.5z",
  shield: "M5.338 1.59a61.44 61.44 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188A10.7 10.7 0 0 0 8 15a10.7 10.7 0 0 0 3.574-2.976c1.527-1.998 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39 61.44 61.44 0 0 0-2.837-.856C9.552 1.29 8.531 1.067 8 1.067c-.531 0-1.552.223-2.662.523z",
  activity: "M6.5 12a.5.5 0 0 1-.447-.276L3.382 6.382 1.894 9.36A.5.5 0 0 1 1.447 9.636H.5a.5.5 0 0 1 0-1h.638l1.915-3.83a.5.5 0 0 1 .894 0L6.5 9.91l2.553-5.105a.5.5 0 0 1 .894 0l1.915 3.83h3.638a.5.5 0 0 1 0 1h-3.947a.5.5 0 0 1-.447-.276L9.5 6.382l-2.553 5.342A.5.5 0 0 1 6.5 12z"
};

const COMMON_KIND_OPTIONS = ["server", "network-device", "virtual-machine", "application", "database", "service"];
const SOURCE_OPTIONS = ["manual", "import", "backend-discovery", "enterprise-proxy", "api"];

const FIELD_SETS = {
  tenant: { name: "tenant_id", label: "Tenant", defaultValue: "default", placeholder: "default" },
  limit: { name: "limit", label: "Limite", type: "number", placeholder: "100" },
  riKind: { name: "kind", label: "Type de ressource", type: "select", options: COMMON_KIND_OPTIONS },
  tag: { name: "tag", label: "Tag", placeholder: "prod" },
  actor: { name: "actor", label: "Opérateur", required: true, placeholder: "admin@openinfra" },
  riKey: { name: "key", label: "Clé ITRM", required: true, placeholder: "server/srv-db-01" },
  displayName: { name: "display_name", label: "Nom affiché", required: true, placeholder: "srv-db-01" },
  source: { name: "source", label: "Source autoritative", required: true, type: "select", options: SOURCE_OPTIONS },
  serial: { name: "serial", label: "Numéro de série", target: "attributes.serial", placeholder: "SN123456" },
  vendor: { name: "vendor", label: "Constructeur", target: "attributes.vendor", placeholder: "Dell, HPE, Cisco" },
  model: { name: "model", label: "Modèle", target: "attributes.model", placeholder: "PowerEdge R760" },
  site: { name: "site", label: "Site", target: "attributes.site", placeholder: "PAR1" },
  building: { name: "building", label: "Bâtiment", target: "attributes.building", placeholder: "B1" },
  room: { name: "room", label: "Salle", target: "attributes.room", placeholder: "DC-A" },
  row: { name: "row", label: "Ligne salle", target: "attributes.row", placeholder: "Rangée A" },
  column: { name: "column", label: "Colonne salle", target: "attributes.column", placeholder: "Colonne 04" },
  rack: { name: "rack", label: "Rack", target: "attributes.rack", placeholder: "R12" },
  managementIp: { name: "management_ip", label: "IP de management", target: "attributes.management_ip", placeholder: "10.10.10.15" },
  lifecycle: { name: "lifecycle_state", label: "État cycle de vie", target: "attributes.lifecycle_state", type: "select", options: ["planned", "active", "maintenance", "retired"] },
  tags: { name: "tags", label: "Tags", type: "csv", placeholder: "prod,critical,postgres" },
  asOf: { name: "as_of", label: "Date ISO-8601", required: true, placeholder: "2026-07-06T10:00:00+02:00" }
};

const OPENINFRA_MODULES = [
  { id: "overview", label: "Dashboard", icon: "speedometer2", description: "Vue de synthèse, readiness backend, version package, trust web-backend et opérations rapides.", operations: [
    { id: "version", label: "Version runtime", method: "GET", path: "/v1/version", query: [] },
    { id: "schema", label: "Statut schéma DB", method: "GET", path: "/v1/database/schema", query: [] }
  ] },
  { id: "itrm", label: "IT Ressources Management", shortLabel: "ITRM", icon: "table", description: "Inventaire canonique, relations, versions, gouvernance et certification.", operations: [
    { id: "itrm-list", label: "Lister les objets ITRM", method: "GET", path: "/v1/itrm/objects", query: [FIELD_SETS.riKind, FIELD_SETS.tag, FIELD_SETS.limit] },
    { id: "itrm-upsert", label: "Créer / mettre à jour une ressource", method: "POST", path: "/v1/itrm/objects", body: [FIELD_SETS.actor, FIELD_SETS.riKey, { ...FIELD_SETS.riKind, required: true }, FIELD_SETS.displayName, FIELD_SETS.source, FIELD_SETS.serial, FIELD_SETS.vendor, FIELD_SETS.model, FIELD_SETS.site, FIELD_SETS.building, FIELD_SETS.room, FIELD_SETS.row, FIELD_SETS.column, FIELD_SETS.rack, FIELD_SETS.managementIp, FIELD_SETS.lifecycle, FIELD_SETS.tags] },
    { id: "itrm-relations", label: "Lister les relations", method: "GET", path: "/v1/itrm/relations", query: [{ name: "source_key", label: "Ressource source" }, { name: "target_key", label: "Ressource cible" }, { name: "relation_type", label: "Type de relation" }, { ...FIELD_SETS.asOf, required: false }, FIELD_SETS.limit] },
    { id: "itrm-as-of", label: "Restituer une ressource à date", method: "GET", path: "/v1/itrm/object-as-of", query: [FIELD_SETS.riKey, FIELD_SETS.asOf] },
    { id: "itrm-object-audit", label: "Audit d’une ressource", method: "GET", path: "/v1/itrm/object-audit", query: [FIELD_SETS.riKey, FIELD_SETS.limit] },
    { id: "itrm-quality-object", label: "Évaluer la qualité d’une ressource", method: "GET", path: "/v1/itrm/quality/object", query: [FIELD_SETS.riKey] },
    { id: "itrm-quality-summary", label: "Synthèse qualité / certification", method: "GET", path: "/v1/itrm/quality/summary", query: [FIELD_SETS.riKind, FIELD_SETS.tag, FIELD_SETS.limit] },
    { id: "itrm-governance", label: "Évaluer une règle de gouvernance", method: "POST", path: "/v1/itrm/governance/evaluate", body: [
      { name: "object_kind", label: "Type d’objet", required: true, type: "select", options: COMMON_KIND_OPTIONS },
      { name: "incoming_source", label: "Source entrante", required: true, type: "select", options: SOURCE_OPTIONS },
      { name: "existing_serial", label: "Serial existant", target: "existing_attributes.serial" },
      { name: "incoming_serial", label: "Serial entrant", target: "incoming_attributes.serial" },
      { name: "existing_site", label: "Site existant", target: "existing_attributes.site" },
      { name: "incoming_site", label: "Site entrant", target: "incoming_attributes.site" }
    ] }
  ] },
  { id: "ipam", label: "IPAM", icon: "grid", description: "Préfixes, VLANs, VRF, réservations, conflits, capacité et allocations.", operations: [
    { id: "ipam-search", label: "Rechercher dans l’IPAM", method: "GET", path: "/v1/ipam/ui-search", query: [{ name: "query", label: "Recherche", required: true, placeholder: "10.20.0.0/24 ou srv-db" }, { name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-capacity", label: "Calculer la capacité d’un préfixe", method: "GET", path: "/v1/ipam/capacity", query: [{ name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }] },
    { id: "ipam-allocate", label: "Allouer une adresse IP", method: "POST", path: "/v1/ipam/allocate", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }, { name: "hostname", label: "Nom DNS / équipement", required: true, placeholder: "srv-app-01" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "ipam-alloc-srv-app-01" }] },
    { id: "ipam-conflicts", label: "Détecter les conflits", method: "GET", path: "/v1/ipam/conflicts", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] }
  ] },
  { id: "dcim", label: "DCIM", icon: "home", description: "Sites, salles, zones, racks, ports, câbles, énergie et localisation terrain.", operations: [
    { id: "dcim-rack-capacity", label: "Capacité rack", method: "GET", path: "/v1/dcim/rack-capacity", query: [{ name: "site", label: "Site" }, { name: "building", label: "Bâtiment" }, { name: "room", label: "Salle" }, { name: "rack", label: "Rack" }] },
    { id: "dcim-room-plan", label: "Plan de salle", method: "GET", path: "/v1/dcim/room-plan", query: [{ name: "site", label: "Site" }, { name: "building", label: "Bâtiment" }, { name: "room", label: "Salle" }] },
    { id: "dcim-cable-trace", label: "Tracer un câble", method: "GET", path: "/v1/dcim/cable-trace", query: [{ name: "cable_id", label: "Identifiant câble", placeholder: "CAB-000123" }] }
  ] },
  { id: "discovery", label: "Discovery", icon: "activity", description: "Collecte backend locale en Lite/Pro ; agents proxy collectors Enterprise uniquement en topologie étoile.", operations: [
    { id: "collectors-list", label: "Lister les agents proxy Enterprise", method: "GET", path: "/v1/discovery/collectors", query: [{ name: "scope", label: "Scope autorisé" }, FIELD_SETS.limit] },
    { id: "collectors-register", label: "Enregistrer un agent proxy Enterprise", method: "POST", path: "/v1/discovery/collectors", body: [FIELD_SETS.actor, { name: "name", label: "Nom agent proxy", required: true }, { name: "kind", label: "Type", required: true, type: "select", options: ["site-proxy", "network-proxy", "datacenter-proxy"] }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "scopes", label: "Scopes autorisés", type: "csv", required: true, placeholder: "site/paris,network/core" }, { name: "version", label: "Version agent", required: true, defaultValue: "1.0.0" }, { name: "endpoint_url", label: "Endpoint mTLS", required: true, placeholder: "https://collector-paris.openinfra.local" }] },
    { id: "job-authorize", label: "Autoriser un job collector", method: "POST", path: "/v1/discovery/jobs/authorize", body: [{ name: "collector_id", label: "ID agent proxy", required: true }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "requested_scope", label: "Scope demandé", required: true }, { name: "job_type", label: "Type de job", required: true, type: "select", options: ["snmp", "ssh", "winrm", "vmware", "kubernetes"] }, { name: "target", label: "Cible", required: true, placeholder: "10.20.30.10" }] }
  ] },
  { id: "security", label: "Sécurité / RBAC / Audit", shortLabel: "Sécurité", icon: "shield", description: "Identité, RBAC, tokens, politiques d’accès, audit et intégrité.", operations: [
    { id: "tokens-list", label: "Lister les tokens techniques", method: "GET", path: "/v1/security/tokens", query: [FIELD_SETS.limit, { name: "include_inactive", label: "Inclure inactifs", type: "boolean" }] },
    { id: "effective-identity", label: "Identité effective", method: "GET", path: "/v1/identity/effective", query: [{ name: "subject", label: "Sujet", placeholder: "user@example.com" }] },
    { id: "access-rules", label: "Politiques d’accès", method: "GET", path: "/v1/access/rules", query: [FIELD_SETS.limit, { name: "include_inactive", label: "Inclure inactives", type: "boolean" }] },
    { id: "audit-events", label: "Événements d’audit", method: "GET", path: "/v1/audit/events", query: [{ name: "action", label: "Action" }, { name: "target_type", label: "Type cible" }, FIELD_SETS.limit] },
    { id: "audit-integrity", label: "Intégrité audit", method: "GET", path: "/v1/audit/integrity", query: [FIELD_SETS.limit] }
  ] }
];

class OpenInfraDashboard {
  constructor(root) {
    this.root = root;
    this.state = {
      activeModuleId: "overview",
      selected: OPENINFRA_MODULES[0].operations[0],
      openedModules: new Set(["itrm"]),
      tenant: "default",
      config: null,
      ready: null,
      status: null,
      version: null,
      result: null,
      error: null
    };
  }

  async start() {
    await this.refreshRuntime();
    this.render();
  }

  async refreshRuntime() {
    try {
      const configResponse = await fetch("/config.json", { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!configResponse.ok) {
        throw new Error(`Configuration unavailable: ${configResponse.status}`);
      }
      const config = await configResponse.json();
      const [version, ready, status] = await Promise.all([
        fetch("/version", { credentials: "same-origin", headers: { Accept: "application/json" } }).then((response) => response.ok ? response.json() : { version: config.version }),
        fetch("/ready", { credentials: "same-origin", headers: { Accept: "application/json" } }).then((response) => response.ok ? response.json() : { ready: false }),
        fetch("/status", { credentials: "same-origin", headers: { Accept: "application/json" } }).then((response) => response.ok ? response.json() : { protectedForms: "unknown", trust: {} })
      ]);
      this.state = { ...this.state, config, version, ready, status, error: null };
    } catch (error) {
      this.state = { ...this.state, error };
    }
  }

  client() {
    return new OpenInfraApiClient(this.state.config?.apiBaseUrl || "/api", () => this.state.tenant);
  }

  visibleOperations(module) {
    return module.operations;
  }

  componentModules() {
    return OPENINFRA_MODULES.filter((module) => module.id !== "overview");
  }

  moduleStatistics(module) {
    const operations = module.operations.length;
    const readOperations = module.operations.filter((operation) => operation.method === "GET").length;
    const writeOperations = operations - readOperations;
    const fields = module.operations.reduce((total, operation) => total + (operation.query || []).length + (operation.body || []).length, 0);
    const requiredFields = module.operations.reduce((total, operation) => {
      return total + [...(operation.query || []), ...(operation.body || [])].filter((field) => field.required).length;
    }, 0);
    const readPercent = operations === 0 ? 0 : Math.round((readOperations / operations) * 100);
    return {
      operations,
      readOperations,
      writeOperations,
      fields,
      requiredFields,
      readPercent,
      writePercent: 100 - readPercent
    };
  }

  render() {
    const { activeModuleId, selected, config, ready, status, version, error, result } = this.state;
    const operationsCount = OPENINFRA_MODULES.reduce((total, module) => total + module.operations.length, 0);
    const displayedVersion = version?.version || config?.version || "indisponible";
    const protectedForms = status?.protectedForms === "enabled" ? "actifs" : "à configurer";
    this.root.innerHTML = `
      <header>
        <div class="px-3 py-2 bg-dark text-white openinfra-top-header">
          <div class="container-fluid">
            <div class="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start">
              <a href="/" class="d-flex align-items-center my-2 my-lg-0 me-lg-auto text-white text-decoration-none" aria-label="OpenInfra accueil">
                <span class="openinfra-brand-mark me-2">OI</span><span class="fs-5 fw-semibold">OpenInfra</span>
              </a>
              <ul class="nav col-12 col-lg-auto my-2 justify-content-center my-md-0 text-small">
                ${OPENINFRA_MODULES.slice(0, 6).map((module) => `
                  <li><button type="button" class="nav-link border-0 bg-transparent ${activeModuleId === module.id ? "text-secondary" : "text-white"}" data-module-id="${this.escape(module.id)}">
                    ${this.icon(module.icon, "bi d-block mx-auto mb-1 openinfra-top-icon", 24, 24)}${this.escape(module.shortLabel || module.label)}
                  </button></li>
                `).join("")}
              </ul>
            </div>
          </div>
        </div>
      </header>
      <div class="container-fluid">
        <div class="row">
          <nav class="col-lg-3 col-xl-2 openinfra-sidebar" aria-label="Sidebar navigation">
            <div class="openinfra-sidebar-heading">Pilotage</div>
            ${this.renderSidebar()}
            <div class="openinfra-sidebar-heading">État runtime</div>
            <div class="px-2 small text-muted">
              <p><span class="openinfra-status-dot ${ready?.ready === true ? "ready" : "warning"}"></span>Backend ${ready?.ready === true ? "prêt" : "à vérifier"}</p>
              <p>Version : <strong>${this.escape(displayedVersion)}</strong></p>
              <p>Trust web/backend : <strong>${this.escape(config?.webBackendTrust || "server-side")}</strong></p>
              <p>Formulaires protégés : <strong>${this.escape(protectedForms)}</strong></p>
            </div>
          </nav>
          <main class="col-lg-9 col-xl-10 ms-sm-auto openinfra-main">
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-2 mb-3 openinfra-titlebar">
              <div><h1 class="h2">Dashboard de pilotage OpenInfra</h1><p class="text-muted mb-0">Portail BFF server-side : l’opérateur ne saisit aucun token technique ; les secrets PostgreSQL restent côté service web.</p></div>
              <div class="btn-toolbar mb-2 mb-md-0"><span class="badge text-bg-primary me-2">${this.escape(config?.edition || "runtime")}</span><span class="badge text-bg-secondary">${this.escape(config?.authMode || "standard")}</span></div>
            </div>
            ${error ? `<div class="alert alert-warning" role="alert">${this.escape(error.message)}</div>` : ""}
            ${result && activeModuleId !== "overview" ? `<div class="alert alert-success" role="status">Soumission exécutée avec succès.</div>` : ""}
            <div class="row g-3 mb-4">
              ${this.metric("Version", this.escape(displayedVersion))}
              ${this.metric("API", this.escape(config?.apiBaseUrl || "/api"))}
              ${this.metric("Trust", this.escape(config?.webBackendTrust || "server-side"))}
              ${this.metric("Formulaires", this.escape(protectedForms))}
              ${this.metric("Modules", `${operationsCount} opérations`)}
            </div>
            ${this.renderWorkspace(selected, result)}
          </main>
        </div>
      </div>
    `;
    this.bindEvents();
  }

  renderWorkspace(selected, result) {
    if (this.state.activeModuleId === "overview") {
      return this.renderOverviewDashboard();
    }
    return `<section class="card openinfra-operation-card"><div class="card-body">${this.renderOperationPanel(selected, result)}</div></section>`;
  }

  renderOverviewDashboard() {
    const components = this.componentModules();
    const totalOperations = components.reduce((total, module) => total + module.operations.length, 0);
    const totalFields = components.reduce((total, module) => total + this.moduleStatistics(module).fields, 0);
    const totalRequiredFields = components.reduce((total, module) => total + this.moduleStatistics(module).requiredFields, 0);
    return `<section class="openinfra-overview" aria-label="Statistiques des composants OpenInfra">
      <div class="card openinfra-overview-summary mb-4">
        <div class="card-body">
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-3">
            <div>
              <h2 class="h4 mb-1">Accueil — statistiques des composants</h2>
              <p class="text-muted mb-0">Vue de synthèse par composant : métriques fonctionnelles, champs métier exposés et camemberts de répartition lecture/mutation.</p>
            </div>
            <div class="text-end">
              <span class="badge text-bg-primary">${components.length} composants</span>
              <span class="badge text-bg-secondary ms-2">${totalOperations} opérations</span>
            </div>
          </div>
          <div class="row g-3 mt-3">
            ${this.metric("Champs métier", String(totalFields))}
            ${this.metric("Champs obligatoires", String(totalRequiredFields))}
            ${this.metric("Navigation", "Accordéons") }
            ${this.metric("Secrets navigateur", "0 exposé")}
          </div>
        </div>
      </div>
      <div class="row g-3">
        ${components.map((module) => this.renderComponentStatsCard(module)).join("")}
      </div>
    </section>`;
  }

  renderComponentStatsCard(module) {
    const stats = this.moduleStatistics(module);
    const readEnd = `${stats.readPercent}%`;
    const writeEnd = `${stats.readPercent + stats.writePercent}%`;
    return `<article class="col-md-6 col-xxl-4">
      <div class="card h-100 openinfra-component-card">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start gap-3">
            <div>
              <h3 class="h5 mb-1">${this.escape(module.shortLabel || module.label)}</h3>
              <p class="text-muted small mb-0">${this.escape(module.description)}</p>
            </div>
            ${this.icon(module.icon, "openinfra-component-icon", 28, 28)}
          </div>
          <div class="openinfra-component-visual mt-3">
            <div class="openinfra-pie-chart" role="img" aria-label="Camembert ${this.escape(module.label)} : ${stats.readOperations} lectures et ${stats.writeOperations} mutations" style="--oi-read-end: ${readEnd}; --oi-write-end: ${writeEnd};">
              <span>${stats.operations}</span>
            </div>
            <div class="openinfra-pie-legend small">
              <span><i class="openinfra-legend-read"></i>${stats.readOperations} lectures</span>
              <span><i class="openinfra-legend-write"></i>${stats.writeOperations} mutations</span>
            </div>
          </div>
          <div class="row g-2 mt-3 openinfra-component-metrics">
            <div class="col-6"><strong>${stats.operations}</strong><span>Opérations</span></div>
            <div class="col-6"><strong>${stats.fields}</strong><span>Champs métier</span></div>
            <div class="col-6"><strong>${stats.requiredFields}</strong><span>Obligatoires</span></div>
            <div class="col-6"><strong>${stats.writeOperations}</strong><span>Mutations</span></div>
          </div>
        </div>
      </div>
    </article>`;
  }

  renderSidebar() {
    return OPENINFRA_MODULES.map((module) => {
      if (module.id === "overview") {
        return `<button type="button" class="nav-link openinfra-sidebar-dashboard w-100 text-start ${this.state.activeModuleId === module.id ? "active" : ""}" data-operation-id="${this.escape(module.operations[0].id)}">${this.icon(module.icon)}Dashboard</button>`;
      }
      const opened = this.state.openedModules.has(module.id);
      const visibleOperations = this.visibleOperations(module);
      if (visibleOperations.length === 0 && !module.label.toLowerCase().includes(this.state.filter.toLowerCase())) {
        return "";
      }
      return `<section class="openinfra-accordion ${opened ? "open" : ""}">
        <button type="button" class="openinfra-accordion-toggle ${this.state.activeModuleId === module.id ? "active" : ""}" data-accordion-id="${this.escape(module.id)}" aria-expanded="${opened ? "true" : "false"}">
          <span>${this.icon(module.icon)}${this.escape(module.shortLabel || module.label)}</span><span class="openinfra-chevron">›</span>
        </button>
        <div class="openinfra-accordion-panel fade ${opened ? "show" : ""}">
          ${visibleOperations.map((operation) => `<button type="button" class="openinfra-sidebar-operation ${this.state.selected.id === operation.id ? "active" : ""}" data-operation-id="${this.escape(operation.id)}">${this.escape(operation.label)}</button>`).join("")}
        </div>
      </section>`;
    }).join("");
  }

  renderOperationPanel(operation, result) {
    const module = this.moduleForOperation(operation);
    const fields = [...(operation.query || []), ...(operation.body || [])];
    return `<div class="row g-4">
      <section class="col-12 col-xxl-8">
        <h2 class="h4">${this.escape(operation.label)}</h2>
        <p class="text-muted">${this.escape(module.description)}</p>
        <div class="alert alert-info" role="note">Formulaire métier typé : chaque champ correspond à une variable attendue par l’API OpenInfra. Aucun champ générique Attributs n’est demandé à l’opérateur.</div>
        <div class="row g-3 mb-3"><label class="col-md-4 form-label">Tenant<input id="openinfra-tenant" class="form-control" value="${this.escape(this.state.tenant)}" autocomplete="off"></label></div>
        <div class="row g-3">${fields.map((field) => this.renderField(field)).join("") || "<p>Aucun paramètre requis.</p>"}</div>
        <button class="btn btn-primary mt-3" type="button" id="openinfra-execute">Exécuter</button>
      </section>
      <aside class="col-12 col-xxl-4">
        <h3 class="h6 text-uppercase text-muted">Résultat</h3>
        <pre class="openinfra-result">${this.escape(result ? JSON.stringify(result, null, 2) : "Résultat en attente.")}</pre>
      </aside>
    </div>`;
  }

  renderField(field) {
    const required = field.required ? " required" : "";
    const requiredText = field.required ? " *" : "";
    const value = field.defaultValue || "";
    if (field.type === "select") {
      return `<label class="col-md-6 col-xl-4 form-label">${this.escape(field.label || field.name)}${requiredText}<select class="form-select" data-field="${this.escape(field.name)}"${required}><option value=""></option>${(field.options || []).map((option) => `<option value="${this.escape(option)}" ${value === option ? "selected" : ""}>${this.escape(option)}</option>`).join("")}</select></label>`;
    }
    if (field.type === "boolean") {
      return `<label class="col-md-6 col-xl-4 form-label">${this.escape(field.label || field.name)}<select class="form-select" data-field="${this.escape(field.name)}"><option value="false">Non</option><option value="true">Oui</option></select></label>`;
    }
    const inputType = field.type === "number" ? "number" : "text";
    return `<label class="col-md-6 col-xl-4 form-label">${this.escape(field.label || field.name)}${requiredText}<input class="form-control" type="${inputType}" data-field="${this.escape(field.name)}" value="${this.escape(value)}" placeholder="${this.escape(field.placeholder || "")}"${required}></label>`;
  }

  bindEvents() {
    document.getElementById("openinfra-execute")?.addEventListener("click", () => this.executeSelected());
    document.getElementById("openinfra-tenant")?.addEventListener("input", (event) => {
      this.state = { ...this.state, tenant: event.target.value };
    });
    for (const button of document.querySelectorAll("[data-module-id]")) {
      button.addEventListener("click", () => this.selectModule(button.dataset.moduleId));
    }
    for (const button of document.querySelectorAll("[data-accordion-id]")) {
      button.addEventListener("click", () => this.toggleAccordion(button.dataset.accordionId));
    }
    for (const button of document.querySelectorAll("[data-operation-id]")) {
      button.addEventListener("click", () => this.selectOperation(button.dataset.operationId));
    }
  }

  toggleAccordion(moduleId) {
    const opened = new Set(this.state.openedModules);
    if (opened.has(moduleId)) {
      opened.delete(moduleId);
    } else {
      opened.add(moduleId);
    }
    this.state = { ...this.state, openedModules: opened };
    this.render();
  }

  selectModule(moduleId) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) {
      return;
    }
    const opened = new Set(this.state.openedModules);
    if (module.id !== "overview") {
      opened.add(module.id);
    }
    this.state = { ...this.state, activeModuleId: module.id, selected: module.operations[0], openedModules: opened, result: null, error: null };
    this.render();
  }

  selectOperation(operationId) {
    for (const module of OPENINFRA_MODULES) {
      const operation = module.operations.find((item) => item.id === operationId);
      if (operation) {
        const opened = new Set(this.state.openedModules);
        if (module.id !== "overview") {
          opened.add(module.id);
        }
        this.state = { ...this.state, activeModuleId: module.id, selected: operation, openedModules: opened, result: null, error: null };
        this.render();
        return;
      }
    }
  }

  async executeSelected() {
    try {
      const payload = {};
      for (const input of document.querySelectorAll("[data-field]")) {
        payload[input.dataset.field] = input.value;
      }
      const data = await this.client().request(this.state.selected, payload);
      this.state = { ...this.state, result: data, error: null };
    } catch (error) {
      this.state = { ...this.state, error, result: null };
    }
    this.render();
  }

  moduleForOperation(operation) {
    return OPENINFRA_MODULES.find((module) => module.operations.some((item) => item.id === operation.id)) || OPENINFRA_MODULES[0];
  }

  metric(title, body) {
    return `<article class="col-md-6 col-xl-3"><div class="card h-100 openinfra-metric"><div class="card-body"><h2 class="h6 text-muted">${this.escape(title)}</h2><p class="openinfra-metric-value mb-0">${body}</p></div></div></article>`;
  }

  icon(name, className = "bi", width = 16, height = 16) {
    return `<svg class="${this.escape(className)}" width="${width}" height="${height}" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="${OPENINFRA_ICONS[name] || OPENINFRA_ICONS.grid}"></path></svg>`;
  }

  escape(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#039;");
  }
}

new OpenInfraDashboard(document.getElementById("openinfra-root")).start();
