import 'bootstrap/dist/css/bootstrap.min.css';
import './openinfra-theme.css';
import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';

const ICONS = {
  speedometer2: 'M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4z',
  table: 'M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2z',
  grid: 'M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3z',
  home: 'M8 3.293l6 6V15a1 1 0 0 1-1 1h-3v-4H6v4H3a1 1 0 0 1-1-1V9.293l6-6z',
  activity: 'M6.5 12a.5.5 0 0 1-.447-.276L3.382 6.382 1.894 9.36A.5.5 0 0 1 1.447 9.636H.5a.5.5 0 0 1 0-1h.638l1.915-3.83a.5.5 0 0 1 .894 0L6.5 9.91l2.553-5.105a.5.5 0 0 1 .894 0l1.915 3.83h3.638a.5.5 0 0 1 0 1h-3.947a.5.5 0 0 1-.447-.276L9.5 6.382l-2.553 5.342A.5.5 0 0 1 6.5 12z',
  shield: 'M5.338 1.59a61.44 61.44 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188A10.7 10.7 0 0 0 8 15a10.7 10.7 0 0 0 3.574-2.976c1.527-1.998 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39 61.44 61.44 0 0 0-2.837-.856C9.552 1.29 8.531 1.067 8 1.067c-.531 0-1.552.223-2.662.523z',
};

const MODULES = [
  { id: 'overview', label: 'Dashboard', icon: 'speedometer2', operations: [{ id: 'version', label: 'Version runtime', path: '/version', method: 'GET', fields: [] }] },
  { id: 'ri', label: 'Ressources Inventory', shortLabel: 'RI', icon: 'table', operations: [
    { id: 'ri-list', label: 'Lister les objets RI', path: '/v1/ri/objects', method: 'GET', fields: ['Type de ressource', 'Tag', 'Limite'] },
    { id: 'ri-upsert', label: 'Créer / mettre à jour une ressource', path: '/v1/ri/objects', method: 'POST', fields: ['Opérateur', 'Clé RI', 'Type de ressource', 'Nom affiché', 'Source autoritative', 'Numéro de série', 'Constructeur', 'Modèle', 'Site', 'Bâtiment', 'Salle', 'Ligne salle', 'Colonne salle', 'Rack', 'IP de management', 'État cycle de vie', 'Tags'] },
  ] },
  { id: 'ipam', label: 'IPAM', icon: 'grid', operations: [{ id: 'ipam-search', label: 'Rechercher dans l’IPAM', path: '/v1/ipam/search', method: 'GET', fields: ['Recherche', 'Limite'] }] },
  { id: 'dcim', label: 'DCIM', icon: 'home', operations: [{ id: 'dcim-rack-capacity', label: 'Capacité rack', path: '/v1/dcim/rack-capacity', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Rack'] }] },
  { id: 'discovery', label: 'Discovery', icon: 'activity', operations: [{ id: 'collectors-register', label: 'Enregistrer un agent proxy Enterprise', path: '/v1/discovery/collectors', method: 'POST', fields: ['Opérateur', 'Nom agent proxy', 'Empreinte certificat', 'Scopes autorisés', 'Endpoint mTLS'] }] },
  { id: 'security', label: 'Sécurité / RBAC / Audit', shortLabel: 'Sécurité', icon: 'shield', operations: [{ id: 'audit-events', label: 'Événements d’audit', path: '/v1/audit/events', method: 'GET', fields: ['Action', 'Type cible', 'Limite'] }] },
];

function Icon({ name, className = 'bi' }) {
  return <svg className={className} width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d={ICONS[name] || ICONS.grid} /></svg>;
}

function Dashboard() {
  const [config, setConfig] = useState({ apiBaseUrl: '/api', version: 'indisponible', webBackendTrust: 'server-side' });
  const [ready, setReady] = useState(null);
  const [version, setVersion] = useState(null);
  const [selected, setSelected] = useState(MODULES[0].operations[0]);
  const [activeModuleId, setActiveModuleId] = useState('overview');
  const [opened, setOpened] = useState(new Set(['ri']));
  const [tenant, setTenant] = useState('default');
  const [result, setResult] = useState('Résultat en attente.');
  const operationsCount = useMemo(() => MODULES.reduce((total, module) => total + module.operations.length, 0), []);

  useEffect(() => {
    Promise.all([
      fetch('/config.json', { credentials: 'same-origin' }).then((response) => response.json()),
      fetch('/ready', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : { ready: false }),
      fetch('/version', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : null),
    ]).then(([loadedConfig, loadedReady, loadedVersion]) => {
      setConfig(loadedConfig);
      setReady(loadedReady);
      setVersion(loadedVersion);
    }).catch(() => setReady({ ready: false }));
  }, []);

  function chooseOperation(module, operation) {
    setSelected(operation);
    setActiveModuleId(module.id);
    setOpened(new Set([...opened, module.id]));
    setResult('Résultat en attente.');
  }

  function toggleAccordion(moduleId) {
    const next = new Set(opened);
    if (next.has(moduleId)) next.delete(moduleId); else next.add(moduleId);
    setOpened(next);
  }

  function execute() {
    setResult(JSON.stringify({ tenant_id: tenant, action: selected.id, via: config.apiBaseUrl, trust: config.webBackendTrust }, null, 2));
  }

  const displayedVersion = version?.version || config.version || 'indisponible';
  const filteredModules = MODULES;

  return <div className="openinfra-shell">
    <header>
      <div className="px-3 py-2 bg-dark text-white openinfra-top-header"><div className="container-fluid"><div className="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start"><a href="/" className="d-flex align-items-center my-2 my-lg-0 me-lg-auto text-white text-decoration-none" aria-label="OpenInfra accueil"><span className="openinfra-brand-mark me-2">OI</span><span className="fs-5 fw-semibold">OpenInfra</span></a><ul className="nav col-12 col-lg-auto my-2 justify-content-center my-md-0 text-small">{MODULES.slice(0, 6).map((module) => <li key={module.id}><button type="button" className={`nav-link border-0 bg-transparent ${activeModuleId === module.id ? 'text-secondary' : 'text-white'}`} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} className="bi d-block mx-auto mb-1 openinfra-top-icon" />{module.shortLabel || module.label}</button></li>)}</ul></div></div></div>
    </header>
    <div className="container-fluid"><div className="row"><nav className="col-lg-3 col-xl-2 openinfra-sidebar" aria-label="Sidebar navigation"><div className="openinfra-sidebar-heading">Pilotage</div>{filteredModules.map((module) => module.id === 'overview' ? <button key={module.id} type="button" className={`nav-link openinfra-sidebar-dashboard w-100 text-start ${activeModuleId === module.id ? 'active' : ''}`} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} />Dashboard</button> : <section className={`openinfra-accordion ${opened.has(module.id) ? 'open' : ''}`} key={module.id}><button type="button" className={`openinfra-accordion-toggle ${activeModuleId === module.id ? 'active' : ''}`} aria-expanded={opened.has(module.id)} onClick={() => toggleAccordion(module.id)}><span><Icon name={module.icon} />{module.shortLabel || module.label}</span><span className="openinfra-chevron">›</span></button><div className={`openinfra-accordion-panel fade ${opened.has(module.id) ? 'show' : ''}`}>{module.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selected.id === operation.id ? 'active' : ''}`} onClick={() => chooseOperation(module, operation)}>{operation.label}</button>)}</div></section>)}</nav><main className="col-lg-9 col-xl-10 ms-sm-auto openinfra-main"><div className="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-2 mb-3 openinfra-titlebar"><div><h1 className="h2">Dashboard de pilotage OpenInfra</h1><p className="text-muted mb-0">Portail BFF server-side : l’opérateur ne saisit aucun token technique ; les secrets PostgreSQL restent côté service web.</p></div><div className="btn-toolbar mb-2 mb-md-0"><span className="badge text-bg-primary me-2">{config.edition || 'runtime'}</span><span className="badge text-bg-secondary">{config.authMode || 'standard'}</span></div></div>{ready?.ready === true && <div className="alert alert-success" role="status">Backend prêt.</div>}<div className="row g-3 mb-4"><Metric title="Version" value={displayedVersion} /><Metric title="API" value={config.apiBaseUrl || '/api'} /><Metric title="Trust" value={config.webBackendTrust || 'server-side'} /><Metric title="Modules" value={`${operationsCount} opérations`} /></div><section className="card openinfra-operation-card"><div className="card-body"><h2 className="h4">{selected.label}</h2><p className="text-muted">Formulaire métier typé. Aucun champ générique Attributs n’est demandé à l’opérateur.</p><div className="row g-3 mb-3"><label className="col-md-4 form-label">Tenant<input className="form-control" value={tenant} onChange={(event) => setTenant(event.target.value)} /></label></div><div className="row g-3">{selected.fields.map((field) => <label className="col-md-6 col-xl-4 form-label" key={field}>{field}<input className="form-control" /></label>)}</div><button type="button" className="btn btn-primary mt-3" onClick={execute}>Exécuter</button><pre className="openinfra-result mt-3">{result}</pre></div></section></main></div></div>
  </div>;
}

function Metric({ title, value }) {
  return <article className="col-md-6 col-xl-3"><div className="card h-100 openinfra-metric"><div className="card-body"><h2 className="h6 text-muted">{title}</h2><p className="openinfra-metric-value mb-0">{value}</p></div></div></article>;
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
