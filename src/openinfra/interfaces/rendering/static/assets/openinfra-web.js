class OpenInfraApiClient {
  constructor(apiBaseUrl, tokenProvider, tenantProvider) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
    this.tokenProvider = tokenProvider;
    this.tenantProvider = tenantProvider;
  }

  async request(operation, payload) {
    const path = this.interpolatePath(operation.path, payload);
    const query = this.buildQuery(operation.query || [], payload);
    const headers = { Accept: "application/json" };
    const token = this.tokenProvider();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
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
      throw new Error(JSON.stringify(data));
    }
    return data;
  }

  async getJson(path) {
    const response = await fetch(`${this.apiBaseUrl}${path}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" }
    });
    if (!response.ok) {
      throw new Error(`API ${path} returned ${response.status}`);
    }
    return response.json();
  }

  interpolatePath(path, payload) {
    return path.replace(/\{([^}]+)\}/g, (_, key) => encodeURIComponent(payload[key] || ""));
  }

  buildQuery(fields, payload) {
    const query = new URLSearchParams();
    for (const field of fields) {
      const value = payload[field.name];
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
      if (raw === undefined || raw === null || String(raw).trim() === "") {
        if (field.required) {
          throw new Error(`Champ obligatoire manquant: ${field.name}`);
        }
        continue;
      }
      body[field.name] = field.type === "json" ? JSON.parse(raw) : raw;
    }
    const tenant = this.tenantProvider();
    if (tenant && operation.body && !Object.prototype.hasOwnProperty.call(body, "tenant_id")) {
      body.tenant_id = tenant;
    }
    return body;
  }
}

const OPENINFRA_OPERATIONS = [
  {
    domain: "Ressources Inventory",
    description: "Inventaire canonique des ressources, relations, versions et gouvernance RI.",
    operations: [
      { id: "ri-list", label: "Lister les objets RI", method: "GET", path: "/v1/ri/objects", query: [{ name: "kind" }, { name: "tag" }, { name: "limit" }] },
      { id: "ri-upsert", label: "Créer ou mettre à jour un objet RI", method: "POST", path: "/v1/ri/objects", body: [
        { name: "actor", required: true }, { name: "key", required: true }, { name: "kind", required: true },
        { name: "display_name", required: true }, { name: "attributes", type: "json" }, { name: "tags", type: "json" }, { name: "source", required: true }
      ] },
      { id: "ri-relations", label: "Lister les relations RI", method: "GET", path: "/v1/ri/relations", query: [{ name: "source_key" }, { name: "target_key" }, { name: "relation_type" }, { name: "limit" }] },
      { id: "ri-governance", label: "Évaluer une règle de gouvernance RI", method: "POST", path: "/v1/ri/governance/evaluate", body: [
        { name: "object_kind", required: true }, { name: "incoming_source", required: true },
        { name: "existing_attributes", type: "json" }, { name: "incoming_attributes", type: "json" }
      ] }
    ]
  },
  {
    domain: "IPAM / DDI",
    description: "Préfixes, VLANs, VRF, réservations, conflits, capacité et assistants de réservation.",
    operations: [
      { id: "ipam-search", label: "Rechercher IPAM", method: "GET", path: "/v1/ipam/search", query: [{ name: "query" }, { name: "limit" }] },
      { id: "ipam-capacity", label: "Capacité IPAM", method: "GET", path: "/v1/ipam/capacity", query: [{ name: "prefix" }] },
      { id: "ipam-allocate", label: "Allouer une IP", method: "POST", path: "/v1/ipam/allocate", body: [
        { name: "actor", required: true }, { name: "prefix", required: true }, { name: "purpose", required: true }
      ] },
      { id: "ipam-conflicts", label: "Détecter les conflits", method: "GET", path: "/v1/ipam/conflicts", query: [{ name: "limit" }] }
    ]
  },
  {
    domain: "DCIM",
    description: "Sites, salles, zones, racks, ports, câbles, énergie, refroidissement et localisation terrain.",
    operations: [
      { id: "dcim-rack-capacity", label: "Capacité rack", method: "GET", path: "/v1/dcim/rack-capacity", query: [{ name: "site" }, { name: "building" }, { name: "room" }, { name: "rack" }] },
      { id: "dcim-room-plan", label: "Plan de salle", method: "GET", path: "/v1/dcim/room-plan", query: [{ name: "site" }, { name: "building" }, { name: "room" }] },
      { id: "dcim-cable-trace", label: "Tracer un câble", method: "GET", path: "/v1/dcim/cable-trace", query: [{ name: "cable_id" }] }
    ]
  },
  {
    domain: "Discovery",
    description: "Collecte locale backend pour Lite/Pro ; agents proxy collectors uniquement Enterprise en topologie étoile.",
    operations: [
      { id: "collectors-list", label: "Lister les agents proxy Enterprise", method: "GET", path: "/v1/discovery/collectors", query: [{ name: "scope" }, { name: "limit" }] },
      { id: "collectors-register", label: "Enregistrer un agent proxy Enterprise", method: "POST", path: "/v1/discovery/collectors", body: [
        { name: "actor", required: true }, { name: "name", required: true }, { name: "kind", required: true },
        { name: "certificate_fingerprint", required: true }, { name: "scopes", type: "json", required: true }, { name: "endpoint", required: true }
      ] },
      { id: "job-authorize", label: "Autoriser un job collector", method: "POST", path: "/v1/discovery/jobs/authorize", body: [
        { name: "collector_id", required: true }, { name: "certificate_fingerprint", required: true }, { name: "scope", required: true }, { name: "job_type", required: true }
      ] }
    ]
  },
  {
    domain: "Identité / RBAC / Sécurité",
    description: "Utilisateurs, groupes, rôles, tokens, politiques d’accès et permissions effectives.",
    operations: [
      { id: "tokens-list", label: "Lister les tokens", method: "GET", path: "/v1/security/tokens", query: [{ name: "limit" }, { name: "include_inactive" }] },
      { id: "effective-identity", label: "Identité effective", method: "GET", path: "/v1/identity/effective", query: [{ name: "subject" }] },
      { id: "access-rules", label: "Lister les politiques d’accès", method: "GET", path: "/v1/access/rules", query: [{ name: "limit" }, { name: "include_inactive" }] }
    ]
  },
  {
    domain: "Audit / Import / Export / Runtime",
    description: "Traçabilité, intégrité, imports atomiques, exports asynchrones, santé et documentation API.",
    operations: [
      { id: "audit-events", label: "Lister les événements d’audit", method: "GET", path: "/v1/audit/events", query: [{ name: "action" }, { name: "target_type" }, { name: "limit" }] },
      { id: "audit-integrity", label: "Vérifier l’intégrité audit", method: "GET", path: "/v1/audit/integrity", query: [{ name: "limit" }] },
      { id: "exports-jobs", label: "Lister les exports", method: "GET", path: "/v1/exports/jobs", query: [{ name: "limit" }] },
      { id: "schema", label: "Statut schéma DB", method: "GET", path: "/v1/database/schema", query: [] }
    ]
  }
];

class OpenInfraDashboard {
  constructor(root) {
    this.root = root;
    this.state = { config: null, version: null, ready: null, selected: OPENINFRA_OPERATIONS[0].operations[0], result: null, error: null };
  }

  async start() {
    try {
      const config = await this.fetchConfig();
      const client = this.client(config);
      const [version, ready] = await Promise.all([
        client.getJson("/v1/version"),
        fetch("/ready", { credentials: "same-origin" }).then((response) => response.json())
      ]);
      this.state = { ...this.state, config, version, ready, error: null };
    } catch (error) {
      this.state = { ...this.state, error };
    }
    this.render();
  }

  client(config) {
    return new OpenInfraApiClient(
      config.apiBaseUrl,
      () => document.getElementById("openinfra-token")?.value || "",
      () => document.getElementById("openinfra-tenant")?.value || "default"
    );
  }

  async fetchConfig() {
    const response = await fetch("/config.json", { credentials: "same-origin" });
    if (!response.ok) {
      throw new Error(`Configuration unavailable: ${response.status}`);
    }
    return response.json();
  }

  render() {
    const { config, version, ready, error, selected, result } = this.state;
    this.root.innerHTML = `
      <nav class="navbar" aria-label="Navigation principale">
        <div class="navbar-brand">OpenInfra Web</div>
        <span class="badge">${this.escape(config?.edition || "runtime")}</span>
      </nav>
      <section class="container">
        <h1>Dashboard de pilotage OpenInfra</h1>
        <p>Portail web API-only aligné sur les domaines CLI : RI, IPAM, DCIM, Discovery, sécurité, audit, import/export et runtime.</p>
        ${error ? `<div class="alert alert-warning" role="alert">${this.escape(error.message)}</div>` : ""}
        ${ready?.ready === true ? `<div class="alert alert-success" role="status">Backend prêt.</div>` : ""}
        <div class="grid">
          ${this.card("Version", this.escape(version?.version || "indisponible"))}
          ${this.card("API", this.escape(config?.apiBaseUrl || "/api"))}
          ${this.card("Authentification", this.escape(config?.authMode || "standard"))}
          ${this.card("RBAC", "Permissions appliquées côté backend à chaque appel API.")}
        </div>
        <section class="card" aria-labelledby="control-title">
          <h2 id="control-title">Centre de contrôle opérationnel</h2>
          <div class="form-grid">
            <label>Tenant<input id="openinfra-tenant" value="default" autocomplete="off"></label>
            <label>Token API<input id="openinfra-token" type="password" autocomplete="off" placeholder="Bearer token"></label>
          </div>
          <div class="dashboard-layout">
            <aside class="operation-list" aria-label="Domaines OpenInfra">${this.renderOperationList()}</aside>
            <section class="operation-panel" aria-live="polite">${this.renderOperationPanel(selected, result)}</section>
          </div>
        </section>
        <button class="btn" type="button" id="refresh-openinfra">Rafraîchir</button>
      </section>
    `;
    document.getElementById("refresh-openinfra")?.addEventListener("click", () => this.start());
    for (const button of document.querySelectorAll("[data-operation-id]")) {
      button.addEventListener("click", () => this.selectOperation(button.dataset.operationId));
    }
    document.getElementById("openinfra-execute")?.addEventListener("click", () => this.executeSelected());
  }

  renderOperationList() {
    return OPENINFRA_OPERATIONS.map((module) => `
      <section>
        <h3>${this.escape(module.domain)}</h3>
        <p>${this.escape(module.description)}</p>
        ${module.operations.map((operation) => `<button class="operation" type="button" data-operation-id="${this.escape(operation.id)}">${this.escape(operation.label)}</button>`).join("")}
      </section>
    `).join("");
  }

  renderOperationPanel(operation, result) {
    const fields = [...(operation.query || []), ...(operation.body || [])];
    const inputs = fields.map((field) => `
      <label>${this.escape(field.name)}${field.required ? " *" : ""}
        <textarea data-field="${this.escape(field.name)}" rows="${field.type === "json" ? 4 : 1}" placeholder="${field.type === "json" ? "{} ou []" : ""}"></textarea>
      </label>
    `).join("");
    return `
      <h3>${this.escape(operation.label)}</h3>
      <p><code>${this.escape(operation.method)} ${this.escape(operation.path)}</code></p>
      <div class="form-grid">${inputs || "<p>Aucun paramètre requis.</p>"}</div>
      <button class="btn" type="button" id="openinfra-execute">Exécuter via API</button>
      <pre class="result">${this.escape(result ? JSON.stringify(result, null, 2) : "Résultat en attente.")}</pre>
    `;
  }

  selectOperation(operationId) {
    const selected = OPENINFRA_OPERATIONS.flatMap((module) => module.operations).find((operation) => operation.id === operationId);
    if (selected) {
      this.state = { ...this.state, selected, result: null, error: null };
      this.render();
    }
  }

  async executeSelected() {
    try {
      const payload = {};
      for (const input of document.querySelectorAll("[data-field]")) {
        payload[input.dataset.field] = input.value;
      }
      const data = await this.client(this.state.config).request(this.state.selected, payload);
      this.state = { ...this.state, result: data, error: null };
    } catch (error) {
      this.state = { ...this.state, error, result: null };
    }
    this.render();
  }

  card(title, body) {
    return `<article class="card"><h3>${this.escape(title)}</h3><p>${body}</p></article>`;
  }

  escape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}

new OpenInfraDashboard(document.getElementById("openinfra-root")).start();
