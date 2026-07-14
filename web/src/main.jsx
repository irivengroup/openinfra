import 'bootstrap/dist/css/bootstrap.min.css';
import './openinfra-theme.css';
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { OpenInfraI18n, localizeOpenInfraCatalog } from './i18n.js';
import { formCountryCode, inputAttributesForField, inputTypeForField, normalizeFieldDefinition, normalizeFieldValue, validateControl } from './form-fields.js';
import { MODULES, SIDEBAR_CONTEXTS, loadDomain } from './domain-manifest.js';
import { OpenInfraQueryCache } from './core/query-cache.js';
import { installOpenInfraWebVitals } from './core/web-vitals.js';
import { VirtualizedList } from './VirtualizedList.jsx';

let RESOURCE_TAXONOMY = {};
let RESOURCE_CATEGORY_OPTIONS = [];


const ICONS = {
  speedometer2: 'M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4z',
  table: 'M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2z',
  reference: 'M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z',
  asset: 'M2 1a2 2 0 0 1 2-2h5.6a2 2 0 0 1 1.414.586l2.4 2.4A2 2 0 0 1 14 3.4V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V1zm2 .8a.8.8 0 0 0-.8.8v10.8a.8.8 0 0 0 .8.8h8a.8.8 0 0 0 .8-.8V4.4h-2.2a1.8 1.8 0 0 1-1.8-1.8V.8H4zm1.25 5.05a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 0 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3zm-2.05 4.6a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 1 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3z',
  grid: 'M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3z',
  home: 'M8 3.293l6 6V15a1 1 0 0 1-1 1h-3v-4H6v4H3a1 1 0 0 1-1-1V9.293l6-6z',
  search: 'M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.099zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z',
  menu: 'M2 4h12v1.4H2V4zm0 3.3h12v1.4H2V7.3zm0 3.3h12V12H2v-1.4z',
  activity: 'M6.5 12a.5.5 0 0 1-.447-.276L3.382 6.382 1.894 9.36A.5.5 0 0 1 1.447 9.636H.5a.5.5 0 0 1 0-1h.638l1.915-3.83a.5.5 0 0 1 .894 0L6.5 9.91l2.553-5.105a.5.5 0 0 1 .894 0l1.915 3.83h3.638a.5.5 0 0 1 0 1h-3.947a.5.5 0 0 1-.447-.276L9.5 6.382l-2.553 5.342A.5.5 0 0 1 6.5 12z',
  sliders: 'M3 4h10v1H3V4zm2 3h6v1H5V7zm-2 3h10v1H3v-1z',
  shield: 'M5.338 1.59a61.44 61.44 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188A10.7 10.7 0 0 0 8 15a10.7 10.7 0 0 0 3.574-2.976c1.527-1.998 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39 61.44 61.44 0 0 0-2.837-.856C9.552 1.29 8.531 1.067 8 1.067c-.531 0-1.552.223-2.662.523z',
};

function Icon({ name, className = 'bi' }) {
  return <svg className={className} width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d={ICONS[name] || ICONS.grid} /></svg>;
}

function componentModules() {
  return MODULES.filter((module) => module.id !== 'overview');
}

function moduleStatistics(module) {
  const base = module.loaded ? {
    operations: module.operations.length,
    readOperations: module.operations.filter((operation) => operation.method === 'GET').length,
    fields: module.operations.reduce((total, operation) => total + operation.fields.length, 0),
  } : module.stats;
  const operations = base.operations || 0;
  const readOperations = base.readOperations || 0;
  const writeOperations = base.writeOperations ?? operations - readOperations;
  const readPercent = operations === 0 ? 0 : Math.round((readOperations / operations) * 100);
  return { operations, readOperations, writeOperations, fields: base.fields || 0, readPercent, writePercent: 100 - readPercent };
}

function normalizeSearchText(value) {
  return String(value || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}


function buildGlobalSearchUrl(apiBaseUrl, tenant, query, limit = 6) {
  const base = String(apiBaseUrl || '/api').replace(/\/$/, '');
  const params = new URLSearchParams({ tenant_id: tenant || 'default', query, limit: String(limit) });
  return `${base}/v1/search/global?${params.toString()}`;
}

function buildApiDocumentationUrl(apiBaseUrl, route) {
  const normalizedRoute = String(route || '/docs').startsWith('/') ? String(route || '/docs') : `/${route}`;
  const value = String(apiBaseUrl || '/api').trim();
  if (/^https?:\/\//i.test(value)) {
    const url = new URL(value);
    return `${url.origin}${normalizedRoute}`;
  }
  return normalizedRoute;
}

function apiDocumentationLinks(config) {
  const published = config?.apiDocumentation || {};
  return {
    swaggerUrl: published.swaggerUrl || buildApiDocumentationUrl(config?.apiBaseUrl, '/docs'),
    redocUrl: published.redocUrl || buildApiDocumentationUrl(config?.apiBaseUrl, '/redoc'),
    openapiUrl: published.openapiUrl || buildApiDocumentationUrl(config?.apiBaseUrl, '/openapi.yaml'),
  };
}

function globalSearchGroups(query, searchIndex) {
  const normalizedQuery = normalizeSearchText(query.trim());
  if (!normalizedQuery || !Array.isArray(searchIndex)) return [];
  const grouped = new Map();
  for (const operation of searchIndex) {
    const haystack = [operation.moduleLabel, operation.id, operation.label, operation.method, operation.path].filter(Boolean).join(' ');
    if (!normalizeSearchText(haystack).includes(normalizedQuery)) continue;
    if (!grouped.has(operation.moduleId)) grouped.set(operation.moduleId, []);
    grouped.get(operation.moduleId).push(operation);
  }
  return Array.from(grouped.entries()).map(([moduleId, operations]) => ({
    module: MODULES.find((module) => module.id === moduleId),
    operations: operations.slice(0, 8),
    total: operations.length,
  })).filter((group) => group.module && group.total > 0);
}

function sidebarOperationGroups(module) {
  const configuredGroups = SIDEBAR_CONTEXTS[module.id] || [];
  const byId = new Map(module.operations.map((operation) => [operation.id, operation]));
  const groupedIds = new Set();
  const groups = configuredGroups.map((group) => {
    const operations = group.operationIds.map((id) => byId.get(id)).filter(Boolean);
    operations.forEach((operation) => groupedIds.add(operation.id));
    return { label: group.label, operations };
  }).filter((group) => group.operations.length > 0);
  const remaining = module.operations.filter((operation) => !groupedIds.has(operation.id));
  if (remaining.length > 0) {
    groups.push({ label: 'Autres', operations: remaining });
  }
  return groups;
}

function sidebarContextKey(moduleId, label) {
  return `${moduleId}::${label}`;
}

function contextForOperation(module, operationId) {
  return sidebarOperationGroups(module).find((group) => group.operations.some((operation) => operation.id === operationId));
}

function withoutModuleContexts(openedContexts, moduleId) {
  const next = new Set(openedContexts);
  for (const key of Array.from(next)) {
    if (key.startsWith(`${moduleId}::`)) {
      next.delete(key);
    }
  }
  return next;
}

function slugifyContextLabel(value) {
  return String(value ?? 'context')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'context';
}

function isMegamenuViewport() {
  return typeof window !== 'undefined'
    && window.matchMedia('(min-width: 768px) and (max-width: 1199.98px)').matches;
}

function NavigationTree({
  modules,
  activeNavigationModuleId,
  selectedOperationId,
  opened,
  openedContexts,
  chooseOperation,
  toggleAccordion,
  toggleSidebarContext,
  surface = 'sidebar',
}) {
  return modules.map((module) => {
    if (module.id === 'overview') {
      return <button key={module.id} type="button" className={`nav-link openinfra-sidebar-dashboard w-100 text-start ${activeNavigationModuleId === module.id ? 'active' : ''}`} aria-current={activeNavigationModuleId === module.id ? 'page' : undefined} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} />Dashboard</button>;
    }
    const moduleOpened = opened.has(module.id);
    const accordionId = `openinfra-${surface}-accordion-${module.id}`;
    const panelId = `openinfra-${surface}-panel-${module.id}`;
    return <section className={`openinfra-accordion ${moduleOpened ? 'open' : ''}`} key={module.id}>
      <button type="button" id={accordionId} className={`openinfra-accordion-toggle ${activeNavigationModuleId === module.id ? 'active' : ''}`} aria-expanded={moduleOpened} aria-controls={panelId} aria-current={activeNavigationModuleId === module.id ? 'page' : undefined} onClick={() => toggleAccordion(module.id)}><span><Icon name={module.icon} />{module.shortLabel || module.label}</span><span className="openinfra-chevron">›</span></button>
      <div id={panelId} className={`openinfra-accordion-panel fade ${moduleOpened ? 'show' : ''}`} role="region" aria-labelledby={accordionId}>
        <div className="openinfra-accordion-panel-inner">
          {!module.loaded && moduleOpened && <div className="px-3 py-2 small text-muted" role="status">Loading component…</div>}
          {sidebarOperationGroups(module).map((group) => {
            const contextKey = sidebarContextKey(module.id, group.label);
            const contextOpened = openedContexts.has(contextKey);
            const contextId = `openinfra-${surface}-context-${module.id}-${slugifyContextLabel(group.label)}`;
            return <section key={`${module.id}-${group.label}`} className={`openinfra-sidebar-context ${contextOpened ? 'open' : ''}`} role="group" aria-label={group.label}>
              <button type="button" className={`openinfra-sidebar-context-title ${contextOpened && activeNavigationModuleId === module.id ? 'active' : ''}`} aria-expanded={contextOpened} aria-controls={contextId} onClick={() => toggleSidebarContext(module.id, group.label)}>{group.label}</button>
              <div id={contextId} className={`openinfra-sidebar-context-panel ${contextOpened ? 'show' : ''}`} role="region" aria-label={group.label}>
                <div className="openinfra-sidebar-context-panel-inner">
                  {group.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selectedOperationId === operation.id ? 'active' : ''}`} aria-current={selectedOperationId === operation.id ? 'page' : undefined} onClick={() => chooseOperation(module, operation)}>{operation.label}</button>)}
                </div>
              </div>
            </section>;
          })}
        </div>
      </div>
    </section>;
  });
}

function MegaMenu({ module, selectedOperationId, chooseOperation, close, i18n }) {
  if (!module || module.id === 'overview') {
    return null;
  }
  return <section id="openinfra-mega-menu" className="openinfra-mega-menu" aria-label={module.shortLabel || module.label}>
    <div className="openinfra-mega-menu-header"><div><Icon name={module.icon} className="openinfra-mega-menu-icon" /><strong>{module.label}</strong></div><button type="button" className="openinfra-navigation-close" aria-label={i18n.t('closeNavigation')} onClick={close}>×</button></div>
    <div className="openinfra-mega-menu-grid">
      {sidebarOperationGroups(module).map((group) => <section className="openinfra-mega-menu-group" role="group" aria-label={group.label} key={`${module.id}-${group.label}`}><h2>{group.label}</h2><div>{group.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selectedOperationId === operation.id ? 'active' : ''}`} aria-current={selectedOperationId === operation.id ? 'page' : undefined} onClick={() => chooseOperation(module, operation, true)}>{operation.label}</button>)}</div></section>)}
    </div>
  </section>;
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Impossible de lire la preuve sélectionnée.'));
    reader.onload = () => {
      const result = String(reader.result || '');
      const separator = result.indexOf(',');
      if (separator < 0) reject(new Error('Le fichier sélectionné est invalide.'));
      else resolve(result.slice(separator + 1));
    };
    reader.readAsDataURL(file);
  });
}

function OperationField({ entry, index, i18n, language }) {
  const field = normalizeFieldDefinition(entry, index);
  const fieldId = `openinfra-react-field-${index}`;
  const requiredText = field.required ? <span aria-hidden="true"> *</span> : null;
  if (field.type === 'file') {
    const attributes = inputAttributesForField(field);
    return <div className="col-12"><label className="form-label" htmlFor={fieldId}>{i18n.label(field.label)}{requiredText}</label><input id={fieldId} name={field.name} className="form-control" type="file" required={field.required} {...attributes} onChange={(event) => { event.currentTarget.setCustomValidity(''); event.currentTarget.removeAttribute('aria-invalid'); }} /><p className="form-text">JPEG, PNG, WebP ou PDF — 2 Mio maximum.</p></div>;
  }
  if (field.type === 'select' || field.type === 'boolean') {
    const options = field.type === 'boolean' ? ['false', 'true'] : field.options || [];
    return <div className="col-md-6 col-xl-4"><label className="form-label" htmlFor={fieldId}>{i18n.label(field.label)}{requiredText}</label><select id={fieldId} name={field.name} className="form-select" defaultValue={field.defaultValue ?? ''} required={field.required} onInput={(event) => validateControl(event.currentTarget, field, i18n, { countryCode: formCountryCode(event.currentTarget.form) })}><option value=""></option>{options.map((option) => <option value={option} key={option}>{field.type === 'boolean' ? (option === 'true' ? i18n.t('yes') : i18n.t('no')) : i18n.optionLabel(option)}</option>)}</select></div>;
  }
  const attributes = inputAttributesForField(field);
  const common = {
    id: fieldId,
    name: field.name,
    defaultValue: field.defaultValue ?? '',
    required: field.required,
    className: 'form-control',
    lang: language,
    placeholder: field.placeholder ? i18n.label(field.placeholder) : undefined,
    ...attributes,
    onInput: (event) => validateControl(event.currentTarget, field, i18n, { countryCode: formCountryCode(event.currentTarget.form) }),
    onBlur: (event) => validateControl(event.currentTarget, field, i18n, { countryCode: formCountryCode(event.currentTarget.form) }),
  };
  return <div className={field.type === 'textarea' || field.type === 'json' ? 'col-12' : 'col-md-6 col-xl-4'}><label className="form-label" htmlFor={fieldId}>{i18n.label(field.label)}{requiredText}</label>{field.type === 'textarea' || field.type === 'json' ? <textarea {...common} rows={field.rows || 8} className="form-control font-monospace" /> : <input {...common} type={inputTypeForField(field)} />}</div>;
}

function validateOperationForm(form, fields, i18n) {
  const controls = Array.from(form.querySelectorAll('input[name], select[name], textarea[name]'));
  const countryCode = formCountryCode(form);
  let valid = true;
  fields.forEach((entry, index) => {
    const field = normalizeFieldDefinition(entry, index);
    const control = controls.find((candidate) => candidate.name === field.name);
    if (!control) return;
    if (field.type === 'file') {
      const file = control.files?.[0];
      const accepted = new Set(['image/jpeg', 'image/png', 'image/webp', 'application/pdf']);
      let message = '';
      if (file && file.size > 2 * 1024 * 1024) message = 'Le fichier dépasse la limite de 2 Mio.';
      else if (file && !accepted.has(file.type)) message = 'Le format de fichier n’est pas autorisé.';
      control.setCustomValidity(message);
      if (message) {
        control.setAttribute('aria-invalid', 'true');
        valid = false;
      } else control.removeAttribute('aria-invalid');
      return;
    }
    if (!validateControl(control, field, i18n, { countryCode })) valid = false;
  });
  if (!valid || !form.checkValidity()) {
    form.reportValidity();
    return false;
  }
  return true;
}

function OperationForm({ i18n, language, selected, tenant, setTenant, execute }) {
  const fields = selected.fields.map((entry, index) => normalizeFieldDefinition(entry, index));
  return <form aria-describedby="openinfra-required-fields-notice" noValidate onSubmit={(event) => { event.preventDefault(); if (validateOperationForm(event.currentTarget, fields, i18n)) execute(event.currentTarget, fields); }}><p id="openinfra-required-fields-notice" className="openinfra-required-notice">{i18n.t('requiredFieldsNotice')}</p><div className="row g-3 mb-3"><label className="col-md-4 form-label" htmlFor="openinfra-react-tenant">{i18n.t('organization')}</label><select id="openinfra-react-tenant" className="form-select" value={tenant} onChange={(event) => setTenant(event.target.value)}><option value="default">{i18n.t('defaultTenant')}</option></select></div><div className="row g-3">{fields.map((field, index) => <OperationField entry={field} index={index} i18n={i18n} language={language} key={field.name} />)}</div><button type="submit" className="btn btn-primary mt-3">{i18n.t('execute')}</button></form>;
}

function Dashboard() {
  const [i18n] = useState(() => new OpenInfraI18n());
  const [language, setLanguage] = useState(i18n.language);
  const [catalogRevision, setCatalogRevision] = useState(0);
  const [searchIndex, setSearchIndex] = useState(null);
  useMemo(() => localizeOpenInfraCatalog({
    modules: MODULES,
    contexts: SIDEBAR_CONTEXTS,
    resourceTaxonomy: RESOURCE_TAXONOMY,
    resourceCategories: RESOURCE_CATEGORY_OPTIONS,
  }, language), [catalogRevision, language]);
  const [config, setConfig] = useState({ apiBaseUrl: '/api', apiDocumentation: { swaggerUrl: '/docs', redocUrl: '/redoc', openapiUrl: '/openapi.yaml' }, version: i18n.t('unavailable'), webBackendTrust: 'server-side' });
  const [ready, setReady] = useState(null);
  const [bffStatus, setBffStatus] = useState(null);
  const [version, setVersion] = useState(null);
  const [selected, setSelected] = useState(MODULES[0].operations[0]);
  const [activeModuleId, setActiveModuleId] = useState('overview');
  const [activeNavigationModuleId, setActiveNavigationModuleId] = useState('overview');
  const [opened, setOpened] = useState(new Set());
  const [openedContexts, setOpenedContexts] = useState(new Set());
  const [tenant, setTenant] = useState('default');
  const [result, setResult] = useState(null);
  const [globalSearchQuery, setGlobalSearchQuery] = useState('');
  const [globalSearchBackend, setGlobalSearchBackend] = useState(null);
  const [globalSearchLoading, setGlobalSearchLoading] = useState(false);
  const [globalSearchError, setGlobalSearchError] = useState(null);
  const [shouldFocusMain, setShouldFocusMain] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [megaMenuModuleId, setMegaMenuModuleId] = useState(null);
  const [announcement, setAnnouncement] = useState({ id: 0, text: '' });
  const mainContentRef = useRef(null);
  const lastComponentTriggerRef = useRef(null);
  const queryCacheRef = useRef(new OpenInfraQueryCache({ defaultTtlMs: 30_000, maxEntries: 192 }));
  const businessModules = useMemo(() => componentModules(), [catalogRevision]);
  const operationsCount = useMemo(() => MODULES.reduce((total, module) => total + moduleStatistics(module).operations, 0), [catalogRevision]);
  const businessFieldsCount = useMemo(() => businessModules.reduce((total, module) => total + moduleStatistics(module).fields, 0), [businessModules]);
  const searchGroups = useMemo(() => globalSearchGroups(globalSearchQuery, searchIndex), [globalSearchQuery, language, searchIndex]);
  const apiDocs = useMemo(() => apiDocumentationLinks(config), [config]);


  async function ensureDomain(moduleId) {
    const domain = await loadDomain(moduleId);
    if (moduleId === 'rsot' && Object.keys(RESOURCE_TAXONOMY).length === 0) {
      const taxonomy = await import('./domains/rsot-taxonomy.js');
      RESOURCE_TAXONOMY = taxonomy.RESOURCE_TAXONOMY;
      RESOURCE_CATEGORY_OPTIONS = taxonomy.RESOURCE_CATEGORY_OPTIONS;
    }
    localizeOpenInfraCatalog({ modules: [domain], contexts: SIDEBAR_CONTEXTS, resourceTaxonomy: RESOURCE_TAXONOMY, resourceCategories: RESOURCE_CATEGORY_OPTIONS }, language);
    setCatalogRevision((current) => current + 1);
    return domain;
  }

  useEffect(() => installOpenInfraWebVitals({ target: window }), []);

  useLayoutEffect(() => {
    i18n.translateDom(document.getElementById('openinfra-root'));
    document.documentElement.lang = language;
    document.title = `OpenInfra — ${activeModuleId === 'overview' ? 'Dashboard' : selected.label}`;
  }, [activeModuleId, i18n, language, selected.label]);

  function announce(text) {
    setAnnouncement({ id: Date.now(), text });
  }

  useLayoutEffect(() => {
    const syncHeaderOffset = () => {
      const header = document.querySelector('.openinfra-header-stack');
      if (header instanceof HTMLElement) {
        const height = Math.ceil(header.getBoundingClientRect().height);
        if (height > 0) {
          document.documentElement.style.setProperty('--openinfra-fixed-header-height', `${height}px`);
        }
      }
    };
    syncHeaderOffset();
    window.addEventListener('resize', syncHeaderOffset);
    return () => window.removeEventListener('resize', syncHeaderOffset);
  });

  useEffect(() => {
    if (globalSearchQuery.trim() === '' || searchIndex) return undefined;
    let active = true;
    import('./search-index.js').then((loaded) => { if (active) setSearchIndex(loaded.default); }).catch(() => { if (active) setGlobalSearchError('search_index_unavailable'); });
    return () => { active = false; };
  }, [globalSearchQuery, searchIndex]);

  useEffect(() => {
    const query = globalSearchQuery.trim();
    const cache = queryCacheRef.current;
    if (query.length < 2) {
      cache.abort('global-search');
      setGlobalSearchBackend(null);
      setGlobalSearchError(null);
      setGlobalSearchLoading(false);
      return undefined;
    }
    let active = true;
    setGlobalSearchLoading(true);
    cache.run(`global-search:${tenant}:${query}`, async (signal) => {
      const response = await fetch(buildGlobalSearchUrl(config.apiBaseUrl, tenant, query, 80), { credentials: 'same-origin', headers: { Accept: 'application/json' }, signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }, { ttlMs: 15_000, scope: 'global-search' }).then((payload) => {
      if (active) { setGlobalSearchBackend(payload); setGlobalSearchError(null); }
    }).catch((error) => {
      if (active && error?.name !== 'AbortError') { setGlobalSearchBackend(null); setGlobalSearchError('backend_unavailable'); }
    }).finally(() => { if (active) setGlobalSearchLoading(false); });
    return () => { active = false; cache.abort('global-search'); };
  }, [config.apiBaseUrl, globalSearchQuery, tenant]);

  useEffect(() => {
    if (!shouldFocusMain) {
      return;
    }
    mainContentRef.current?.focus({ preventScroll: false });
    setShouldFocusMain(false);
  }, [activeModuleId, selected.id, shouldFocusMain]);

  useEffect(() => {
    const closeResponsiveNavigationFromDocument = (event) => {
      if (event?.type === 'keydown' && event.key !== 'Escape') {
        return;
      }
      if (event?.key === 'Escape' && (mobileSidebarOpen || megaMenuModuleId)) {
        event.preventDefault();
        setMobileSidebarOpen(false);
        setMegaMenuModuleId(null);
        setActiveNavigationModuleId(activeModuleId);
        announce(i18n.t('navigationClosed'));
        window.requestAnimationFrame(() => lastComponentTriggerRef.current?.focus());
      }
    };
    const handleResize = () => {
      if (!isMegamenuViewport()) {
        setMegaMenuModuleId(null);
      }
      if (!window.matchMedia('(max-width: 767.98px)').matches) {
        setMobileSidebarOpen(false);
      }
    };
    document.addEventListener('keydown', closeResponsiveNavigationFromDocument);
    window.addEventListener('resize', handleResize);
    return () => {
      document.removeEventListener('keydown', closeResponsiveNavigationFromDocument);
      window.removeEventListener('resize', handleResize);
    };
  }, [activeModuleId, i18n, megaMenuModuleId, mobileSidebarOpen]);

  useEffect(() => {
    const cache = queryCacheRef.current;
    cache.run('bootstrap', async (signal) => {
      const response = await fetch('/bootstrap.json', { credentials: 'same-origin', headers: { Accept: 'application/json' }, signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }, { ttlMs: 60_000, scope: 'bootstrap' }).then((bootstrap) => {
      setConfig((current) => bootstrap.config || current);
      setVersion(bootstrap.version || null);
      setBffStatus(bootstrap.status || { protectedForms: 'unknown', trust: {} });
    }).catch(() => setBffStatus({ protectedForms: 'unknown', trust: {} }));
    cache.run('readiness', async (signal) => {
      const response = await fetch('/ready', { credentials: 'same-origin', headers: { Accept: 'application/json' }, signal });
      return response.ok ? response.json() : { ready: false };
    }, { ttlMs: 5_000, force: true, scope: 'readiness' }).then(setReady).catch(() => setReady({ ready: false }));
    return () => { cache.abort('bootstrap'); cache.abort('readiness'); };
  }, []);

  function chooseOperation(module, operation, focusMain = false) {
    setSelected(operation);
    setActiveModuleId(module.id);
    setActiveNavigationModuleId(module.id);
    setOpened((current) => module.id === 'overview' ? new Set() : new Set([...current, module.id]));
    setOpenedContexts((current) => {
      if (module.id === 'overview') {
        return new Set();
      }
      const next = withoutModuleContexts(current, module.id);
      const context = contextForOperation(module, operation.id);
      if (context) {
        next.add(sidebarContextKey(module.id, context.label));
      }
      return next;
    });
    setResult(null);
    announce(i18n.t('operationSelected', { operation: operation.label }));
    setMobileSidebarOpen(false);
    setMegaMenuModuleId(null);
    if (focusMain) {
      setShouldFocusMain(true);
    }
  }

  async function selectSearchOperation(module, operation) {
    const loadedModule = await ensureDomain(module.id);
    const loadedOperation = loadedModule.operations.find((candidate) => candidate.id === operation.id);
    if (loadedOperation) chooseOperation(loadedModule, loadedOperation, true);
    setGlobalSearchQuery('');
  }

  function selectBackendSearchItem(item) {
    if (!item.route) return;
    fetch(item.route, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then((response) => response.json())
      .then((payload) => {
        setResult(JSON.stringify(payload, null, 2));
        setShouldFocusMain(true);
      })
      .catch((error) => {
        setResult(JSON.stringify({ error: error.message }, null, 2));
        setShouldFocusMain(true);
      });
    setGlobalSearchQuery('');
  }

  async function toggleAccordion(moduleId) {
    let module = MODULES.find((item) => item.id === moduleId);
    if (!module) return;
    const willOpen = !opened.has(moduleId);
    setActiveNavigationModuleId(module.id);
    setOpened(willOpen ? new Set([moduleId]) : new Set());
    setOpenedContexts(new Set());
    if (willOpen && !module.loaded) module = await ensureDomain(moduleId);
  }

  function toggleSidebarContext(moduleId, contextLabel) {
    const module = MODULES.find((item) => item.id === moduleId);
    if (!module || !contextLabel) {
      return;
    }
    setActiveNavigationModuleId(module.id);
    setOpened(new Set([moduleId]));
    setOpenedContexts((current) => {
      const contextKey = sidebarContextKey(moduleId, contextLabel);
      const wasOpen = current.has(contextKey);
      const next = new Set();
      if (!wasOpen) {
        next.add(contextKey);
      }
      return next;
    });
  }

  function changeLanguage(nextLanguage) {
    const normalized = i18n.setLanguage(nextLanguage);
    document.documentElement.lang = normalized;
    setLanguage(normalized);
  }

  async function openMegaMenu(module, trigger = null) {
    if (module.id === 'overview' || !isMegamenuViewport()) return;
    if (trigger instanceof HTMLElement) lastComponentTriggerRef.current = trigger;
    setActiveNavigationModuleId(module.id);
    setMobileSidebarOpen(false);
    setMegaMenuModuleId(module.id);
    announce(i18n.t('navigationOpened', { component: module.shortLabel || module.label }));
    if (!module.loaded) await ensureDomain(module.id);
  }

  async function handleModuleNavigation(module) {
    if (module.id === 'overview') { chooseOperation(module, module.operations[0]); return; }
    if (!isMegamenuViewport()) {
      const loadedModule = module.loaded ? module : await ensureDomain(module.id);
      chooseOperation(loadedModule, loadedModule.operations[0]);
      return;
    }
    await openMegaMenu(module);
  }

  function closeResponsiveNavigation({ restoreFocus = false } = {}) {
    setMobileSidebarOpen(false);
    setMegaMenuModuleId(null);
    setActiveNavigationModuleId(activeModuleId);
    announce(i18n.t('navigationClosed'));
    if (restoreFocus) {
      window.requestAnimationFrame(() => lastComponentTriggerRef.current?.focus());
    }
  }

  function handleComponentNavigationKeyDown(event, index, module) {
    const buttons = Array.from(document.querySelectorAll('.openinfra-component-link'));
    const focusAt = (targetIndex) => buttons[targetIndex]?.focus();
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      focusAt((index + 1) % buttons.length);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      focusAt((index - 1 + buttons.length) % buttons.length);
    } else if (event.key === 'Home') {
      event.preventDefault();
      focusAt(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      focusAt(buttons.length - 1);
    } else if (event.key === 'ArrowDown' && module.id !== 'overview') {
      event.preventDefault();
      openMegaMenu(module, event.currentTarget);
      window.requestAnimationFrame(() => document.querySelector('.openinfra-mega-menu .openinfra-sidebar-operation')?.focus());
    }
  }

  async function execute(form, fields) {
    const isLiveOperation = selected.id.startsWith('graph-') || selected.id.startsWith('field-') || selected.id.startsWith('simulation-') || selected.id.startsWith('greenops-') || selected.id.startsWith('sbom-') || selected.id.startsWith('rag-') || selected.id.startsWith('kubernetes-');
    if (!isLiveOperation) {
      setResult({ tenant_id: tenant, action: selected.id, via: config.apiBaseUrl, trust: config.webBackendTrust });
      return;
    }
    try {
      const formData = new FormData(form);
      const countryCode = formCountryCode(form);
      const query = new URLSearchParams();
      const body = { tenant_id: tenant };
      query.set('tenant_id', tenant);
      for (const field of fields) {
        if (field.type === 'file') {
          const file = form.querySelector(`[name="${field.name}"]`)?.files?.[0];
          if (!file) continue;
          body.filename = file.name;
          body.media_type = file.type;
          body.content_base64 = await readFileAsBase64(file);
          continue;
        }
        const normalized = normalizeFieldValue(field, formData.get(field.name), { countryCode });
        if (normalized === undefined) continue;
        if (selected.method === 'GET') query.append(field.name, typeof normalized === 'string' ? normalized : JSON.stringify(normalized));
        else body[field.name] = normalized;
      }
      const apiBase = String(config.apiBaseUrl || '/api').replace(/\/$/, '');
      const requestUrl = selected.method === 'GET' ? `${apiBase}${selected.path}?${query}` : `${apiBase}${selected.path}`;
      const response = await fetch(requestUrl, {
        method: selected.method,
        credentials: 'same-origin',
        headers: selected.method === 'GET'
          ? { Accept: selected.download ? '*/*' : 'application/json' }
          : { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: selected.method === 'GET' ? undefined : JSON.stringify(body),
      });
      if (selected.download) {
        const blob = await response.blob();
        if (!response.ok) throw new Error(await blob.text() || `HTTP ${response.status}`);
        const disposition = response.headers.get('content-disposition') || '';
        const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || 'openinfra-graph-export.bin';
        const objectUrl = URL.createObjectURL(blob);
        try {
          const anchor = document.createElement('a');
          anchor.href = objectUrl;
          anchor.download = filename;
          anchor.hidden = true;
          document.body.append(anchor);
          anchor.click();
          anchor.remove();
        } finally {
          URL.revokeObjectURL(objectUrl);
        }
        setResult({ downloaded: true, filename, content_type: blob.type || response.headers.get('content-type'), size_bytes: blob.size });
      } else {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || JSON.stringify(payload));
        setResult(payload);
      }
      setShouldFocusMain(true);
    } catch (error) {
      setResult({ error: error.message });
      setShouldFocusMain(true);
    }
  }

  const displayedVersion = version?.version || config.version || i18n.t('unavailable');
  const filteredModules = MODULES;
  const submissionCompleted = result !== null;
  const protectedForms = bffStatus?.protectedForms === 'enabled' ? i18n.t('active') : i18n.t('configure');
  const activeModule = MODULES.find((module) => module.id === activeModuleId) || MODULES[0];
  const pageTitle = activeModuleId === 'overview' ? 'Dashboard' : activeModule.shortLabel || activeModule.label;
  const pageSubtitle = activeModuleId === 'overview'
    ? i18n.t('dashboardSubtitle')
    : i18n.t('operationSubtitle', { operation: selected.label });

  const megaMenuModule = MODULES.find((module) => module.id === megaMenuModuleId) || null;
  const runtimeStatus = <div className="px-2 small text-muted openinfra-runtime-status" role="status" aria-live="polite" aria-atomic="true">
    <p><span className={`openinfra-status-dot ${ready?.ready === true ? 'ready' : 'warning'}`} />{ready?.ready === true ? i18n.t('backendReady') : i18n.t('backendCheck')}</p>
    <p>{i18n.t('version')} : <strong>{displayedVersion}</strong></p>
    <p>Trust web/backend : <strong>{config.webBackendTrust || 'server-side'}</strong></p>
    <p>{i18n.t('protectedForms')} : <strong>{protectedForms}</strong></p>
  </div>;

  return <div className="openinfra-shell">
    <div className="openinfra-skip-links" aria-label={i18n.t('accessibilityStatus')}>
      <a className="openinfra-skip-link" href="#openinfra-main-content">{i18n.t('skipToContent')}</a>
      <a className="openinfra-skip-link" href="#openinfra-component-navigation">{i18n.t('skipToNavigation')}</a>
      <a className="openinfra-skip-link" href="#openinfra-global-search">{i18n.t('skipToSearch')}</a>
    </div>
    <div key={announcement.id} className="openinfra-live-region" role="status" aria-live="polite" aria-atomic="true">{announcement.text}</div>
    <header className="openinfra-header-stack" role="banner">
      <div className="px-3 py-2 bg-dark text-white openinfra-top-header">
        <div className="container-fluid">
          <div className="d-flex align-items-center openinfra-top-header-inner">
            <a href="/" className="d-flex align-items-center openinfra-brand-link text-white text-decoration-none" aria-label={i18n.t('home')}>
              <span className="openinfra-brand-mark me-2">OI</span>
              <span className="fs-5 fw-semibold openinfra-brand-name">OpenInfra</span>
              <span className="badge openinfra-edition-badge ms-3">{config.edition || 'runtime'}</span>
            </a>
            <nav id="openinfra-component-navigation" className="openinfra-component-navigation" aria-label={i18n.t('navigation')} aria-describedby="openinfra-component-navigation-instructions">
              <p id="openinfra-component-navigation-instructions" className="openinfra-component-navigation-instructions">{i18n.t('componentNavigationInstructions')}</p>
              <ul className="nav justify-content-center text-small openinfra-component-nav">
                {MODULES.map((module, index) => <li key={module.id}><button id={`openinfra-component-${module.id}`} data-component-index={index} type="button" className={`nav-link border-0 bg-transparent openinfra-component-link ${activeNavigationModuleId === module.id ? 'active' : ''}`} aria-current={activeNavigationModuleId === module.id ? 'page' : undefined} aria-haspopup={module.id === 'overview' ? undefined : 'true'} aria-expanded={module.id === 'overview' ? undefined : megaMenuModuleId === module.id} aria-controls={module.id === 'overview' ? undefined : 'openinfra-mega-menu'} onMouseEnter={(event) => openMegaMenu(module, event.currentTarget)} onFocus={(event) => openMegaMenu(module, event.currentTarget)} onKeyDown={(event) => handleComponentNavigationKeyDown(event, index, module)} onClick={(event) => { lastComponentTriggerRef.current = event.currentTarget; handleModuleNavigation(module); }}><Icon name={module.icon} className="bi d-block mx-auto mb-1 openinfra-top-icon" /><span>{module.shortLabel || module.label}</span></button></li>)}
              </ul>
            </nav>
            <button type="button" id="openinfra-compact-menu-button" className="btn btn-primary openinfra-compact-menu-button" aria-label={i18n.t(mobileSidebarOpen ? 'closeNavigation' : 'openNavigation')} aria-expanded={mobileSidebarOpen} aria-controls="openinfra-compact-navigation" onClick={() => { setMegaMenuModuleId(null); setMobileSidebarOpen((open) => !open); }}><Icon name="menu" className="openinfra-mobile-menu-icon" /><span className="visually-hidden">Menu</span></button>
          </div>
        </div>
      </div>
      <div className="px-3 py-2 border-bottom openinfra-global-toolbar">
        <div className="container-fluid openinfra-global-toolbar-inner">
          <div className="openinfra-global-toolbar-spacer" aria-hidden="true" />
          <form className="openinfra-global-search-form" role="search" aria-label={i18n.t('globalSearch')} autoComplete="off">
            <label className="visually-hidden" htmlFor="openinfra-global-search">{i18n.t('globalSearch')}</label>
            <div className="openinfra-global-search-control"><Icon name="search" className="openinfra-global-search-icon" /><input type="search" id="openinfra-global-search" className="form-control" placeholder={i18n.t('globalSearchPlaceholder')} aria-label={i18n.t('globalSearch')} role="combobox" aria-autocomplete="list" aria-haspopup="listbox" aria-controls="openinfra-global-search-results" aria-expanded={globalSearchQuery.trim() !== ''} value={globalSearchQuery} onChange={(event) => setGlobalSearchQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') setGlobalSearchQuery(''); }} /></div>
            {globalSearchQuery.trim() !== '' && <div id="openinfra-global-search-results" className="openinfra-global-search-results" role="listbox" aria-label={i18n.t('globalSearchResults')} aria-live="polite" aria-atomic="false" aria-busy={globalSearchLoading}><GlobalSearchResults i18n={i18n} query={globalSearchQuery} groups={searchGroups} backend={globalSearchBackend} loading={globalSearchLoading} error={globalSearchError} onSelect={selectSearchOperation} onBackendSelect={selectBackendSearchItem} /></div>}
          </form>
          <div className="openinfra-toolbar-actions">
            <div className="openinfra-language-control"><label className="visually-hidden" htmlFor="openinfra-language">{i18n.t('language')}</label><select id="openinfra-language" className="form-select form-select-sm" aria-label={i18n.t('language')} value={language} onChange={(event) => changeLanguage(event.target.value)}><option value="en">EN</option><option value="fr">FR</option></select></div>
            <div className="text-end openinfra-api-doc-actions"><a className="btn btn-light text-dark" href={apiDocs.swaggerUrl} target="_blank" rel="noopener noreferrer" aria-label={`${i18n.t('openSwagger')} — ${i18n.t('opensNewWindow')}`}>Swagger</a><a className="btn btn-primary" href={apiDocs.redocUrl} target="_blank" rel="noopener noreferrer" aria-label={`${i18n.t('openRedoc')} — ${i18n.t('opensNewWindow')}`}>ReDoc</a></div>
          </div>
        </div>
      </div>
      <MegaMenu module={megaMenuModule} selectedOperationId={selected.id} chooseOperation={chooseOperation} close={closeResponsiveNavigation} i18n={i18n} />
      {mobileSidebarOpen && <nav id="openinfra-compact-navigation" className="openinfra-compact-navigation" aria-label={i18n.t('navigation')}>
        <div className="openinfra-compact-navigation-header"><strong>{i18n.t('navigation')}</strong><button type="button" className="openinfra-navigation-close" aria-label={i18n.t('closeNavigation')} onClick={() => closeResponsiveNavigation({ restoreFocus: true })}>×</button></div>
        <div className="openinfra-compact-navigation-body"><div className="openinfra-sidebar-heading">{i18n.t('control')}</div><NavigationTree modules={filteredModules} activeNavigationModuleId={activeNavigationModuleId} selectedOperationId={selected.id} opened={opened} openedContexts={openedContexts} chooseOperation={chooseOperation} toggleAccordion={toggleAccordion} toggleSidebarContext={toggleSidebarContext} surface="compact" /><div className="openinfra-sidebar-heading">{i18n.t('runtimeStatus')}</div>{runtimeStatus}</div>
      </nav>}
    </header>
    {(mobileSidebarOpen || megaMenuModuleId) && <button type="button" className="openinfra-navigation-backdrop" aria-label={i18n.t('closeNavigation')} onClick={() => closeResponsiveNavigation({ restoreFocus: true })} />}
    <div className="container-fluid">
      <div className="row">
        <nav id="openinfra-sidebar" className="col-xl-2 openinfra-sidebar" aria-label={i18n.t('navigation')}>
          <div className="openinfra-sidebar-heading">{i18n.t('control')}</div>
          <NavigationTree modules={filteredModules} activeNavigationModuleId={activeNavigationModuleId} selectedOperationId={selected.id} opened={opened} openedContexts={openedContexts} chooseOperation={chooseOperation} toggleAccordion={toggleAccordion} toggleSidebarContext={toggleSidebarContext} />
          <div className="openinfra-sidebar-heading">{i18n.t('runtimeStatus')}</div>
          {runtimeStatus}
        </nav>
        <main id="openinfra-main-content" ref={mainContentRef} tabIndex={-1} className="col-xl-10 ms-sm-auto openinfra-main">
          <div className="pb-2 mb-3 openinfra-titlebar"><h1 className="h2">{pageTitle}</h1><p className="text-muted mb-0">{pageSubtitle}</p></div>
          {submissionCompleted && activeModuleId !== 'overview' && <div className="alert alert-success" role="status">{i18n.t('success')}</div>}
          {activeModuleId === 'overview' && <div className="row g-3 mb-4 openinfra-dashboard-metrics" aria-label={i18n.t('componentStatistics')}><Metric title={i18n.t('version')} value={displayedVersion} /><Metric title="API" value={config.apiBaseUrl || '/api'} /><Metric title={i18n.t('trust')} value={config.webBackendTrust || 'server-side'} /><Metric title={i18n.t('forms')} value={protectedForms} /><Metric title={i18n.t('modules')} value={`${operationsCount} ${i18n.t('operations')}`} /></div>}
          {activeModuleId === 'overview' ? <OverviewStats i18n={i18n} modules={businessModules} fieldsCount={businessFieldsCount} /> : <section className="card openinfra-operation-card" aria-labelledby="openinfra-operation-title"><div className="card-body"><h2 id="openinfra-operation-title" className="h4">{selected.label}</h2><OperationForm i18n={i18n} language={language} selected={selected} tenant={tenant} setTenant={setTenant} execute={execute} /><GraphResultPanel i18n={i18n} operation={selected} result={result} /></div></section>}
        </main>
      </div>
    </div>
  </div>;
}

function GraphResultPanel({ i18n, operation, result }) {
  const serialized = result === null ? i18n.t('pendingResult') : (typeof result === 'string' ? result : JSON.stringify(result, null, 2));
  if (!operation.id.startsWith('graph-') || result === null || typeof result === 'string' || result.error) {
    return <pre className="openinfra-result mt-3" role="status" aria-live="polite" aria-atomic="true" aria-label={i18n.t('operationResult')}>{serialized}</pre>;
  }
  if (operation.id === 'graph-export') {
    return <><div className="alert alert-success openinfra-download-result mt-3" role="status"><strong>{i18n.t('downloadReady')}</strong><br />{result.filename} · {result.size_bytes || 0} octets</div><RawGraphResult i18n={i18n} value={serialized} /></>;
  }
  return <div className="mt-3">{operation.id === 'graph-spof' ? <SpofRanking i18n={i18n} result={result} /> : <DependencyGraphVisualization i18n={i18n} result={result} />}<RawGraphResult i18n={i18n} value={serialized} /></div>;
}

function RawGraphResult({ i18n, value }) {
  return <details className="openinfra-raw-result"><summary>{i18n.t('rawResult')}</summary><pre className="openinfra-result" role="status" aria-live="polite" aria-atomic="true" aria-label={i18n.t('operationResult')}>{value}</pre></details>;
}

function DependencyGraphVisualization({ i18n, result }) {
  const nodes = Array.isArray(result.nodes) ? result.nodes.slice(0, 80) : [];
  const keys = new Set(nodes.map((node) => String(node.key || '')));
  const edges = (Array.isArray(result.edges) ? result.edges : []).filter((edge) => keys.has(String(edge.source_key || '')) && keys.has(String(edge.target_key || ''))).slice(0, 160);
  if (nodes.length === 0) return <p className="text-muted">{i18n.t('noGraphData')}</p>;
  const layers = new Map();
  for (const node of nodes) {
    const depth = Number.isFinite(Number(node.depth)) ? Number(node.depth) : 0;
    if (!layers.has(depth)) layers.set(depth, []);
    layers.get(depth).push(node);
  }
  const depths = [...layers.keys()].sort((left, right) => left - right);
  const layerGap = Math.max(145, Math.floor(720 / Math.max(depths.length, 1)));
  const positions = new Map();
  depths.forEach((depth, layerIndex) => {
    const layer = layers.get(depth).sort((left, right) => String(left.key).localeCompare(String(right.key)));
    layer.forEach((node, rowIndex) => positions.set(String(node.key), { x: 70 + layerIndex * layerGap, y: 46 + rowIndex * 76 }));
  });
  const maxLayer = Math.max(...[...layers.values()].map((layer) => layer.length), 1);
  const width = Math.max(720, 120 + (depths.length - 1) * layerGap);
  const height = Math.max(280, maxLayer * 76 + 56);
  const omitted = (Array.isArray(result.nodes) ? result.nodes.length : 0) - nodes.length;
  // A scrollable graph region must be keyboard-focusable; a text-equivalent list follows it.
  // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
  return <section className="openinfra-graph-visualization" aria-labelledby="openinfra-react-graph-title"><h3 id="openinfra-react-graph-title" className="h6">{i18n.t('graphVisualization')}</h3><p className="small text-muted">{i18n.t('graphVisualizationDescription')}</p><div className="openinfra-graph-canvas" role="region" aria-label={i18n.t('graphVisualization')} tabIndex={0}><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${nodes.length} nodes, ${edges.length} relationships`}><defs><marker id="openinfra-react-graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" /></marker></defs><g className="openinfra-graph-edges">{edges.map((edge) => { const source = positions.get(String(edge.source_key)); const target = positions.get(String(edge.target_key)); return source && target ? <line key={edge.id || `${edge.source_key}-${edge.target_key}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} markerEnd="url(#openinfra-react-graph-arrow)"><title>{`${edge.relation_type || 'relation'}: ${edge.source_key} → ${edge.target_key}`}</title></line> : null; })}</g><g className="openinfra-graph-nodes" role="list">{nodes.map((node) => { const position = positions.get(String(node.key)); const label = String(node.display_name || node.key || ''); const shortLabel = label.length > 16 ? `${label.slice(0, 15)}…` : label; const isRoot = String(node.key) === String(result.root_key || result.source_key || ''); return <g key={node.key} className={`openinfra-graph-node${isRoot ? ' is-root' : ''}`} transform={`translate(${position.x},${position.y})`} role="listitem" aria-label={`${label}, ${node.resource_type || node.kind || 'object'}, depth ${node.depth ?? 0}`}><circle r="24" /><text textAnchor="middle" y="4">{shortLabel}</text><title>{`${label} (${node.key})`}</title></g>; })}</g></svg></div><ul className="visually-hidden" aria-label={i18n.t('graphVisualization')}>{nodes.map((node) => <li key={`accessible-${node.key}`}>{`${node.display_name || node.key}, ${node.resource_type || node.kind || 'object'}, depth ${node.depth ?? 0}`}</li>)}</ul>{omitted > 0 ? <p className="small text-muted">{i18n.t('graphNodesOmitted', { count: omitted })}</p> : null}</section>;
}

function SpofRanking({ i18n, result }) {
  const items = Array.isArray(result.items) ? result.items : [];
  return <section className="openinfra-spof-ranking" aria-labelledby="openinfra-react-spof-title"><div className="d-flex flex-wrap justify-content-between gap-2"><h3 id="openinfra-react-spof-title" className="h6">{i18n.t('spofRanking')}</h3><span className={`badge ${result.complete === false ? 'text-bg-warning' : 'text-bg-success'}`}>{i18n.t(result.complete === false ? 'boundedAnalysis' : 'completeAnalysis')}</span></div><p className="small text-muted">{`${result.spof_count || 0} SPOF · ${result.node_count || 0} nodes · ${result.edge_count || 0} relationships`}</p><div className="table-responsive"><table className="table table-sm align-middle"><caption className="visually-hidden">{i18n.t('spofRanking')}</caption><thead><tr><th scope="col">#</th><th scope="col">{i18n.t('candidate')}</th><th scope="col">{i18n.t('affectedNodes')}</th><th scope="col">{i18n.t('directAffected')}</th><th scope="col">{i18n.t('impactRatio')}</th><th scope="col">{i18n.t('affectedSample')}</th></tr></thead><tbody>{items.length === 0 ? <tr><td colSpan="6">{i18n.t('noSpofDetected')}</td></tr> : items.map((item) => { const node = item.node || {}; const ratio = Math.max(0, Math.min(1, Number(item.affected_ratio || 0))); return <tr key={node.key || item.rank}><td>{item.rank}</td><th scope="row">{node.display_name || node.key}<small>{node.key}</small></th><td>{item.affected_count}</td><td>{item.direct_affected_count}</td><td><span className="openinfra-spof-ratio" aria-label={`${Math.round(ratio * 100)} %`}><span style={{ width: `${Math.round(ratio * 100)}%` }} /></span>{Math.round(ratio * 100)} %</td><td>{Array.isArray(item.affected_sample) && item.affected_sample.length > 0 ? item.affected_sample.join(', ') : '—'}</td></tr>; })}</tbody></table></div></section>;
}

function GlobalSearchResults({ i18n, query, groups, backend, loading, error, onSelect, onBackendSelect }) {
  if (loading) {
    return <div className="openinfra-global-search-empty">{i18n.t('loadingSearch', { query: query.trim() })}</div>;
  }
  if (backend && backend.query === query.trim()) {
    const resultGroups = (backend.groups || []).filter((group) => group.status === 'ok' && Array.isArray(group.items) && group.items.length > 0);
    const skipped = (backend.groups || []).filter((group) => group.status === 'skipped');
    if (resultGroups.length > 0) {
      return <>{resultGroups.map((group) => <section className="openinfra-global-search-group" role="group" aria-label={`${i18n.t('globalSearchResults')} ${group.label || group.component}`} key={group.component}><div className="openinfra-global-search-group-title"><span>{group.label || group.component}</span><span>{i18n.count(group.total, 'result', 'results')}</span></div>{group.items.length > 40 ? <VirtualizedList items={group.items} ariaLabel={`${i18n.t('globalSearchResults')} ${group.label || group.component}`} renderItem={(item) => <button type="button" className="openinfra-global-search-item" role="option" aria-selected="false" onClick={() => onBackendSelect(item)}><span>{item.label}</span><small>{item.kind} · {item.description}</small></button>} /> : group.items.map((item) => <button type="button" className="openinfra-global-search-item" role="option" aria-selected="false" key={`${group.component}-${item.kind}-${item.label}`} onClick={() => onBackendSelect(item)}><span>{item.label}</span><small>{item.kind} · {item.description}</small></button>)}{group.total > group.items.length && <div className="openinfra-global-search-more">{i18n.t(group.total - group.items.length === 1 ? 'additionalResults' : 'additionalResultsPlural', { count: group.total - group.items.length })}</div>}</section>)}{skipped.length > 0 && <div className="openinfra-global-search-empty">{i18n.t('skippedComponents', { components: skipped.map((group) => group.label || group.component).join(', ') })}</div>}</>;
    }
  }
  if (error) {
    return <><div className="openinfra-global-search-empty">{i18n.t('backendSearchUnavailable')}</div><OperationSearchResults i18n={i18n} query={query} groups={groups} onSelect={onSelect} /></>;
  }
  return <OperationSearchResults i18n={i18n} query={query} groups={groups} onSelect={onSelect} />;
}

function OperationSearchResults({ i18n, query, groups, onSelect }) {
  if (groups.length === 0) {
    return <div className="openinfra-global-search-empty">{i18n.t('noGlobalResult', { query: query.trim() })}</div>;
  }
  return groups.map(({ module, operations, total }) => <section className="openinfra-global-search-group" role="group" aria-label={`${i18n.t('globalSearchResults')} ${module.shortLabel || module.label}`} key={module.id}><div className="openinfra-global-search-group-title"><span>{module.shortLabel || module.label}</span><span>{i18n.count(total, 'result', 'results')}</span></div>{operations.map((operation) => <button type="button" className="openinfra-global-search-item" role="option" aria-selected="false" key={operation.id} onClick={() => onSelect(module, operation)}><span>{operation.label}</span><small>{operation.method} {operation.path}</small></button>)}{total > operations.length && <div className="openinfra-global-search-more">{i18n.t(total - operations.length === 1 ? 'additionalResults' : 'additionalResultsPlural', { count: total - operations.length })}</div>}</section>);
}

function OverviewStats({ i18n, modules, fieldsCount }) {
  const operations = modules.reduce((total, module) => total + moduleStatistics(module).operations, 0);
  return <section className="openinfra-overview" aria-label={i18n.t('componentStatistics')}><div className="card openinfra-overview-summary mb-4"><div className="card-body"><div className="d-flex flex-wrap justify-content-between align-items-start gap-3"><div><h2 className="h4 mb-1">{i18n.t('overviewTitle')}</h2><p className="text-muted mb-0">{i18n.t('overviewDescription')}</p></div><div><span className="badge text-bg-primary">{modules.length} {i18n.t('components')}</span><span className="badge text-bg-secondary ms-2">{operations} {i18n.t('operations')}</span></div></div><div className="row g-3 mt-3"><Metric title={i18n.t('fields')} value={String(fieldsCount)} /><Metric title={i18n.t('navigationMode')} value={i18n.t('accordions')} /><Metric title={i18n.t('browserSecrets')} value={i18n.t('noneExposed')} /><Metric title={i18n.t('uiParity')} value="CLI/API" /></div></div></div><div className="row g-3">{modules.map((module) => <ComponentStatsCard i18n={i18n} key={module.id} module={module} />)}</div></section>;
}

function ComponentStatsCard({ i18n, module }) {
  const stats = moduleStatistics(module);
  const style = { '--oi-read-end': `${stats.readPercent}%`, '--oi-write-end': `${stats.readPercent + stats.writePercent}%` };
  return <article className="col-md-6 col-xxl-4"><div className="card h-100 openinfra-component-card"><div className="card-body"><div className="d-flex justify-content-between align-items-start gap-3"><div><h3 className="h5 mb-1">{module.shortLabel || module.label}</h3><p className="text-muted small mb-0">{i18n.t('operationsExposed', { count: moduleStatistics(module).operations })}</p></div><Icon name={module.icon} className="openinfra-component-icon" /></div><div className="openinfra-component-visual mt-3"><div className="openinfra-pie-chart" role="img" aria-label={i18n.t('distributionChart', { module: module.label, reads: stats.readOperations, mutations: stats.writeOperations })} style={style}><span>{stats.operations}</span></div><div className="openinfra-pie-legend small"><span><i className="openinfra-legend-read" />{stats.readOperations} {i18n.t('reads').toLowerCase()}</span><span><i className="openinfra-legend-write" />{stats.writeOperations} {i18n.t('mutations').toLowerCase()}</span></div></div><div className="row g-2 mt-3 openinfra-component-metrics"><div className="col-6"><strong>{stats.operations}</strong><span>{i18n.t('operations')}</span></div><div className="col-6"><strong>{stats.fields}</strong><span>{i18n.t('fields')}</span></div><div className="col-6"><strong>{stats.readOperations}</strong><span>{i18n.t('reads')}</span></div><div className="col-6"><strong>{stats.writeOperations}</strong><span>{i18n.t('mutations')}</span></div></div></div></div></article>;
}

function Metric({ title, value }) {
  return <article className="col-md-6 col-xl-3"><div className="card h-100 openinfra-metric"><div className="card-body"><h2 className="h6 text-muted">{title}</h2><p className="openinfra-metric-value mb-0">{value}</p></div></div></article>;
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
