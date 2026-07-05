import 'bootstrap/dist/css/bootstrap.min.css';
import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';

const OPERATIONS = [
  ['Ressources Inventory', 'Inventaire canonique RI', [
    ['ri-list', 'GET', '/v1/ri/objects', 'Lister les objets RI'],
    ['ri-upsert', 'POST', '/v1/ri/objects', 'Créer ou mettre à jour un objet RI'],
    ['ri-relations', 'GET', '/v1/ri/relations', 'Lister les relations RI'],
    ['ri-governance', 'POST', '/v1/ri/governance/evaluate', 'Évaluer la gouvernance RI'],
  ]],
  ['IPAM / DDI', 'Préfixes, VLANs, VRF, réservations et conflits', [
    ['ipam-search', 'GET', '/v1/ipam/search', 'Rechercher IPAM'],
    ['ipam-capacity', 'GET', '/v1/ipam/capacity', 'Capacité IPAM'],
    ['ipam-allocate', 'POST', '/v1/ipam/allocate', 'Allouer une IP'],
  ]],
  ['DCIM', 'Salles, racks, ports, câbles, énergie et localisation', [
    ['dcim-rack', 'GET', '/v1/dcim/rack-capacity', 'Capacité rack'],
    ['dcim-room', 'GET', '/v1/dcim/room-plan', 'Plan de salle'],
    ['dcim-cable', 'GET', '/v1/dcim/cable-trace', 'Tracer un câble'],
  ]],
  ['Discovery', 'Backends collecteurs pour Lite/Pro ; agents proxy collectors uniquement Enterprise', [
    ['collectors-list', 'GET', '/v1/discovery/collectors', 'Lister les agents proxy Enterprise'],
    ['collector-register', 'POST', '/v1/discovery/collectors', 'Enregistrer un agent proxy'],
    ['job-authorize', 'POST', '/v1/discovery/jobs/authorize', 'Autoriser un job collector'],
  ]],
  ['Sécurité / RBAC / Audit', 'Tokens, identité, politiques, audit et runtime', [
    ['tokens', 'GET', '/v1/security/tokens', 'Lister les tokens'],
    ['identity', 'GET', '/v1/identity/effective', 'Identité effective'],
    ['audit', 'GET', '/v1/audit/events', 'Événements audit'],
    ['schema', 'GET', '/v1/database/schema', 'Statut schéma DB'],
  ]],
];

class OpenInfraApiClient {
  constructor(apiBaseUrl) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '');
  }

  async getJson(path) {
    const response = await fetch(`${this.apiBaseUrl}${path}`, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`API ${path} returned ${response.status}`);
    }
    return response.json();
  }

  async call(operation, token, tenant, payload) {
    const headers = { Accept: 'application/json' };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    if (operation.method !== 'GET') {
      headers['Content-Type'] = 'application/json';
    }
    const query = operation.method === 'GET' ? `?tenant_id=${encodeURIComponent(tenant)}` : '';
    const body = operation.method === 'GET' ? undefined : JSON.stringify({ tenant_id: tenant, ...payload });
    const response = await fetch(`${this.apiBaseUrl}${operation.path}${query}`, {
      method: operation.method,
      credentials: 'same-origin',
      headers,
      body,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }
    return data;
  }
}

function Dashboard() {
  const [state, setState] = useState({ config: null, version: null, ready: null, error: null, result: null });
  const [tenant, setTenant] = useState('default');
  const [token, setToken] = useState('');
  const [payload, setPayload] = useState('{}');
  const operations = useMemo(() => OPERATIONS.flatMap(([domain, description, items]) => items.map(([id, method, path, label]) => ({ id, domain, description, method, path, label }))), []);
  const [selected, setSelected] = useState(operations[0]);

  async function refresh() {
    try {
      const configResponse = await fetch('/config.json', { credentials: 'same-origin' });
      if (!configResponse.ok) {
        throw new Error(`Configuration unavailable: ${configResponse.status}`);
      }
      const config = await configResponse.json();
      const client = new OpenInfraApiClient(config.apiBaseUrl);
      const [version, ready] = await Promise.all([
        client.getJson('/v1/version'),
        fetch('/ready', { credentials: 'same-origin' }).then((response) => response.json()),
      ]);
      setState((previous) => ({ ...previous, config, version, ready, error: null }));
    } catch (error) {
      setState((previous) => ({ ...previous, error }));
    }
  }

  async function execute() {
    try {
      const jsonPayload = payload.trim() ? JSON.parse(payload) : {};
      const client = new OpenInfraApiClient(state.config.apiBaseUrl);
      const result = await client.call(selected, token, tenant, jsonPayload);
      setState((previous) => ({ ...previous, result, error: null }));
    } catch (error) {
      setState((previous) => ({ ...previous, result: null, error }));
    }
  }

  useEffect(() => { refresh(); }, []);

  return (
    <>
      <nav className="navbar navbar-dark bg-dark px-4">
        <span className="navbar-brand mb-0 h1">OpenInfra Web</span>
        <span className="badge text-bg-primary">{state.config?.edition ?? 'runtime'}</span>
      </nav>
      <section className="container py-4">
        <h1>Dashboard de pilotage OpenInfra</h1>
        <p className="lead">Portail web API-only aligné sur les domaines CLI : RI, IPAM, DCIM, Discovery, sécurité, audit, import/export et runtime.</p>
        {state.error && <div className="alert alert-warning">{state.error.message}</div>}
        {state.ready?.ready === true && <div className="alert alert-success">Backend prêt.</div>}
        <div className="row g-3">
          <Metric title="Version" value={state.version?.version ?? 'indisponible'} />
          <Metric title="API" value={state.config?.apiBaseUrl ?? '/api'} />
          <Metric title="Authentification" value={state.config?.authMode ?? 'standard'} />
          <Metric title="RBAC" value="Appliqué côté backend" />
        </div>
        <section className="card mt-4">
          <div className="card-body">
            <h2 className="h4">Centre de contrôle opérationnel</h2>
            <div className="row g-3">
              <label className="col-md-4 form-label">Tenant<input className="form-control" value={tenant} onChange={(event) => setTenant(event.target.value)} /></label>
              <label className="col-md-8 form-label">Token API<input className="form-control" type="password" value={token} onChange={(event) => setToken(event.target.value)} /></label>
            </div>
            <div className="row g-3 mt-1">
              <aside className="col-lg-4">
                {OPERATIONS.map(([domain, description, items]) => <section key={domain} className="mb-3"><h3 className="h5">{domain}</h3><p>{description}</p>{items.map(([id, method, path, label]) => <button className="btn btn-outline-primary d-block w-100 mb-2 text-start" type="button" key={id} onClick={() => setSelected({ id, domain, description, method, path, label })}>{label}</button>)}</section>)}
              </aside>
              <section className="col-lg-8">
                <h3 className="h5">{selected.label}</h3>
                <p><code>{selected.method} {selected.path}</code></p>
                <label className="form-label">Payload JSON<textarea className="form-control" rows="8" value={payload} onChange={(event) => setPayload(event.target.value)} /></label>
                <button className="btn btn-primary mt-2" type="button" onClick={execute}>Exécuter via API</button>
                <pre className="bg-dark text-light rounded p-3 mt-3">{JSON.stringify(state.result ?? 'Résultat en attente.', null, 2)}</pre>
              </section>
            </div>
          </div>
        </section>
        <button className="btn btn-primary mt-3" type="button" onClick={refresh}>Rafraîchir</button>
      </section>
    </>
  );
}

function Metric({ title, value }) {
  return <article className="col-md-3"><div className="card h-100"><div className="card-body"><h2 className="h5">{title}</h2><p>{value}</p></div></div></article>;
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
