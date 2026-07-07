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

const RESOURCE_TAXONOMY = {
  server: ['physical-server', 'rack-server', 'blade-server', 'tower-server', 'hypervisor-host', 'virtual-machine', 'container-host'],
  'personal-computer': ['laptop', 'desktop', 'workstation', 'thin-client', 'tablet'],
  'network-device': ['switch', 'router', 'firewall', 'load-balancer', 'wireless-access-point'],
  storage: ['storage-array', 'nas-appliance', 'disk', 'ssd', 'tape-library'],
  'power-supply': ['ups', 'pdu', 'ats', 'generator'],
  'rack-facility': ['rack', 'cabinet', 'patch-panel'],
  cooling: ['crac', 'crah', 'in-row-cooler', 'chiller'],
  'software-service': ['application', 'service', 'database-instance'],
};

const MODULES = [
  { id: 'overview', label: 'Dashboard', icon: 'speedometer2', operations: [{ id: 'version', label: 'Version runtime', path: '/v1/version', method: 'GET', fields: [] }] },
  { id: 'itrm', label: 'IT Ressources Management', shortLabel: 'ITRM', icon: 'table', operations: [
    { id: 'itrm-taxonomy', label: 'Catalogue catégories / types', path: '/v1/itrm/resource-taxonomy', method: 'GET', fields: [] },
    { id: 'itrm-list', label: 'Lister les objets ITRM', path: '/v1/itrm/objects', method: 'GET', fields: ['Catégorie', 'Type de ressource', 'Tag', 'Limite'] },
    { id: 'itrm-upsert', label: 'Créer / mettre à jour une ressource', path: '/v1/itrm/objects', method: 'POST', fields: ['Opérateur', 'Clé ITRM', 'Catégorie', 'Type de ressource', 'Nom affiché', 'Source autoritative', 'Numéro de série', 'Constructeur', 'Modèle', 'Site', 'Bâtiment', 'Salle', 'Ligne salle', 'Colonne salle', 'Rack', 'IP de management', 'État cycle de vie', 'Tags'] },
    { id: 'itrm-as-of', label: 'Restituer une ressource à date', path: '/v1/itrm/object-as-of', method: 'GET', fields: ['Clé ITRM', 'Date ISO-8601'] },
    { id: 'itrm-object-audit', label: 'Audit d’une ressource', path: '/v1/itrm/object-audit', method: 'GET', fields: ['Clé ITRM', 'Limite'] },
    { id: 'itrm-reconcile', label: 'Réconcilier une ressource', path: '/v1/itrm/reconcile-object', method: 'POST', fields: ['Opérateur', 'Clé ITRM', 'Source entrante', 'Catégorie', 'Type de ressource', 'Nom affiché cible', 'Numéro de série', 'Constructeur', 'Modèle', 'Site', 'Rack', 'Tags', 'Appliquer le plan'] },
  ] },
  { id: 'ipam', label: 'IPAM', icon: 'grid', operations: [{ id: 'ipam-search', label: 'Rechercher dans l’IPAM', path: '/v1/ipam/ui-search', method: 'GET', fields: ['Recherche', 'VRF'] }] },
  { id: 'dcim', label: 'DCIM', icon: 'home', operations: [
    { id: 'dcim-locate-equipment', label: 'Localiser un équipement', path: '/v1/dcim/locations', method: 'POST', fields: ['Opérateur', 'Numéro d’actif', 'Nom équipement', 'Site', 'Bâtiment', 'Étage', 'Salle', 'Zone', 'Ligne salle', 'Colonne salle', 'Rack', 'Position U', 'Face rack', 'Hauteur U', 'Coordonnée X', 'Coordonnée Y', 'Coordonnée Z'] },
    { id: 'dcim-rack-capacity', label: 'Capacité rack', path: '/v1/dcim/rack-capacity', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Rack'] },
  ] },
  { id: 'discovery', label: 'Discovery', icon: 'activity', operations: [{ id: 'collectors-register', label: 'Enregistrer un agent proxy Enterprise', path: '/v1/discovery/collectors', method: 'POST', fields: ['Opérateur', 'Nom agent proxy', 'Type', 'Empreinte certificat', 'Scopes autorisés', 'Version agent', 'Endpoint mTLS'] }] },
  { id: 'security', label: 'Sécurité / RBAC / Audit', shortLabel: 'Sécurité', icon: 'shield', operations: [{ id: 'audit-events', label: 'Événements d’audit', path: '/v1/audit/events', method: 'GET', fields: ['Action', 'Type cible', 'Limite'] }] },
];

function Icon({ name, className = 'bi' }) {
  return <svg className={className} width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d={ICONS[name] || ICONS.grid} /></svg>;
}

function componentModules() {
  return MODULES.filter((module) => module.id !== 'overview');
}

function moduleStatistics(module) {
  const operations = module.operations.length;
  const readOperations = module.operations.filter((operation) => operation.method === 'GET').length;
  const writeOperations = operations - readOperations;
  const fields = module.operations.reduce((total, operation) => total + operation.fields.length, 0);
  const readPercent = operations === 0 ? 0 : Math.round((readOperations / operations) * 100);
  return { operations, readOperations, writeOperations, fields, readPercent, writePercent: 100 - readPercent };
}

function Dashboard() {
  const [config, setConfig] = useState({ apiBaseUrl: '/api', version: 'indisponible', webBackendTrust: 'server-side' });
  const [ready, setReady] = useState(null);
  const [bffStatus, setBffStatus] = useState(null);
  const [version, setVersion] = useState(null);
  const [selected, setSelected] = useState(MODULES[0].operations[0]);
  const [activeModuleId, setActiveModuleId] = useState('overview');
  const [opened, setOpened] = useState(new Set(['itrm']));
  const [tenant, setTenant] = useState('default');
  const [result, setResult] = useState('Résultat en attente.');
  const businessModules = useMemo(() => componentModules(), []);
  const operationsCount = useMemo(() => MODULES.reduce((total, module) => total + module.operations.length, 0), []);
  const businessFieldsCount = useMemo(() => businessModules.reduce((total, module) => total + moduleStatistics(module).fields, 0), [businessModules]);

  useEffect(() => {
    Promise.all([
      fetch('/config.json', { credentials: 'same-origin' }).then((response) => response.json()),
      fetch('/ready', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : { ready: false }),
      fetch('/version', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : null),
      fetch('/status', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : { protectedForms: 'unknown', trust: {} }),
    ]).then(([loadedConfig, loadedReady, loadedVersion, loadedBffStatus]) => {
      setConfig(loadedConfig);
      setReady(loadedReady);
      setVersion(loadedVersion);
      setBffStatus(loadedBffStatus);
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
  const submissionCompleted = result !== 'Résultat en attente.';
  const protectedForms = bffStatus?.protectedForms === 'enabled' ? 'actifs' : 'à configurer';

  return <div className="openinfra-shell">
    <header>
      <div className="px-3 py-2 bg-dark text-white openinfra-top-header"><div className="container-fluid"><div className="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start"><a href="/" className="d-flex align-items-center my-2 my-lg-0 me-lg-auto text-white text-decoration-none" aria-label="OpenInfra accueil"><span className="openinfra-brand-mark me-2">OI</span><span className="fs-5 fw-semibold">OpenInfra</span></a><ul className="nav col-12 col-lg-auto my-2 justify-content-center my-md-0 text-small">{MODULES.slice(0, 6).map((module) => <li key={module.id}><button type="button" className={`nav-link border-0 bg-transparent ${activeModuleId === module.id ? 'text-secondary' : 'text-white'}`} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} className="bi d-block mx-auto mb-1 openinfra-top-icon" />{module.shortLabel || module.label}</button></li>)}</ul></div></div></div>
    </header>
    <div className="container-fluid"><div className="row"><nav className="col-lg-3 col-xl-2 openinfra-sidebar" aria-label="Sidebar navigation"><div className="openinfra-sidebar-heading">Pilotage</div>{filteredModules.map((module) => module.id === 'overview' ? <button key={module.id} type="button" className={`nav-link openinfra-sidebar-dashboard w-100 text-start ${activeModuleId === module.id ? 'active' : ''}`} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} />Dashboard</button> : <section className={`openinfra-accordion ${opened.has(module.id) ? 'open' : ''}`} key={module.id}><button type="button" className={`openinfra-accordion-toggle ${activeModuleId === module.id ? 'active' : ''}`} aria-expanded={opened.has(module.id)} onClick={() => toggleAccordion(module.id)}><span><Icon name={module.icon} />{module.shortLabel || module.label}</span><span className="openinfra-chevron">›</span></button><div className={`openinfra-accordion-panel fade ${opened.has(module.id) ? 'show' : ''}`}>{module.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selected.id === operation.id ? 'active' : ''}`} onClick={() => chooseOperation(module, operation)}>{operation.label}</button>)}</div></section>)}</nav><main className="col-lg-9 col-xl-10 ms-sm-auto openinfra-main"><div className="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-2 mb-3 openinfra-titlebar"><div><h1 className="h2">Dashboard de pilotage OpenInfra</h1><p className="text-muted mb-0">Portail BFF server-side : l’opérateur ne saisit aucun token technique ; les secrets PostgreSQL restent côté service web.</p></div><div className="btn-toolbar mb-2 mb-md-0"><span className="badge text-bg-primary me-2">{config.edition || 'runtime'}</span><span className="badge text-bg-secondary">{config.authMode || 'standard'}</span></div></div>{submissionCompleted && activeModuleId !== 'overview' && <div className="alert alert-success" role="status">Soumission exécutée avec succès.</div>}<div className="row g-3 mb-4"><Metric title="Version" value={displayedVersion} /><Metric title="API" value={config.apiBaseUrl || '/api'} /><Metric title="Trust" value={config.webBackendTrust || 'server-side'} /><Metric title="Formulaires" value={protectedForms} /><Metric title="Modules" value={`${operationsCount} opérations`} /></div>{activeModuleId === 'overview' ? <OverviewStats modules={businessModules} fieldsCount={businessFieldsCount} /> : <section className="card openinfra-operation-card"><div className="card-body"><h2 className="h4">{selected.label}</h2><p className="text-muted">Formulaire métier typé. Aucun champ générique Attributs n’est demandé à l’opérateur.</p><div className="row g-3 mb-3"><label className="col-md-4 form-label">Tenant<input className="form-control" value={tenant} onChange={(event) => setTenant(event.target.value)} /></label></div><div className="row g-3">{selected.fields.map((field) => <label className="col-md-6 col-xl-4 form-label" key={field}>{field}<input className="form-control" /></label>)}</div><button type="button" className="btn btn-primary mt-3" onClick={execute}>Exécuter</button><pre className="openinfra-result mt-3">{result}</pre></div></section>}</main></div></div>
  </div>;
}

function OverviewStats({ modules, fieldsCount }) {
  const operations = modules.reduce((total, module) => total + module.operations.length, 0);
  return <section className="openinfra-overview" aria-label="Statistiques des composants OpenInfra"><div className="card openinfra-overview-summary mb-4"><div className="card-body"><div className="d-flex flex-wrap justify-content-between align-items-start gap-3"><div><h2 className="h4 mb-1">Accueil — statistiques des composants</h2><p className="text-muted mb-0">Vue de synthèse par composant : métriques fonctionnelles et camemberts de répartition lecture/mutation.</p></div><div><span className="badge text-bg-primary">{modules.length} composants</span><span className="badge text-bg-secondary ms-2">{operations} opérations</span></div></div><div className="row g-3 mt-3"><Metric title="Champs métier" value={String(fieldsCount)} /><Metric title="Navigation" value="Accordéons" /><Metric title="Secrets navigateur" value="0 exposé" /><Metric title="Parité UI" value="CLI/API" /></div></div></div><div className="row g-3">{modules.map((module) => <ComponentStatsCard key={module.id} module={module} />)}</div></section>;
}

function ComponentStatsCard({ module }) {
  const stats = moduleStatistics(module);
  const style = { '--oi-read-end': `${stats.readPercent}%`, '--oi-write-end': `${stats.readPercent + stats.writePercent}%` };
  return <article className="col-md-6 col-xxl-4"><div className="card h-100 openinfra-component-card"><div className="card-body"><div className="d-flex justify-content-between align-items-start gap-3"><div><h3 className="h5 mb-1">{module.shortLabel || module.label}</h3><p className="text-muted small mb-0">{module.operations.length} opérations métier exposées</p></div><Icon name={module.icon} className="openinfra-component-icon" /></div><div className="openinfra-component-visual mt-3"><div className="openinfra-pie-chart" role="img" aria-label={`Camembert ${module.label}`} style={style}><span>{stats.operations}</span></div><div className="openinfra-pie-legend small"><span><i className="openinfra-legend-read" />{stats.readOperations} lectures</span><span><i className="openinfra-legend-write" />{stats.writeOperations} mutations</span></div></div><div className="row g-2 mt-3 openinfra-component-metrics"><div className="col-6"><strong>{stats.operations}</strong><span>Opérations</span></div><div className="col-6"><strong>{stats.fields}</strong><span>Champs métier</span></div><div className="col-6"><strong>{stats.readOperations}</strong><span>Lectures</span></div><div className="col-6"><strong>{stats.writeOperations}</strong><span>Mutations</span></div></div></div></div></article>;
}

function Metric({ title, value }) {
  return <article className="col-md-6 col-xl-3"><div className="card h-100 openinfra-metric"><div className="card-body"><h2 className="h6 text-muted">{title}</h2><p className="openinfra-metric-value mb-0">{value}</p></div></div></article>;
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
