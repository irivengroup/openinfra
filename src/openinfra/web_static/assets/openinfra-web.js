class OpenInfraApiClient {
  constructor(apiBaseUrl) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
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
}

class OpenInfraDashboard {
  constructor(root) {
    this.root = root;
    this.state = { config: null, version: null, ready: null, error: null };
  }

  async start() {
    try {
      const config = await this.fetchConfig();
      const client = new OpenInfraApiClient(config.apiBaseUrl);
      const [version, ready] = await Promise.all([
        client.getJson("/v1/version"),
        fetch("/ready", { credentials: "same-origin" }).then((response) => response.json())
      ]);
      this.state = { config, version, ready, error: null };
    } catch (error) {
      this.state = { config: this.state.config, version: null, ready: null, error };
    }
    this.render();
  }

  async fetchConfig() {
    const response = await fetch("/config.json", { credentials: "same-origin" });
    if (!response.ok) {
      throw new Error(`Configuration unavailable: ${response.status}`);
    }
    return response.json();
  }

  render() {
    const { config, version, ready, error } = this.state;
    this.root.innerHTML = `
      <nav class="navbar" aria-label="Navigation principale">
        <div class="navbar-brand">OpenInfra Web</div>
        <span class="badge">${this.escape(config?.edition || "runtime")}</span>
      </nav>
      <section class="container">
        <h1>Console d'exploitation OpenInfra</h1>
        <p>Interface web API-only : aucun accès direct PostgreSQL, aucun secret runtime exposé au navigateur.</p>
        ${error ? `<div class="alert alert-warning" role="alert">${this.escape(error.message)}</div>` : ""}
        ${ready?.ready === true ? `<div class="alert alert-success" role="status">Backend prêt.</div>` : ""}
        <div class="grid">
          ${this.card("Version", this.escape(version?.version || "indisponible"))}
          ${this.card("API", this.escape(config?.apiBaseUrl || "/api"))}
          ${this.card("Authentification", this.escape(config?.authMode || "standard"))}
          ${this.card("RBAC", "Permissions appliquées côté backend à chaque appel API.")}
        </div>
        <section class="card" aria-labelledby="parity-title">
          <h2 id="parity-title">Parcours opérationnels P08</h2>
          <div class="table-responsive">
            <table>
              <thead><tr><th>Domaine</th><th>API consommée</th><th>Objectif UI</th></tr></thead>
              <tbody>
                <tr><td>Source of Truth</td><td>/api/v1/sot/objects</td><td>Inventaire et consultation paginée</td></tr>
                <tr><td>IPAM</td><td>/api/v1/ipam/*</td><td>Réservations et capacité</td></tr>
                <tr><td>DCIM</td><td>/api/v1/dcim/*</td><td>Racks, salles, localisation</td></tr>
                <tr><td>Audit</td><td>/api/v1/audit/events</td><td>Traçabilité des permissions</td></tr>
              </tbody>
            </table>
          </div>
        </section>
        <button class="btn" type="button" id="refresh-openinfra">Rafraîchir</button>
      </section>
    `;
    const refresh = document.getElementById("refresh-openinfra");
    refresh?.addEventListener("click", () => this.start());
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
