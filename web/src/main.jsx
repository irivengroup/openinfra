import 'bootstrap/dist/css/bootstrap.min.css';
import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

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
}

function Dashboard() {
  const [state, setState] = useState({ config: null, version: null, ready: null, error: null });

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
      setState({ config, version, ready, error: null });
    } catch (error) {
      setState((previous) => ({ ...previous, error }));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const workflows = [
    ['Source of Truth', '/api/v1/sot/objects', 'Inventaire et consultation paginée'],
    ['IPAM', '/api/v1/ipam/*', 'Réservations et capacité'],
    ['DCIM', '/api/v1/dcim/*', 'Racks, salles, localisation'],
    ['Audit', '/api/v1/audit/events', 'Traçabilité des permissions'],
  ];

  return (
    <>
      <nav className="navbar navbar-dark bg-dark px-4">
        <span className="navbar-brand mb-0 h1">OpenInfra Web</span>
        <span className="badge text-bg-primary">{state.config?.edition ?? 'runtime'}</span>
      </nav>
      <section className="container py-4">
        <h1>Console d'exploitation OpenInfra</h1>
        <p className="lead">
          Interface web API-only : aucun accès direct PostgreSQL, aucun secret runtime exposé au navigateur.
        </p>
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
            <h2 className="h4">Parcours opérationnels P08</h2>
            <div className="table-responsive">
              <table className="table">
                <thead><tr><th>Domaine</th><th>API consommée</th><th>Objectif UI</th></tr></thead>
                <tbody>
                  {workflows.map(([domain, api, goal]) => (
                    <tr key={domain}><td>{domain}</td><td>{api}</td><td>{goal}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
        <button className="btn btn-primary mt-3" type="button" onClick={refresh}>Rafraîchir</button>
      </section>
    </>
  );
}

function Metric({ title, value }) {
  return (
    <article className="col-md-3">
      <div className="card h-100">
        <div className="card-body">
          <h2 className="h5">{title}</h2>
          <p>{value}</p>
        </div>
      </div>
    </article>
  );
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
