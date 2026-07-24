import 'bootstrap/dist/css/bootstrap.min.css';
import './openinfra-theme.css';
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { OpenInfraI18n, localizeOpenInfraCatalog } from './i18n.js';
import { fileHelpText, formCountryCode, inputAttributesForField, inputTypeForField, normalizeFieldDefinition, normalizeFieldValue, validateControl, validateFileForField } from './form-fields.js';
import { MODULES, SIDEBAR_CONTEXTS, loadDomain } from './domain-manifest.js';
import { OpenInfraQueryCache } from './core/query-cache.js';
import { installOpenInfraWebVitals } from './core/web-vitals.js';
import { VirtualizedList } from './VirtualizedList.jsx';
import {
  collapseManagementOperations,
  localizedManagementLabel,
  managementNavigationOperation,
  managementResourceById,
  managementResourceForOperation,
  flattenManagementCollection,
  managementDisplayName,
  managementFieldValue,
  managementIdentityPayload,
  managementContextLabel,
  managementFilterOptions,
  managementFilterGroups,
  managementItemMatchesFilter,
  normalizeManagementFilters,
  orderManagementContextEntries,
  updateManagementFilters,
} from './management/resources.js';
import { loadManagementOperationSchema } from './management/operation-schema.js';

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

function sidebarOperationGroups(module, language = 'fr') {
  const configuredGroups = SIDEBAR_CONTEXTS[module.id] || [];
  const byId = new Map(module.operations.map((operation) => [operation.id, operation]));
  const groupedIds = new Set();
  const groups = configuredGroups.map((group) => {
    const operationIds = group.operationIds || (group.operationIdPrefix
      ? module.operations.filter((operation) => operation.id.startsWith(group.operationIdPrefix)).map((operation) => operation.id)
      : []);
    const rawOperations = operationIds.map((id) => byId.get(id)).filter(Boolean);
    rawOperations.forEach((operation) => groupedIds.add(operation.id));
    const operations = collapseManagementOperations(module.id, module.operations, operationIds, language);
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

function contextForOperation(module, operationId, language = 'fr') {
  const management = managementResourceForOperation(operationId);
  const effectiveOperationId = management ? `management:${management.resource.id}` : operationId;
  return sidebarOperationGroups(module, language).find((group) => group.operations.some((operation) => operation.id === effectiveOperationId));
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

function isLiveOperationId(operationId) {
  const normalized = String(operationId || '');
  return normalized.startsWith('graph-')
    || normalized.startsWith('field-')
    || normalized.startsWith('simulation-')
    || normalized.startsWith('greenops-')
    || normalized.startsWith('sbom-')
    || normalized.startsWith('rag-')
    || normalized.startsWith('kubernetes-')
    || normalized.startsWith('import-')
    || normalized.startsWith('export-')
    || normalized === 'rsot-as-of'
    || normalized.startsWith('rsot-quality-');
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
  language = 'fr',
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
          {sidebarOperationGroups(module, language).map((group) => {
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

function MegaMenu({ module, selectedOperationId, chooseOperation, close, i18n, language = 'fr' }) {
  if (!module || module.id === 'overview') {
    return null;
  }
  return <section id="openinfra-mega-menu" className="openinfra-mega-menu" aria-label={module.shortLabel || module.label}>
    <div className="openinfra-mega-menu-header"><div><Icon name={module.icon} className="openinfra-mega-menu-icon" /><strong>{module.label}</strong></div><button type="button" className="openinfra-navigation-close" aria-label={i18n.t('closeNavigation')} onClick={close}>×</button></div>
    <div className="openinfra-mega-menu-grid">
      {sidebarOperationGroups(module, language).map((group) => <section className="openinfra-mega-menu-group" role="group" aria-label={group.label} key={`${module.id}-${group.label}`}><h2>{group.label}</h2><div>{group.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selectedOperationId === operation.id ? 'active' : ''}`} aria-current={selectedOperationId === operation.id ? 'page' : undefined} onClick={() => chooseOperation(module, operation, true)}>{operation.label}</button>)}</div></section>)}
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
    return <div className="col-12"><label className="form-label" htmlFor={fieldId}>{i18n.label(field.label)}{requiredText}</label><input id={fieldId} name={field.name} className="form-control" type="file" required={field.required} {...attributes} onChange={(event) => { event.currentTarget.setCustomValidity(''); event.currentTarget.removeAttribute('aria-invalid'); }} /><p className="form-text">{fileHelpText(field)}</p></div>;
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
      const message = validateFileForField(file, field);
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
  const fields = orderManagementContextEntries(selected.fields.map((entry, index) => normalizeFieldDefinition(entry, index)));
  return <form aria-describedby="openinfra-required-fields-notice" noValidate onSubmit={(event) => { event.preventDefault(); if (validateOperationForm(event.currentTarget, fields, i18n)) execute(event.currentTarget, fields); }}><p id="openinfra-required-fields-notice" className="openinfra-required-notice">{i18n.t('requiredFieldsNotice')}</p><div className="row g-3 mb-3"><label className="col-md-4 form-label" htmlFor="openinfra-react-tenant">{i18n.t('organization')}</label><select id="openinfra-react-tenant" className="form-select" value={tenant} onChange={(event) => setTenant(event.target.value)}><option value="default">{i18n.t('defaultTenant')}</option></select></div><div className="row g-3">{fields.map((field, index) => <OperationField entry={field} index={index} i18n={i18n} language={language} key={field.name} />)}</div><button type="submit" className="btn btn-primary mt-3">{i18n.t('execute')}</button></form>;
}

function managementOperationFields(operation) {
  return orderManagementContextEntries([...(operation?.query || []), ...(operation?.body || [])].map((field, index) => normalizeFieldDefinition(field, index)));
}

function assignManagementBodyValue(body, target, value) {
  const parts = String(target || '').split('.').filter(Boolean);
  if (parts.length === 0) return;
  let current = body;
  for (const part of parts.slice(0, -1)) {
    current[part] ||= {};
    current = current[part];
  }
  current[parts.at(-1)] = value;
}

function normalizeManagementRequestValue(field, raw, payload) {
  const value = normalizeFieldValue(field, raw, { countryCode: payload.country_code || payload.country || '' });
  if (value === undefined) return undefined;
  if (field.type === 'boolean') return ['1', 'true', 'yes', 'oui'].includes(String(value).toLowerCase());
  return value;
}

async function requestManagementOperation({ config, tenant, operation, payload }) {
  if (!operation) throw new Error('Operation de gestion indisponible.');
  const apiBase = String(config.apiBaseUrl || '/api').replace(/\/$/u, '');
  const path = String(operation.path || '').replace(/\{([^}]+)\}/gu, (_match, key) => encodeURIComponent(payload[key] ?? ''));
  const tenantScoped = !String(operation.id || '').startsWith('itam-organization');
  const query = new URLSearchParams();
  for (const field of operation.query || []) {
    const value = normalizeManagementRequestValue(field, payload[field.name], payload);
    if (value !== undefined && value !== null && String(value).trim() !== '') query.set(field.name, String(value));
  }
  if (tenantScoped && tenant && !query.has('tenant_id')) query.set('tenant_id', tenant);
  const body = {};
  for (const field of operation.body || []) {
    const value = normalizeManagementRequestValue(field, payload[field.name], payload);
    if (value === undefined || value === null || String(value).trim?.() === '') {
      if (field.required) throw new Error(`Champ obligatoire manquant : ${field.label || field.name}`);
      continue;
    }
    assignManagementBodyValue(body, field.target || field.name, value);
  }
  if (tenantScoped && tenant && operation.method !== 'GET' && !Object.prototype.hasOwnProperty.call(body, 'tenant_id')) body.tenant_id = tenant;
  const suffix = query.toString() ? `?${query.toString()}` : '';
  const response = await fetch(`${apiBase}${path}${suffix}`, {
    method: operation.method,
    credentials: 'same-origin',
    headers: operation.method === 'GET' ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: operation.method === 'GET' ? undefined : JSON.stringify(body),
  });
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(typeof data === 'string' ? data : (data.error || JSON.stringify(data)));
  return data;
}

function ManagementWorkspace({ resource, config, tenant, i18n, language, announce }) {
  const [mode, setMode] = useState('list');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({});
  const [includeRetired, setIncludeRetired] = useState(false);
  const [sort, setSort] = useState({ key: resource.columns[0]?.key || '', direction: 'asc' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [selectedItem, setSelectedItem] = useState(null);
  const [detailItem, setDetailItem] = useState(null);
  const [deleteItem, setDeleteItem] = useState(null);
  const [actionOperation, setActionOperation] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const deleteActorRef = useRef(null);

  const label = localizedManagementLabel(resource, language);
  const singular = localizedManagementLabel(resource, language, 'singular');

  async function loadItems() {
    setLoading(true);
    setError(null);
    try {
      const operationId = resource.sourceOperationId || resource.operations.list;
      const operation = await loadManagementOperationSchema(resource.moduleId, operationId);
      const payload = await requestManagementOperation({ config, tenant, operation, payload: { include_retired: includeRetired } });
      setItems(flattenManagementCollection(resource, payload, { tenant_id: tenant }));
      setPage(1);
    } catch (loadError) {
      setItems([]);
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadItems(); }, [resource.id, tenant, includeRetired]);

  useEffect(() => {
    setFilters((current) => normalizeManagementFilters(current, resource.filters, items));
  }, [items, resource.filters]);

  useEffect(() => {
    if (deleteItem) window.requestAnimationFrame(() => deleteActorRef.current?.focus({ preventScroll: true }));
  }, [deleteItem]);

  useEffect(() => {
    const closeDialog = (event) => {
      if (event.key !== 'Escape') return;
      if (deleteItem) setDeleteItem(null);
      else if (detailItem) setDetailItem(null);
    };
    document.addEventListener('keydown', closeDialog);
    return () => document.removeEventListener('keydown', closeDialog);
  }, [deleteItem, detailItem]);

  const filterOptions = useMemo(() => managementFilterOptions(items, filters, resource.filters, language), [filters, items, language, resource.filters]);
  const filterGroups = useMemo(() => managementFilterGroups(resource.filters), [resource.filters]);
  const filteredItems = useMemo(() => {
    const normalizedQuery = normalizeSearchText(query.trim());
    const resultItems = items.filter((item) => {
      if (normalizedQuery && !normalizeSearchText(Object.values(item || {}).map((value) => typeof value === 'object' ? JSON.stringify(value) : String(value ?? '')).join(' ')).includes(normalizedQuery)) return false;
      return resource.filters.every(({ key }) => managementItemMatchesFilter(item, key, filters[key]));
    });
    if (!sort.key) return resultItems;
    return [...resultItems].sort((left, right) => {
      const comparison = managementFieldValue(left, sort.key).localeCompare(managementFieldValue(right, sort.key), language, { numeric: true, sensitivity: 'base' });
      return sort.direction === 'desc' ? -comparison : comparison;
    });
  }, [filters, items, language, query, resource.filters, sort]);
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filteredItems.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  async function openAction(nextMode, item = null) {
    const role = nextMode === 'create' ? 'create' : 'update';
    const operation = await loadManagementOperationSchema(resource.moduleId, resource.operations[role]);
    if (!operation) {
      setError(i18n.t('managementUnavailable'));
      return;
    }
    setActionOperation(operation);
    setSelectedItem(item);
    setNotice(null);
    setMode(nextMode);
  }

  function managementFieldEntries() {
    if (!actionOperation) return [];
    return managementOperationFields(actionOperation).map((field) => ({ ...field, defaultValue: selectedItem?.[field.name] ?? field.defaultValue ?? '' }));
  }

  async function submitManagementForm(event) {
    event.preventDefault();
    if (!actionOperation) return;
    const fields = managementFieldEntries();
    if (!validateOperationForm(event.currentTarget, fields, i18n)) return;
    setSubmitting(true);
    setError(null);
    try {
      const formData = new FormData(event.currentTarget);
      const payload = Object.fromEntries(fields.map((field) => [field.name, formData.get(field.name)]));
      await requestManagementOperation({ config, tenant, operation: actionOperation, payload });
      setNotice(i18n.t(mode === 'create' ? 'managementCreated' : 'managementUpdated', { item: managementDisplayName(resource, selectedItem || payload) }));
      setMode('list');
      setSelectedItem(null);
      setActionOperation(null);
      await loadItems();
      announce(i18n.t('success'));
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function submitDelete(event) {
    event.preventDefault();
    if (!deleteItem) return;
    setSubmitting(true);
    setError(null);
    try {
      const operation = await loadManagementOperationSchema(resource.moduleId, resource.operations.delete);
      const formData = new FormData(event.currentTarget);
      const payload = { ...managementIdentityPayload(resource, deleteItem), actor: formData.get('actor') };
      await requestManagementOperation({ config, tenant, operation, payload });
      setNotice(i18n.t('managementDeleted', { item: managementDisplayName(resource, deleteItem) }));
      setDeleteItem(null);
      await loadItems();
      announce(i18n.t('success'));
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setSubmitting(false);
    }
  }

  function renderManagementFilter(definition) {
    const options = filterOptions[definition.key] || [];
    const selected = String(filters[definition.key] || '');
    const renderedOptions = selected && !options.includes(selected) ? [selected, ...options] : options;
    const unavailable = renderedOptions.length === 0;
    return <div className="openinfra-management-filter-control" key={definition.key}>
      <label className="form-label" htmlFor={`management-filter-${resource.id}-${definition.key}`}>{managementContextLabel(definition.key, language) || definition.label}</label>
      <select id={`management-filter-${resource.id}-${definition.key}`} className="form-select" value={selected} disabled={unavailable} aria-disabled={unavailable} onChange={(event) => { setFilters((current) => updateManagementFilters(current, resource.filters, definition.key, event.target.value)); setPage(1); }}>
        <option value="">{unavailable ? i18n.t('managementNoFilterValues') : i18n.t('allValues')}</option>
        {renderedOptions.map((value) => <option value={value} key={value}>{value}</option>)}
      </select>
    </div>;
  }

  if (mode === 'create' || mode === 'edit') {
    const fields = managementFieldEntries();
    const immutableFields = new Set(mode === 'edit' ? resource.immutable : []);
    const visibleFields = fields.filter((field) => !immutableFields.has(field.name));
    return <section className="card openinfra-operation-card openinfra-management-card" aria-labelledby="openinfra-management-form-title"><div className="card-body"><div className="openinfra-management-heading"><div><p className="openinfra-management-kicker">{label}</p><h2 id="openinfra-management-form-title" className="h4">{i18n.t(mode === 'create' ? 'createManagementItem' : 'editManagementItem', { item: singular })}</h2><p className="text-muted mb-0">{i18n.t(mode === 'create' ? 'createManagementDescription' : 'editManagementDescription')}</p></div><button type="button" className="btn btn-light" onClick={() => { setMode('list'); setSelectedItem(null); setActionOperation(null); }}>{i18n.t('backToManagement')}</button></div>{error && <div className="alert alert-danger mt-3" role="alert">{error}</div>}{mode === 'edit' && selectedItem && <dl className="openinfra-management-identity mt-3">{resource.identity.map((key) => <div key={key}><dt>{key}</dt><dd>{managementFieldValue(selectedItem, key) || '—'}</dd></div>)}</dl>}<form className="mt-3" noValidate onSubmit={submitManagementForm}><p className="openinfra-required-notice">{i18n.t('requiredFieldsNotice')}</p>{fields.filter((field) => immutableFields.has(field.name)).map((field) => <input key={field.name} type="hidden" name={field.name} value={selectedItem?.[field.name] ?? ''} readOnly />)}<div className="row g-3">{visibleFields.map((field, index) => <OperationField entry={field} index={index} i18n={i18n} language={language} key={field.name} />)}</div><div className="openinfra-management-form-actions"><button type="submit" className="btn btn-primary" disabled={submitting}>{mode === 'create' ? i18n.t('create') : i18n.t('saveChanges')}</button><button type="button" className="btn btn-light" onClick={() => { setMode('list'); setSelectedItem(null); setActionOperation(null); }}>{i18n.t('cancel')}</button></div></form></div></section>;
  }

  return <section className="card openinfra-operation-card openinfra-management-card" aria-labelledby="openinfra-management-title"><div className="card-body"><div className="openinfra-management-heading"><div><p className="openinfra-management-kicker">{i18n.t('managementWorkspace')}</p><h2 id="openinfra-management-title" className="h4">{label}</h2><p className="text-muted mb-0">{i18n.t('managementDescription', { resource: localizedManagementLabel(resource, language, 'plural') })}</p></div><button type="button" className="btn btn-primary" onClick={() => void openAction('create')}>+ {i18n.t('newItem')}</button></div>{notice && <div className="alert alert-success mt-3" role="status">{notice}</div>}{error && <div className="alert alert-danger mt-3" role="alert">{error}</div>}<form className="openinfra-management-filter-panel mt-3" role="search" aria-labelledby={`management-filter-title-${resource.id}`} onSubmit={(event) => { event.preventDefault(); setPage(1); }}><div className="openinfra-management-filter-header"><div><p className="openinfra-management-filter-kicker">{i18n.t('managementFilters')}</p><h3 id={`management-filter-title-${resource.id}`} className="h5 mb-1">{i18n.t('managementFilterTitle')}</h3><p className="text-muted mb-0">{i18n.t('managementFilterDescription')}</p></div></div><div className="openinfra-management-search-block"><label className="form-label" htmlFor={`management-search-${resource.id}`}>{i18n.t('search')}</label><input id={`management-search-${resource.id}`} type="search" className="form-control" value={query} placeholder={i18n.t('managementSearchPlaceholder')} onChange={(event) => { setQuery(event.target.value); setPage(1); }} /></div>{filterGroups.context.length > 0 && <fieldset className="openinfra-management-filter-section"><legend>{i18n.t('managementContextFilters')}</legend><div className="openinfra-management-filter-grid">{filterGroups.context.map(renderManagementFilter)}</div></fieldset>}{filterGroups.business.length > 0 && <fieldset className="openinfra-management-filter-section"><legend>{i18n.t('managementBusinessFilters')}</legend><div className="openinfra-management-filter-grid">{filterGroups.business.map(renderManagementFilter)}</div></fieldset>}<div className="openinfra-management-filter-actions"><div className="form-check openinfra-management-retired"><input id={`management-retired-${resource.id}`} className="form-check-input" type="checkbox" checked={includeRetired} onChange={(event) => setIncludeRetired(event.target.checked)} /><label className="form-check-label" htmlFor={`management-retired-${resource.id}`}>{i18n.t('includeRetired')}</label></div><div className="openinfra-management-filter-buttons"><button type="submit" className="btn btn-primary">{i18n.t('applyFilters')}</button><button type="button" className="btn btn-light" onClick={() => { setQuery(''); setFilters({}); setPage(1); }}>{i18n.t('resetFilters')}</button></div></div></form><div className="openinfra-management-table-summary"><span>{i18n.t('managementResults', { count: filteredItems.length })}</span><label>{i18n.t('rowsPerPage')} <select className="form-select form-select-sm" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }}>{[25, 50, 100].map((size) => <option value={size} key={size}>{size}</option>)}</select></label></div>{loading ? <p role="status">{i18n.t('loadingManagementData')}</p> : <div className="openinfra-management-table-wrapper"><table className="table align-middle openinfra-management-table"><caption className="visually-hidden">{label}</caption><thead><tr>{resource.columns.map((column) => <th scope="col" key={column.key}><button type="button" className="openinfra-management-sort" onClick={() => setSort((current) => ({ key: column.key, direction: current.key === column.key && current.direction === 'asc' ? 'desc' : 'asc' }))}>{column.label}{sort.key === column.key ? (sort.direction === 'asc' ? ' ↑' : ' ↓') : ''}</button></th>)}<th scope="col">{i18n.t('actions')}</th></tr></thead><tbody>{pageItems.length === 0 ? <tr><td colSpan={resource.columns.length + 1}>{i18n.t('noManagementResults')}</td></tr> : pageItems.map((item) => { const key = JSON.stringify(managementIdentityPayload(resource, item)); return <tr key={key}>{resource.columns.map((column, index) => <td key={column.key}>{index === 0 ? <button type="button" className="openinfra-management-detail-link" onClick={() => setDetailItem(item)}>{managementFieldValue(item, column.key) || '—'}</button> : (managementFieldValue(item, column.key) || '—')}</td>)}<td><div className="openinfra-management-actions"><button type="button" className="btn btn-sm btn-light" onClick={() => void openAction('edit', item)}>{i18n.t('edit')}</button><button type="button" className="btn btn-sm btn-outline-danger" onClick={() => setDeleteItem(item)}>{i18n.t('delete')}</button></div></td></tr>; })}</tbody></table></div>}<div className="openinfra-management-pagination"><span>{i18n.t('pagination', { page: currentPage, pages: totalPages })}</span><div><button type="button" className="btn btn-sm btn-light" disabled={currentPage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>{i18n.t('previous')}</button><button type="button" className="btn btn-sm btn-light" disabled={currentPage >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>{i18n.t('next')}</button></div></div>{detailItem && <div className="openinfra-management-modal" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setDetailItem(null); }}><section className="openinfra-management-dialog" role="dialog" aria-modal="true" aria-labelledby="openinfra-management-detail-title"><div className="openinfra-management-dialog-header"><h3 id="openinfra-management-detail-title" className="h5">{managementDisplayName(resource, detailItem)}</h3><button type="button" className="btn btn-light" aria-label={i18n.t('close')} onClick={() => setDetailItem(null)}>×</button></div><dl className="openinfra-management-detail-grid">{Object.entries(detailItem).sort(([left], [right]) => left.localeCompare(right)).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value && typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—')}</dd></div>)}</dl></section></div>}{deleteItem && <div className="openinfra-management-modal" role="presentation"><section className="openinfra-management-dialog" role="dialog" aria-modal="true" aria-labelledby="openinfra-management-delete-title"><div className="openinfra-management-dialog-header"><h3 id="openinfra-management-delete-title" className="h5">{i18n.t('confirmDeletion')}</h3><button type="button" className="btn btn-light" aria-label={i18n.t('close')} onClick={() => setDeleteItem(null)}>×</button></div><p>{i18n.t('deleteManagementConfirmation', { item: managementDisplayName(resource, deleteItem) })}</p><p className="text-muted small">{i18n.t('deleteManagementLifecycleNotice')}</p><form onSubmit={submitDelete}><label className="form-label" htmlFor={`management-delete-actor-${resource.id}`}>{i18n.t('operator')}</label><input id={`management-delete-actor-${resource.id}`} name="actor" className="form-control" required ref={deleteActorRef} /><div className="openinfra-management-form-actions"><button type="submit" className="btn btn-danger" disabled={submitting}>{i18n.t('delete')}</button><button type="button" className="btn btn-light" onClick={() => setDeleteItem(null)}>{i18n.t('cancel')}</button></div></form></section></div>}</div></section>;
}

function RuntimeLicenseBanner({ report, failed, i18n }) {
  if (!report && !failed) return null;
  if (failed) {
    return <div className="alert alert-warning openinfra-license-banner" role="alert" aria-live="assertive" aria-atomic="true"><strong>{i18n.t('runtimeLicense')}</strong><span className="ms-2">{i18n.t('licenseUnavailable')}</span></div>;
  }
  const level = String(report.notification_level || 'none');
  if (level === 'none' && ['active', 'not_required'].includes(String(report.status || ''))) return null;
  const alertClass = level === 'critical' ? 'alert-danger' : (level === 'warning' ? 'alert-warning' : 'alert-info');
  const role = level === 'critical' ? 'alert' : 'status';
  const statusKey = `licenseStatus_${String(report.status || 'invalid')}`;
  const hosts = report.max_hosts == null ? String(report.current_hosts || 0) : `${report.current_hosts || 0} / ${report.max_hosts}`;
  return <div className={`alert ${alertClass} openinfra-license-banner`} role={role} aria-live={level === 'critical' ? 'assertive' : 'polite'} aria-atomic="true"><div className="d-flex flex-wrap gap-3 align-items-baseline"><strong>{i18n.t('runtimeLicense')}</strong><span>{i18n.t('licenseStatus')} : <strong>{i18n.t(statusKey)}</strong></span>{report.company_name ? <span>{i18n.t('licenseCompany')} : <strong>{report.company_name}</strong></span> : null}<span>{i18n.t('licenseHosts')} : <strong>{hosts}</strong></span>{report.expires_at ? <span>{i18n.t('licenseExpires')} : <strong>{new Date(report.expires_at).toLocaleDateString()}</strong></span> : null}{report.grace_until && report.status === 'grace' ? <span>{i18n.t('licenseGraceUntil')} : <strong>{new Date(report.grace_until).toLocaleDateString()}</strong></span> : null}</div><p className="mb-0 mt-1 small">{report.reason}</p></div>;
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
  const [licenseReport, setLicenseReport] = useState(null);
  const [licenseStatusFailed, setLicenseStatusFailed] = useState(false);
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

  useEffect(() => {
    const controller = new AbortController();
    const apiBase = String(config.apiBaseUrl || '/api').replace(/\/$/u, '');
    const refreshLicenseStatus = async () => {
      try {
        const response = await fetch(`${apiBase}/v1/license/status`, { credentials: 'same-origin', headers: { Accept: 'application/json' }, signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setLicenseReport(await response.json());
        setLicenseStatusFailed(false);
      } catch (error) {
        if (error?.name !== 'AbortError') {
          setLicenseReport(null);
          setLicenseStatusFailed(true);
        }
      }
    };
    void refreshLicenseStatus();
    const interval = window.setInterval(() => void refreshLicenseStatus(), 3_600_000);
    return () => { controller.abort(); window.clearInterval(interval); };
  }, [config.apiBaseUrl]);

  function chooseOperation(module, operation, focusMain = false) {
    const mappedManagement = managementResourceForOperation(operation.id);
    const eligibleManagement = mappedManagement && ['list', 'create', 'update', 'delete'].every((role) => module.operations.some((candidate) => candidate.id === mappedManagement.resource.operations[role]));
    const effectiveOperation = operation.managementResourceId
      ? operation
      : (eligibleManagement ? managementNavigationOperation(mappedManagement.resource, language) : operation);
    setSelected(effectiveOperation);
    setActiveModuleId(module.id);
    setActiveNavigationModuleId(module.id);
    setOpened((current) => module.id === 'overview' ? new Set() : new Set([...current, module.id]));
    setOpenedContexts((current) => {
      if (module.id === 'overview') {
        return new Set();
      }
      const next = withoutModuleContexts(current, module.id);
      const context = contextForOperation(module, effectiveOperation.id, language);
      if (context) {
        next.add(sidebarContextKey(module.id, context.label));
      }
      return next;
    });
    setResult(null);
    announce(i18n.t('operationSelected', { operation: effectiveOperation.label }));
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
    if (!isLiveOperationId(selected.id)) {
      setResult({ tenant_id: tenant, action: selected.id, via: config.apiBaseUrl, trust: config.webBackendTrust });
      return;
    }
    try {
      const formData = new FormData(form);
      const countryCode = formCountryCode(form);
      const query = new URLSearchParams();
      const body = { tenant_id: tenant };
      query.set('tenant_id', tenant);
      let uploadFile = null;
      for (const field of fields) {
        if (field.type === 'file') {
          const file = form.querySelector(`[name="${field.name}"]`)?.files?.[0];
          if (!file) continue;
          if (selected.binaryUpload) uploadFile = file;
          else {
            body.filename = file.name;
            body.media_type = file.type;
            body.content_base64 = await readFileAsBase64(file);
          }
          continue;
        }
        const normalized = normalizeFieldValue(field, formData.get(field.name), { countryCode });
        if (normalized === undefined) continue;
        if (selected.method === 'GET' || selected.binaryUpload) query.append(field.name, typeof normalized === 'string' ? normalized : JSON.stringify(normalized));
        else body[field.name] = normalized;
      }
      const apiBase = String(config.apiBaseUrl || '/api').replace(/\/$/, '');
      const useQuery = selected.method === 'GET' || selected.binaryUpload;
      const requestUrl = useQuery ? `${apiBase}${selected.path}?${query}` : `${apiBase}${selected.path}`;
      const headers = selected.method === 'GET'
        ? { Accept: selected.download ? '*/*' : 'application/json' }
        : selected.binaryUpload
          ? {
              Accept: 'application/json',
              'Content-Type': uploadFile?.type || 'application/octet-stream',
              'X-OpenInfra-Filename': encodeURIComponent(uploadFile?.name || 'dataset'),
            }
          : { Accept: 'application/json', 'Content-Type': 'application/json' };
      if (selected.binaryUpload && !uploadFile) throw new Error('Le fichier source est obligatoire.');
      const response = await fetch(requestUrl, {
        method: selected.method,
        credentials: 'same-origin',
        headers,
        body: selected.method === 'GET' ? undefined : selected.binaryUpload ? uploadFile : JSON.stringify(body),
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
        if (!response.ok) {
          const operationError = new Error(payload.error || JSON.stringify(payload));
          operationError.status = response.status;
          throw operationError;
        }
        setResult(payload);
      }
      setShouldFocusMain(true);
    } catch (error) {
      setResult({
        error: error instanceof Error ? error.message : String(error),
        status: Number.isInteger(error?.status) ? error.status : null,
      });
      setShouldFocusMain(true);
    }
  }

  const displayedVersion = version?.version || config.version || i18n.t('unavailable');
  const filteredModules = MODULES;
  const submissionCompleted = result !== null && !(typeof result === 'object' && result?.error);
  const protectedForms = bffStatus?.protectedForms === 'enabled' ? i18n.t('active') : i18n.t('configure');
  const activeModule = MODULES.find((module) => module.id === activeModuleId) || MODULES[0];
  const activeManagementResource = selected.managementResourceId ? managementResourceById(selected.managementResourceId) : null;
  const pageTitle = activeModuleId === 'overview' ? 'Dashboard' : activeModule.shortLabel || activeModule.label;
  const pageSubtitle = activeModuleId === 'overview'
    ? i18n.t('dashboardSubtitle')
    : (activeManagementResource
      ? i18n.t('managementSubtitle', { operation: localizedManagementLabel(activeManagementResource, language) })
      : i18n.t('operationSubtitle', { operation: selected.label }));

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
      <MegaMenu module={megaMenuModule} selectedOperationId={selected.id} chooseOperation={chooseOperation} close={closeResponsiveNavigation} i18n={i18n} language={language} />
      {mobileSidebarOpen && <nav id="openinfra-compact-navigation" className="openinfra-compact-navigation" aria-label={i18n.t('navigation')}>
        <div className="openinfra-compact-navigation-header"><strong>{i18n.t('navigation')}</strong><button type="button" className="openinfra-navigation-close" aria-label={i18n.t('closeNavigation')} onClick={() => closeResponsiveNavigation({ restoreFocus: true })}>×</button></div>
        <div className="openinfra-compact-navigation-body"><div className="openinfra-sidebar-heading">{i18n.t('control')}</div><NavigationTree modules={filteredModules} activeNavigationModuleId={activeNavigationModuleId} selectedOperationId={selected.id} opened={opened} openedContexts={openedContexts} chooseOperation={chooseOperation} toggleAccordion={toggleAccordion} toggleSidebarContext={toggleSidebarContext} surface="compact" language={language} /><div className="openinfra-sidebar-heading">{i18n.t('runtimeStatus')}</div>{runtimeStatus}</div>
      </nav>}
    </header>
    {(mobileSidebarOpen || megaMenuModuleId) && <button type="button" className="openinfra-navigation-backdrop" aria-label={i18n.t('closeNavigation')} onClick={() => closeResponsiveNavigation({ restoreFocus: true })} />}
    <div className="container-fluid">
      <div className="row">
        <nav id="openinfra-sidebar" className="col-xl-2 openinfra-sidebar" aria-label={i18n.t('navigation')}>
          <div className="openinfra-sidebar-heading">{i18n.t('control')}</div>
          <NavigationTree modules={filteredModules} activeNavigationModuleId={activeNavigationModuleId} selectedOperationId={selected.id} opened={opened} openedContexts={openedContexts} chooseOperation={chooseOperation} toggleAccordion={toggleAccordion} toggleSidebarContext={toggleSidebarContext} language={language} />
          <div className="openinfra-sidebar-heading">{i18n.t('runtimeStatus')}</div>
          {runtimeStatus}
        </nav>
        <main id="openinfra-main-content" ref={mainContentRef} tabIndex={-1} className="col-xl-10 ms-sm-auto openinfra-main">
          <RuntimeLicenseBanner report={licenseReport} failed={licenseStatusFailed} i18n={i18n} />
          <div className="pb-2 mb-3 openinfra-titlebar"><h1 className="h2">{pageTitle}</h1><p className="text-muted mb-0">{pageSubtitle}</p></div>
          {submissionCompleted && activeModuleId !== 'overview' && <div className="alert alert-success" role="status">{i18n.t('success')}</div>}
          {activeModuleId === 'overview' && <div className="row g-3 mb-4 openinfra-dashboard-metrics" aria-label={i18n.t('componentStatistics')}><Metric title={i18n.t('version')} value={displayedVersion} /><Metric title="API" value={config.apiBaseUrl || '/api'} /><Metric title={i18n.t('trust')} value={config.webBackendTrust || 'server-side'} /><Metric title={i18n.t('forms')} value={protectedForms} /><Metric title={i18n.t('modules')} value={`${operationsCount} ${i18n.t('operations')}`} /></div>}
          {activeModuleId === 'overview'
            ? <OverviewStats i18n={i18n} modules={businessModules} fieldsCount={businessFieldsCount} />
            : (activeManagementResource
              ? <ManagementWorkspace key={activeManagementResource.id} resource={activeManagementResource} config={config} tenant={tenant} i18n={i18n} language={language} announce={announce} />
              : <section className="card openinfra-operation-card" aria-labelledby="openinfra-operation-title"><div className="card-body"><h2 id="openinfra-operation-title" className="h4">{selected.label}</h2><OperationForm i18n={i18n} language={language} selected={selected} tenant={tenant} setTenant={setTenant} execute={execute} /><GraphResultPanel i18n={i18n} operation={selected} result={result} /></div></section>)}
        </main>
      </div>
    </div>
  </div>;
}

function GraphResultPanel({ i18n, operation, result }) {
  const serialized = result === null ? i18n.t('pendingResult') : (typeof result === 'string' ? result : JSON.stringify(result, null, 2));
  if (operation.id === 'rsot-as-of' && result !== null && typeof result !== 'string' && !result.error) {
    return <div className="mt-3"><TimeTravelReport i18n={i18n} result={result} /><RawGraphResult i18n={i18n} value={serialized} /></div>;
  }
  if (operation.id === 'rag-query' && result !== null && typeof result !== 'string' && !result.error) {
    return <div className="mt-3"><GovernedRagReport i18n={i18n} result={result} /><RawGraphResult i18n={i18n} value={serialized} /></div>;
  }
  if ((operation.id === 'rsot-quality-object' || operation.id === 'rsot-quality-summary') && result !== null && typeof result !== 'string' && !result.error) {
    return <div className="mt-3"><RsotQualityReport i18n={i18n} result={result} /><RawGraphResult i18n={i18n} value={serialized} /></div>;
  }
  if (!operation.id.startsWith('graph-') || result === null || typeof result === 'string' || result.error) {
    return <pre className="openinfra-result mt-3" role="status" aria-live="polite" aria-atomic="true" aria-label={i18n.t('operationResult')}>{serialized}</pre>;
  }
  if (operation.id === 'graph-export') {
    return <><div className="alert alert-success openinfra-download-result mt-3" role="status"><strong>{i18n.t('downloadReady')}</strong><br />{result.filename} · {result.size_bytes || 0} octets</div><RawGraphResult i18n={i18n} value={serialized} /></>;
  }
  const visualization = operation.id === 'graph-spof'
    ? <SpofRanking i18n={i18n} result={result} />
    : operation.id === 'graph-change-impact'
      ? <><ChangeImpactReport i18n={i18n} result={result} /><DependencyGraphVisualization i18n={i18n} result={result} /></>
      : <DependencyGraphVisualization i18n={i18n} result={result} />;
  return <div className="mt-3">{visualization}<RawGraphResult i18n={i18n} value={serialized} /></div>;
}

function RsotQualityReport({ i18n, result }) {
  const reports = Array.isArray(result.reports) ? result.reports : [result];
  const certified = Number(result.certified ?? reports.filter((report) => report.certification_status === 'certified').length);
  const warning = Number(result.warning ?? reports.filter((report) => report.certification_status === 'warning').length);
  const rejected = Number(result.rejected ?? reports.filter((report) => report.certification_status === 'rejected').length);
  const averageScore = Number(result.average_score ?? reports.reduce((total, report) => total + Number(report.score || 0), 0) / Math.max(reports.length, 1));
  const allIssues = reports.flatMap((report) => (Array.isArray(report.issues) ? report.issues.map((issue) => ({ ...issue, key: report.key })) : []));
  const statusClass = rejected > 0 ? 'text-bg-danger' : warning > 0 ? 'text-bg-warning' : 'text-bg-success';
  return <section className="openinfra-rsot-quality-report mb-4" aria-labelledby="openinfra-rsot-quality-title">
    <div className="d-flex flex-wrap justify-content-between gap-2 align-items-start"><h3 id="openinfra-rsot-quality-title" className="h6 mb-1">{i18n.label('Certification qualité RSOT')}</h3><span className={`badge ${statusClass}`}>{rejected > 0 ? i18n.label('Rejeté') : warning > 0 ? i18n.label('Avertissement') : i18n.label('Certifié')}</span></div>
    <dl className="row g-2 mt-2 openinfra-rsot-quality-summary"><div className="col-sm-6 col-xl-3"><dt>{i18n.label('Objets évalués')}</dt><dd>{Number(result.total ?? reports.length)}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.label('Score moyen')}</dt><dd>{averageScore.toFixed(2)}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.label('Certifiés')}</dt><dd>{certified}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.label('Avertissements / rejets')}</dt><dd>{warning} / {rejected}</dd></div></dl>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-rsot-quality-dimensions"><caption>{i18n.label('Dimensions de qualité')}</caption><thead><tr><th scope="col">{i18n.t('sourceObject')}</th><th scope="col">{i18n.label('Statut')}</th><th scope="col">{i18n.label('Score')}</th><th scope="col">{i18n.label('Complétude')}</th><th scope="col">{i18n.label('Fraîcheur')}</th><th scope="col">{i18n.label('Autorité')}</th><th scope="col">{i18n.label('Confiance')}</th></tr></thead><tbody>{reports.map((report) => <tr key={report.key || report.display_name}><th scope="row">{report.display_name || report.key || '—'}<small className="d-block text-muted">{report.key || '—'} · {report.source || '—'}</small></th><td>{report.certification_status || '—'}</td><td>{Number(report.score || 0)}</td><td>{Number(report.completeness_score || 0)}</td><td>{Number(report.freshness_score || 0)}</td><td>{Number(report.authority_score || 0)}</td><td>{Number(report.confidence_score || 0)}</td></tr>)}</tbody></table></div>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-rsot-quality-issues"><caption>{i18n.label('Anomalies qualité')}</caption><thead><tr><th scope="col">{i18n.t('sourceObject')}</th><th scope="col">{i18n.label('Sévérité')}</th><th scope="col">{i18n.label('Champ')}</th><th scope="col">{i18n.label('Code')}</th><th scope="col">{i18n.label('Message')}</th></tr></thead><tbody>{allIssues.length > 0 ? allIssues.map((issue, index) => <tr key={`${issue.key}-${issue.code}-${issue.field}-${index}`}><td>{issue.key || '—'}</td><td>{issue.severity || '—'}</td><td>{issue.field || '—'}</td><td>{issue.code || '—'}</td><td>{issue.message || '—'}{issue.actual_source || issue.expected_source || issue.governance_rule ? <small className="d-block text-muted">{i18n.label('Source observée')}: {issue.actual_source || '—'} · {i18n.label('Source attendue')}: {issue.expected_source || '—'} · {i18n.label('Règle')}: {issue.governance_rule || '—'}</small> : null}</td></tr>) : <tr><td colSpan="5">{i18n.label('Aucune anomalie qualité')}</td></tr>}</tbody></table></div>
  </section>;
}

function GovernedRagReport({ i18n, result }) {
  const citations = Array.isArray(result.citations) ? result.citations : [];
  const sourceObjects = Array.isArray(result.source_objects) ? result.source_objects : [];
  const governance = result.governance && typeof result.governance === 'object' ? result.governance : {};
  const mutationPerformed = governance.source_data_mutation_performed === true;
  const validationRequired = governance.change_validation_required !== false;
  return <section className="openinfra-rag-governance-report mb-4" aria-labelledby="openinfra-rag-governance-title">
    <div className="d-flex flex-wrap justify-content-between gap-2 align-items-start"><h3 id="openinfra-rag-governance-title" className="h6 mb-1">{i18n.t('resultTitle')}</h3><span className={`badge ${mutationPerformed ? 'text-bg-danger' : 'text-bg-success'}`}>{governance.mode || i18n.t('reads')}</span></div>
    <dl className="row g-2 mt-2 openinfra-rag-governance-summary"><div className="col-sm-6 col-xl-3"><dt>{i18n.label('Statut')}</dt><dd>{result.status || '—'}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.label('Confiance (0 à 1)')}</dt><dd>{result.confidence || '0'}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('mutations')}</dt><dd>{mutationPerformed ? i18n.t('yes') : i18n.t('no')}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('required')}</dt><dd>{validationRequired ? i18n.t('yes') : i18n.t('no')}</dd></div></dl>
    <p className="openinfra-rag-answer" role="status" aria-live="polite">{result.answer || '—'}</p>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-rag-source-objects"><caption>{i18n.t('sourceObject')}</caption><thead><tr><th scope="col">{i18n.t('sourceObject')}</th><th scope="col">{i18n.t('provenance')}</th><th scope="col">{i18n.label('Confiance (0 à 1)')}</th></tr></thead><tbody>{sourceObjects.length > 0 ? sourceObjects.map((source) => <tr key={source.object_key}><th scope="row">{source.title || source.object_key}<small className="d-block text-muted">{source.object_key}</small></th><td>{source.source_uri || '—'}</td><td>{source.score || '0'}</td></tr>) : <tr><td colSpan="3">{i18n.t('noGraphData')}</td></tr>}</tbody></table></div>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-rag-citations"><caption>{i18n.t('provenance')}</caption><thead><tr><th scope="col">{i18n.t('sourceObject')}</th><th scope="col">{i18n.label('Source')}</th><th scope="col">{i18n.label('Confiance (0 à 1)')}</th><th scope="col">{i18n.t('resultTitle')}</th></tr></thead><tbody>{citations.length > 0 ? citations.map((citation) => <tr key={citation.chunk_id}><th scope="row">{citation.title || citation.source_ref}<small className="d-block text-muted">{citation.source_ref}</small></th><td>{citation.source_type || '—'}</td><td>{citation.score || '0'}</td><td>{citation.excerpt || '—'}</td></tr>) : <tr><td colSpan="4">{i18n.t('noGraphData')}</td></tr>}</tbody></table></div>
  </section>;
}

function TimeTravelReport({ i18n, result }) {
  const relations = Array.isArray(result.relations) ? result.relations : [];
  const provenance = result.provenance && typeof result.provenance === 'object' ? result.provenance : {};
  const complete = result.complete !== false;
  const objectKey = String(result.key || result.object_key || '—');
  return <section className="openinfra-time-travel-report mb-4" aria-labelledby="openinfra-time-travel-title">
    <div className="d-flex flex-wrap justify-content-between gap-2 align-items-start"><h3 id="openinfra-time-travel-title" className="h6 mb-1">{i18n.t('timeTravelReport')}</h3><span className={`badge ${complete ? 'text-bg-success' : 'text-bg-warning'}`}>{complete ? i18n.t('completeHistoricalState') : i18n.t('boundedHistoricalState')}</span></div>
    <dl className="row g-2 mt-2 openinfra-time-travel-summary"><div className="col-sm-6 col-xl-3"><dt>{i18n.t('historicalObject')}</dt><dd>{result.display_name || objectKey}<small className="d-block text-muted">{objectKey}</small></dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('requestedAt')}</dt><dd>{result.as_of || '—'}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('resolvedVersion')}</dt><dd>{result.resolved_version ?? result.version ?? '—'}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('historicalRelations')}</dt><dd>{Number(result.relation_count || relations.length)}</dd></div></dl>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-time-travel-provenance"><caption>{i18n.t('provenance')}</caption><thead><tr><th scope="col">{i18n.t('sourceSystem')}</th><th scope="col">{i18n.t('snapshotChangedBy')}</th><th scope="col">{i18n.t('snapshotChangedAt')}</th><th scope="col">{i18n.t('snapshotIdentifier')}</th></tr></thead><tbody><tr><td>{provenance.source_system || result.source || '—'}</td><td>{provenance.changed_by || result.snapshot_changed_by || '—'}</td><td>{provenance.snapshot_changed_at || result.snapshot_changed_at || '—'}</td><td>{provenance.snapshot_id || result.snapshot_id || '—'}</td></tr></tbody></table></div>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-time-travel-relations"><caption>{i18n.t('historicalRelations')}</caption><thead><tr><th scope="col">{i18n.t('relationType')}</th><th scope="col">{i18n.t('sourceObject')}</th><th scope="col">{i18n.t('targetObject')}</th><th scope="col">{i18n.t('provenance')}</th><th scope="col">{i18n.t('validityWindow')}</th></tr></thead><tbody>{relations.length > 0 ? relations.map((relation) => <tr key={relation.id || `${relation.source_key}-${relation.target_key}-${relation.relation_type}`}><td>{relation.relation_type || '—'}</td><td>{relation.source_key || '—'}</td><td>{relation.target_key || '—'}</td><td>{relation.provenance || '—'}</td><td>{`${relation.valid_from || '—'} → ${relation.valid_to || '∞'}`}</td></tr>) : <tr><td colSpan="5">{i18n.t('noHistoricalRelations')}</td></tr>}</tbody></table></div>
  </section>;
}

function ChangeImpactReport({ i18n, result }) {
  const services = Array.isArray(result.business_services) ? result.business_services : [];
  const risks = Array.isArray(result.critical_dependencies) ? result.critical_dependencies : [];
  const complete = result.complete !== false;
  const rootSpof = result.root_spof_risk === true;
  return <section className="openinfra-change-impact-report mb-4" aria-labelledby="openinfra-change-impact-title">
    <div className="d-flex flex-wrap justify-content-between gap-2 align-items-start"><h3 id="openinfra-change-impact-title" className="h6 mb-1">{i18n.t('changeImpactReport')}</h3><span className={`badge ${complete ? 'text-bg-success' : 'text-bg-warning'}`}>{complete ? i18n.t('completeAnalysis') : i18n.t('boundedAnalysis')}</span></div>
    <dl className="row g-2 mt-2 openinfra-change-impact-summary"><div className="col-sm-6 col-xl-3"><dt>{i18n.t('affectedNodes')}</dt><dd>{Number(result.impacted_count || 0)}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('impactedBusinessServices')}</dt><dd>{Number(result.business_service_count || services.length)}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('criticalDependencies')}</dt><dd>{Number(result.critical_dependency_count || risks.length)}</dd></div><div className="col-sm-6 col-xl-3"><dt>{i18n.t('rootSpofRisk')}</dt><dd>{rootSpof ? i18n.t('yes') : i18n.t('no')}</dd></div></dl>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-change-impact-services"><caption>{i18n.t('impactedBusinessServices')}</caption><thead><tr><th scope="col">{i18n.t('impactedBusinessServices')}</th><th scope="col">{i18n.label('Type de ressource')}</th><th scope="col">{i18n.t('graphDepth')}</th></tr></thead><tbody>{services.length > 0 ? services.map((service) => <tr key={service.key}><th scope="row">{service.display_name || service.key}<small className="d-block text-muted">{service.key}</small></th><td>{service.resource_type || service.kind || '—'}</td><td>{service.depth ?? '—'}</td></tr>) : <tr><td colSpan="3">{i18n.t('noGraphData')}</td></tr>}</tbody></table></div>
    <div className="table-responsive mt-3"><table className="table table-sm align-middle openinfra-change-impact-dependencies"><caption>{i18n.t('criticalDependencies')}</caption><thead><tr><th scope="col">{i18n.t('criticalDependencies')}</th><th scope="col">{i18n.t('riskLevel')}</th><th scope="col">{i18n.t('impactedBusinessServices')}</th><th scope="col">{i18n.t('affectedNodes')}</th><th scope="col">{i18n.t('affectedSample')}</th></tr></thead><tbody>{risks.length > 0 ? risks.map((risk) => { const node = risk.node || {}; const sample = Array.isArray(risk.affected_business_service_keys) ? risk.affected_business_service_keys.join(', ') : ''; return <tr key={node.key || sample}><th scope="row">{node.display_name || node.key || '—'}<small className="d-block text-muted">{node.key || ''}</small></th><td>{String(risk.risk_level || '—').toUpperCase()}</td><td>{Number(risk.affected_business_service_count || 0)}</td><td>{Number(risk.affected_node_count || 0)}</td><td>{sample || '—'}</td></tr>; }) : <tr><td colSpan="5">{i18n.t('noGraphData')}</td></tr>}</tbody></table></div>
  </section>;
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
  return groups.map(({ module, operations, total }) => <section className="openinfra-global-search-group" role="group" aria-label={`${i18n.t('globalSearchResults')} ${module.shortLabel || module.label}`} key={module.id}><div className="openinfra-global-search-group-title"><span>{module.shortLabel || module.label}</span><span>{i18n.count(total, 'result', 'results')}</span></div>{operations.map((operation) => <button type="button" className="openinfra-global-search-item" role="option" aria-selected="false" key={operation.id} onClick={() => onSelect(module, operation)}><span>{operation.label}</span><small>{module.shortLabel || module.label}</small></button>)}{total > operations.length && <div className="openinfra-global-search-more">{i18n.t(total - operations.length === 1 ? 'additionalResults' : 'additionalResultsPlural', { count: total - operations.length })}</div>}</section>);
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
