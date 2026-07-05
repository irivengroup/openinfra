import 'bootstrap/dist/css/bootstrap.min.css';
import './openinfra-theme.css';
import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';

const ICONS = {
  home: 'M8 3.293l6 6V15a1 1 0 0 1-1 1h-3v-4H6v4H3a1 1 0 0 1-1-1V9.293l6-6zm5-.793V6l-2-2V2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5z',
  speedometer2: 'M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4zM3.732 5.732a.5.5 0 0 1 .707 0l.915.914a.5.5 0 1 1-.708.708l-.914-.915a.5.5 0 0 1 0-.707zM2 10a.5.5 0 0 1 .5-.5h1.586a.5.5 0 0 1 0 1H2.5A.5.5 0 0 1 2 10zm9.5 0a.5.5 0 0 1 .5-.5h1.5a.5.5 0 0 1 0 1H12a.5.5 0 0 1-.5-.5zm.754-4.246a.5.5 0 0 1 0 .707l-.94.94a.5.5 0 1 1-.707-.708l.94-.94a.5.5 0 0 1 .707 0zM9.67 11.71a2 2 0 1 1-3.34-2.19l3.95-3.95a.5.5 0 0 1 .8.6l-1.41 5.54zM8 1a7 7 0 0 0-7 7c0 1.71.61 3.28 1.63 4.5a.5.5 0 0 0 .38.17h9.98a.5.5 0 0 0 .38-.17A6.97 6.97 0 0 0 15 8a7 7 0 0 0-7-7z',
  table: 'M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm15 2h-4v3h4V4zm0 4h-4v3h4V8zm0 4h-4v3h3a1 1 0 0 0 1-1v-2zm-5 3v-3H6v3h4zm-5 0v-3H1v2a1 1 0 0 0 1 1h3zm-4-4h4V8H1v3zm0-4h4V4H1v3zm5-3v3h4V4H6zm4 4H6v3h4V8z',
  grid: 'M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z',
  people: 'M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm-1.559 4.27A4.985 4.985 0 0 0 8 10c-2.67 0-4.9 2.1-4.99 4.71A1 1 0 0 0 4 15h8a1 1 0 0 0 .99-1.29 5.002 5.002 0 0 0-3.549-3.44zM13.5 7a2.5 2.5 0 0 1-1.18 2.12 6.01 6.01 0 0 1 2.2 2.56A1 1 0 0 0 15.5 10.5 3.5 3.5 0 0 0 12 7h1.5z',
  shield: 'M5.338 1.59a61.44 61.44 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188A10.7 10.7 0 0 0 8 15a10.7 10.7 0 0 0 3.574-2.976c1.527-1.998 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39 61.44 61.44 0 0 0-2.837-.856C9.552 1.29 8.531 1.067 8 1.067c-.531 0-1.552.223-2.662.523z',
  activity: 'M6.5 12a.5.5 0 0 1-.447-.276L3.382 6.382 1.894 9.36A.5.5 0 0 1 1.447 9.636H.5a.5.5 0 0 1 0-1h.638l1.915-3.83a.5.5 0 0 1 .894 0L6.5 9.91l2.553-5.105a.5.5 0 0 1 .894 0l1.915 3.83h3.638a.5.5 0 0 1 0 1h-3.947a.5.5 0 0 1-.447-.276L9.5 6.382l-2.553 5.342A.5.5 0 0 1 6.5 12z',
  search: 'M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.099zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z',
};

const MODULES = [
  {
    id: 'overview',
    label: 'Dashboard',
    icon: 'speedometer2',
    description: 'Vue de synthèse, readiness backend, version, sécurité et opérations rapides.',
    operations: [
      { id: 'version', label: 'Version runtime', method: 'GET', path: '/v1/version', query: [] },
      { id: 'schema', label: 'Statut schéma DB', method: 'GET', path: '/v1/database/schema', query: [] },
    ],
  },
  {
    id: 'ri',
    label: 'RI',
    icon: 'table',
    description: 'Ressources Inventory : inventaire canonique, relations, versions, gouvernance et certification.',
    operations: [
      { id: 'ri-list', label: 'Lister les objets RI', method: 'GET', path: '/v1/ri/objects', query: [{ name: 'kind' }, { name: 'tag' }, { name: 'limit' }] },
      { id: 'ri-upsert', label: 'Créer / mettre à jour un objet RI', method: 'POST', path: '/v1/ri/objects', body: [{ name: 'actor', required: true }, { name: 'key', required: true }, { name: 'kind', required: true }, { name: 'display_name', required: true }, { name: 'attributes', type: 'json' }, { name: 'tags', type: 'json' }, { name: 'source', required: true }] },
      { id: 'ri-relations', label: 'Lister les relations RI', method: 'GET', path: '/v1/ri/relations', query: [{ name: 'source_key' }, { name: 'target_key' }, { name: 'relation_type' }, { name: 'limit' }] },
      { id: 'ri-quality-object', label: 'Évaluer la qualité d’un objet RI', method: 'GET', path: '/v1/ri/quality/object', query: [{ name: 'key' }] },
      { id: 'ri-quality-summary', label: 'Synthèse qualité / certification RI', method: 'GET', path: '/v1/ri/quality/summary', query: [{ name: 'kind' }, { name: 'tag' }, { name: 'limit' }] },
      { id: 'ri-governance', label: 'Évaluer une règle de gouvernance RI', method: 'POST', path: '/v1/ri/governance/evaluate', body: [{ name: 'object_kind', required: true }, { name: 'incoming_source', required: true }, { name: 'existing_attributes', type: 'json' }, { name: 'incoming_attributes', type: 'json' }] },
    ],
  },
  {
    id: 'ipam',
    label: 'IPAM',
    icon: 'grid',
    description: 'Préfixes, VLANs, VRF, réservations, conflits, capacité et allocations.',
    operations: [
      { id: 'ipam-search', label: 'Rechercher IPAM', method: 'GET', path: '/v1/ipam/search', query: [{ name: 'query' }, { name: 'limit' }] },
      { id: 'ipam-capacity', label: 'Capacité IPAM', method: 'GET', path: '/v1/ipam/capacity', query: [{ name: 'prefix' }] },
      { id: 'ipam-allocate', label: 'Allouer une IP', method: 'POST', path: '/v1/ipam/allocate', body: [{ name: 'actor', required: true }, { name: 'prefix', required: true }, { name: 'purpose', required: true }] },
      { id: 'ipam-conflicts', label: 'Détecter les conflits', method: 'GET', path: '/v1/ipam/conflicts', query: [{ name: 'limit' }] },
    ],
  },
  {
    id: 'dcim',
    label: 'DCIM',
    icon: 'home',
    description: 'Sites, salles, zones, racks, ports, câbles, énergie et localisation terrain.',
    operations: [
      { id: 'dcim-rack-capacity', label: 'Capacité rack', method: 'GET', path: '/v1/dcim/rack-capacity', query: [{ name: 'site' }, { name: 'building' }, { name: 'room' }, { name: 'rack' }] },
      { id: 'dcim-room-plan', label: 'Plan de salle', method: 'GET', path: '/v1/dcim/room-plan', query: [{ name: 'site' }, { name: 'building' }, { name: 'room' }] },
      { id: 'dcim-cable-trace', label: 'Tracer un câble', method: 'GET', path: '/v1/dcim/cable-trace', query: [{ name: 'cable_id' }] },
    ],
  },
  {
    id: 'discovery',
    label: 'Discovery',
    icon: 'activity',
    description: 'Collecte locale backend Lite/Pro ; agents proxy collectors Enterprise uniquement en topologie étoile.',
    operations: [
      { id: 'collectors-list', label: 'Lister les agents proxy Enterprise', method: 'GET', path: '/v1/discovery/collectors', query: [{ name: 'scope' }, { name: 'limit' }] },
      { id: 'collectors-register', label: 'Enregistrer un agent proxy Enterprise', method: 'POST', path: '/v1/discovery/collectors', body: [{ name: 'actor', required: true }, { name: 'name', required: true }, { name: 'kind', required: true }, { name: 'certificate_fingerprint', required: true }, { name: 'scopes', type: 'json', required: true }, { name: 'endpoint', required: true }] },
      { id: 'job-authorize', label: 'Autoriser un job collector', method: 'POST', path: '/v1/discovery/jobs/authorize', body: [{ name: 'collector_id', required: true }, { name: 'certificate_fingerprint', required: true }, { name: 'scope', required: true }, { name: 'job_type', required: true }] },
    ],
  },
  {
    id: 'security',
    label: 'Sécurité',
    icon: 'shield',
    description: 'Identité, RBAC, tokens, politiques d’accès, audit et intégrité.',
    operations: [
      { id: 'tokens-list', label: 'Lister les tokens', method: 'GET', path: '/v1/security/tokens', query: [{ name: 'limit' }, { name: 'include_inactive' }] },
      { id: 'effective-identity', label: 'Identité effective', method: 'GET', path: '/v1/identity/effective', query: [{ name: 'subject' }] },
      { id: 'access-rules', label: 'Lister les politiques d’accès', method: 'GET', path: '/v1/access/rules', query: [{ name: 'limit' }, { name: 'include_inactive' }] },
      { id: 'audit-events', label: 'Lister les événements d’audit', method: 'GET', path: '/v1/audit/events', query: [{ name: 'action' }, { name: 'target_type' }, { name: 'limit' }] },
      { id: 'audit-integrity', label: 'Vérifier l’intégrité audit', method: 'GET', path: '/v1/audit/integrity', query: [{ name: 'limit' }] },
    ],
  },
];

function Icon({ name, className = 'bi' }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d={ICONS[name] || ICONS.grid} />
    </svg>
  );
}

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
    const path = operation.path.replace(/\{([^}]+)\}/g, (_, key) => encodeURIComponent(payload[key] || ''));
    const query = new URLSearchParams();
    for (const field of operation.query || []) {
      const value = payload[field.name];
      if (value !== undefined && value !== null && String(value).trim() !== '') {
        query.set(field.name, String(value));
      }
    }
    if (tenant && !query.has('tenant_id')) {
      query.set('tenant_id', tenant);
    }
    const headers = { Accept: 'application/json' };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    let body;
    if (operation.method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(buildBody(operation, payload, tenant));
    }
    const response = await fetch(`${this.apiBaseUrl}${path}${query.toString() ? `?${query.toString()}` : ''}`, {
      method: operation.method,
      credentials: 'same-origin',
      headers,
      body,
    });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }
    return data;
  }
}

function buildBody(operation, payload, tenant) {
  const body = {};
  for (const field of operation.body || []) {
    const raw = payload[field.name];
    if (raw === undefined || raw === null || String(raw).trim() === '') {
      if (field.required) {
        throw new Error(`Champ obligatoire manquant: ${field.name}`);
      }
      continue;
    }
    body[field.name] = field.type === 'json' ? JSON.parse(raw) : raw;
  }
  if (tenant && operation.body && !Object.prototype.hasOwnProperty.call(body, 'tenant_id')) {
    body.tenant_id = tenant;
  }
  return body;
}

function Dashboard() {
  const operations = useMemo(() => MODULES.flatMap((module) => module.operations.map((operation) => ({ ...operation, module }))), []);
  const [state, setState] = useState({ config: null, version: null, ready: null, error: null, result: null });
  const [selected, setSelected] = useState(operations[0]);
  const [activeModuleId, setActiveModuleId] = useState('overview');
  const [tenant, setTenant] = useState('default');
  const [token, setToken] = useState('');
  const [fields, setFields] = useState({});
  const [filter, setFilter] = useState('');

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
      const client = new OpenInfraApiClient(state.config.apiBaseUrl);
      const result = await client.call(selected, token, tenant, fields);
      setState((previous) => ({ ...previous, result, error: null }));
    } catch (error) {
      setState((previous) => ({ ...previous, result: null, error }));
    }
  }

  function selectModule(module) {
    setActiveModuleId(module.id);
    setSelected({ ...module.operations[0], module });
    setFields({});
    setState((previous) => ({ ...previous, result: null }));
  }

  function selectOperation(operation, module) {
    setActiveModuleId(module.id);
    setSelected({ ...operation, module });
    setFields({});
    setState((previous) => ({ ...previous, result: null }));
  }

  const filteredModules = MODULES.map((module) => ({
    ...module,
    operations: module.operations.filter((operation) => `${module.label} ${operation.label} ${operation.path}`.toLowerCase().includes(filter.toLowerCase())),
  })).filter((module) => module.operations.length > 0 || module.label.toLowerCase().includes(filter.toLowerCase()));

  useEffect(() => { refresh(); }, []);

  return (
    <div className="openinfra-shell">
      <header>
        <div className="px-3 py-2 bg-dark text-white openinfra-top-header">
          <div className="container-fluid">
            <div className="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start">
              <a href="/" className="d-flex align-items-center my-2 my-lg-0 me-lg-auto text-white text-decoration-none" aria-label="OpenInfra accueil">
                <span className="openinfra-brand-mark me-2">OI</span>
                <span className="fs-5 fw-semibold">OpenInfra</span>
              </a>
              <ul className="nav col-12 col-lg-auto my-2 justify-content-center my-md-0 text-small">
                {MODULES.slice(0, 6).map((module) => (
                  <li key={module.id}>
                    <button type="button" className={`nav-link border-0 bg-transparent ${activeModuleId === module.id ? 'text-secondary' : 'text-white'}`} onClick={() => selectModule(module)}>
                      <Icon name={module.icon} className="bi d-block mx-auto mb-1 openinfra-top-icon" />
                      {module.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
        <div className="px-3 py-2 border-bottom mb-3">
          <div className="container-fluid d-flex flex-wrap justify-content-center">
            <form className="col-12 col-lg-auto mb-2 mb-lg-0 me-lg-auto" role="search" onSubmit={(event) => event.preventDefault()}>
              <input type="search" className="form-control openinfra-search" placeholder="Search OpenInfra operations..." aria-label="Search" value={filter} onChange={(event) => setFilter(event.target.value)} />
            </form>
            <div className="text-end">
              <button type="button" className="btn btn-light text-dark me-2" onClick={() => document.getElementById('openinfra-token')?.focus()}>Login</button>
              <button type="button" className="btn btn-primary" onClick={() => selectModule(MODULES.find((module) => module.id === 'security'))}>Sign-up</button>
            </div>
          </div>
        </div>
      </header>
      <div className="container-fluid">
        <div className="row">
          <nav className="col-lg-3 col-xl-2 openinfra-sidebar" aria-label="Sidebar navigation">
            <div className="openinfra-sidebar-heading">Composantes</div>
            <ul className="nav flex-column">
              {MODULES.map((module) => (
                <li className="nav-item" key={module.id}>
                  <button type="button" className={`nav-link w-100 text-start ${activeModuleId === module.id ? 'active' : ''}`} onClick={() => selectModule(module)}>
                    <Icon name={module.icon} />
                    {module.label}
                  </button>
                </li>
              ))}
            </ul>
            <div className="openinfra-sidebar-heading">État runtime</div>
            <div className="px-2 small text-muted">
              <p><span className={`openinfra-status-dot ${state.ready?.ready === true ? 'ready' : 'warning'}`} />Backend {state.ready?.ready === true ? 'prêt' : 'à vérifier'}</p>
              <p>API : <code>{state.config?.apiBaseUrl ?? '/api'}</code></p>
            </div>
          </nav>
          <main className="col-lg-9 col-xl-10 ms-sm-auto openinfra-main">
            <div className="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-2 mb-3 openinfra-titlebar">
              <div>
                <h1 className="h2">Dashboard de pilotage OpenInfra</h1>
                <p className="text-muted mb-0">Portail API-only aligné sur les domaines CLI : RI, IPAM, DCIM, Discovery, Sécurité/RBAC, Audit et Runtime.</p>
              </div>
              <div className="btn-toolbar mb-2 mb-md-0">
                <span className="badge text-bg-primary me-2">{state.config?.edition ?? 'runtime'}</span>
                <span className="badge text-bg-secondary">{state.config?.authMode ?? 'standard'}</span>
              </div>
            </div>
            {state.error && <div className="alert alert-warning" role="alert">{state.error.message}</div>}
            {state.ready?.ready === true && <div className="alert alert-success" role="status">Backend prêt.</div>}
            <div className="row g-3 mb-4">
              <Metric title="Version" value={state.version?.version ?? 'indisponible'} />
              <Metric title="API" value={state.config?.apiBaseUrl ?? '/api'} />
              <Metric title="RBAC" value="Backend enforced" />
              <Metric title="Modules" value={`${operations.length} opérations`} />
            </div>
            <section className="card openinfra-operation-card">
              <div className="card-body">
                <div className="row g-4">
                  <section className="col-xl-4">
                    <h2 className="h5">Opérations</h2>
                    <p className="text-muted">Chaque action du dashboard appelle l’API backend, sans accès direct aux secrets ni à PostgreSQL.</p>
                    <div className="openinfra-operation-list list-group">
                      {filteredModules.map((module) => (
                        <div className="mb-3" key={module.id}>
                          <h3 className="h6 text-uppercase text-muted">{module.label}</h3>
                          {module.operations.map((operation) => (
                            <button type="button" className={`list-group-item list-group-item-action openinfra-operation ${selected.id === operation.id ? 'active' : ''}`} key={operation.id} onClick={() => selectOperation(operation, module)}>
                              <span className="badge text-bg-light text-dark openinfra-method me-2">{operation.method}</span>
                              {operation.label}
                            </button>
                          ))}
                        </div>
                      ))}
                    </div>
                  </section>
                  <section className="col-xl-8">
                    <h2 className="h5">{selected.label}</h2>
                    <p className="text-muted">{selected.module.description}</p>
                    <p><code>{selected.method} {selected.path}</code></p>
                    <div className="row g-3 mb-3">
                      <label className="col-md-4 form-label">Tenant<input className="form-control" value={tenant} onChange={(event) => setTenant(event.target.value)} /></label>
                      <label className="col-md-8 form-label">Token API<input className="form-control" type="password" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" /></label>
                    </div>
                    <div className="row g-3">
                      {[...(selected.query || []), ...(selected.body || [])].map((field) => (
                        <label className="col-md-6 form-label" key={field.name}>{field.name}{field.required ? ' *' : ''}
                          <textarea className="form-control" rows={field.type === 'json' ? 4 : 1} placeholder={field.type === 'json' ? '{} ou []' : ''} value={fields[field.name] || ''} onChange={(event) => setFields((previous) => ({ ...previous, [field.name]: event.target.value }))} />
                        </label>
                      ))}
                    </div>
                    <button className="btn btn-primary mt-3" type="button" onClick={execute} disabled={!state.config}>Exécuter via API</button>
                    <pre className="openinfra-result mt-3">{JSON.stringify(state.result ?? 'Résultat en attente.', null, 2)}</pre>
                  </section>
                </div>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
}

function Metric({ title, value }) {
  return <article className="col-md-6 col-xl-3"><div className="card h-100 openinfra-metric"><div className="card-body"><h2 className="h6 text-muted">{title}</h2><p className="openinfra-metric-value mb-0">{value}</p></div></div></article>;
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
