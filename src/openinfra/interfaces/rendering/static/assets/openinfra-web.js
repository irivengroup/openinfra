import { OpenInfraI18n, localizeOpenInfraCatalog } from "./openinfra-i18n.js?v=0.33.3";
let managementRegistryPromise = null;
let collapseManagementOperations = (_moduleId, operations, operationIds) => {
  const byId = new Map(operations.map((operation) => [operation.id, operation]));
  return operationIds.map((operationId) => byId.get(operationId)).filter(Boolean);
};
let flattenManagementCollection = () => [];
let localizedManagementLabel = (resource) => resource?.id || "";
let managementDisplayName = (_resource, item) => String(item?.name || item?.code || item?.id || "");
let managementFieldValue = (item, fieldName) => String(item?.[fieldName] ?? "");
let managementIdentityPayload = () => ({});
let managementNavigationOperation = () => null;
let managementResourceById = () => null;
let managementResourceForOperation = () => null;
let managementResourcesForModule = () => [];

async function ensureManagementRegistryLoaded() {
  if (!managementRegistryPromise) {
    managementRegistryPromise = import("./openinfra-management-resources.js?v=0.33.3").then((loaded) => {
      collapseManagementOperations = loaded.collapseManagementOperations;
      flattenManagementCollection = loaded.flattenManagementCollection;
      localizedManagementLabel = loaded.localizedManagementLabel;
      managementDisplayName = loaded.managementDisplayName;
      managementFieldValue = loaded.managementFieldValue;
      managementIdentityPayload = loaded.managementIdentityPayload;
      managementNavigationOperation = loaded.managementNavigationOperation;
      managementResourceById = loaded.managementResourceById;
      managementResourceForOperation = loaded.managementResourceForOperation;
      managementResourcesForModule = loaded.managementResourcesForModule;
      return loaded;
    });
  }
  return managementRegistryPromise;
}

import {
  fieldValidationMessage,
  formCountryCode,
  inputAttributesForField,
  inputTypeForField,
  normalizeFieldDefinition,
  normalizeFieldValue,
  validateControl
} from "./openinfra-form-fields.js?v=0.33.3";
import { OPENINFRA_DOMAIN_LOADERS, OPENINFRA_MODULES, OPENINFRA_SIDEBAR_CONTEXTS } from "./openinfra-domain-manifest.js?v=0.33.3";
import { OpenInfraQueryCache } from "./openinfra-query-cache.js?v=0.33.3";
import { OpenInfraVirtualList } from "./openinfra-virtual-list.js?v=0.33.3";
import { installOpenInfraWebVitals } from "./openinfra-web-vitals.js?v=0.33.3";


class OpenInfraApiClient {
  constructor(apiBaseUrl, tenantProvider, i18n = null) {
    this.i18n = i18n;
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
    this.tenantProvider = tenantProvider;
  }

  async request(operation, payload) {
    const path = this.interpolatePath(operation.path, payload);
    this.currentOperationId = operation.id || "";
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
    if (operation.download) {
      const blob = await response.blob();
      if (!response.ok) {
        const errorText = await blob.text();
        throw new Error(errorText || `Download failed with status ${response.status}`);
      }
      const disposition = response.headers.get("content-disposition") || "";
      const filename = this.downloadFilename(disposition, operation.downloadFilename || "openinfra-export.bin");
      const objectUrl = URL.createObjectURL(blob);
      try {
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = filename;
        anchor.hidden = true;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
      return {
        downloaded: true,
        filename,
        content_type: contentType || blob.type || "application/octet-stream",
        size_bytes: blob.size
      };
    }
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      throw new Error(typeof data === "string" ? data : JSON.stringify(data));
    }
    return data;
  }

  downloadFilename(disposition, fallback) {
    const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (encoded) {
      try {
        return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, ""));
      } catch (_error) {
        return fallback;
      }
    }
    const simple = disposition.match(/filename="?([^";]+)"?/i);
    return simple ? simple[1].trim() : fallback;
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
      const value = this.normalizedFieldValue(field, payload[field.name], payload);
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        query.set(field.name, String(value));
      }
    }
    const tenant = this.tenantProvider();
    if (this.isTenantScopedOperation({ id: this.currentOperationId || "" }) && tenant && !query.has("tenant_id")) {
      query.set("tenant_id", tenant);
    }
    return query.toString() ? `?${query.toString()}` : "";
  }

  buildBody(operation, payload) {
    const body = {};
    for (const field of operation.body || []) {
      const raw = payload[field.name];
      if (field.type === "file") {
        if (!raw) {
          if (field.required) {
            throw new Error(this.i18n?.t("requiredField", { field: field.label || field.name }) || `Missing required field: ${field.label || field.name}`);
          }
          continue;
        }
        this.assignBodyValue(body, "filename", raw.filename);
        this.assignBodyValue(body, "media_type", raw.media_type);
        this.assignBodyValue(body, "content_base64", raw.content_base64);
        continue;
      }
      const value = this.normalizedFieldValue(field, raw, payload);
      if (value === undefined || value === null || String(value).trim?.() === "") {
        if (field.required) {
          throw new Error(this.i18n?.t("requiredField", { field: field.label || field.name }) || `Missing required field: ${field.label || field.name}`);
        }
        continue;
      }
      this.assignBodyValue(body, field.target || field.name, value);
    }
    const tenant = this.tenantProvider();
    if (this.isTenantScopedOperation(operation) && tenant && operation.body && !Object.prototype.hasOwnProperty.call(body, "tenant_id")) {
      body.tenant_id = tenant;
    }
    return body;
  }

  isTenantScopedOperation(operation) {
    const id = String(operation?.id || this.currentOperationId || "");
    return !id.startsWith("itam-organization");
  }

  normalizedFieldValue(field, raw, payload = {}) {
    try {
      const value = normalizeFieldValue(field, raw, {
        countryCode: payload.country_code || payload.country || ""
      });
      if (value === undefined) {
        return undefined;
      }
      if (field.type === "boolean") {
        return ["1", "true", "yes", "oui"].includes(String(value).toLowerCase());
      }
      return value;
    } catch (error) {
      if (error instanceof Error && error.code) {
        throw new Error(fieldValidationMessage(this.i18n, { code: error.code }, error.field || field));
      }
      throw error;
    }
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
  search: "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.099zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z",
  menu: "M2 4h12v1.4H2V4zm0 3.3h12v1.4H2V7.3zm0 3.3h12V12H2v-1.4z",
  speedometer2: "M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4zM3.732 5.732a.5.5 0 0 1 .707 0l.915.914a.5.5 0 1 1-.708.708l-.914-.915a.5.5 0 0 1 0-.707zM2 10a.5.5 0 0 1 .5-.5h1.586a.5.5 0 0 1 0 1H2.5A.5.5 0 0 1 2 10zm9.5 0a.5.5 0 0 1 .5-.5h1.5a.5.5 0 0 1 0 1H12a.5.5 0 0 1-.5-.5zm.754-4.246a.5.5 0 0 1 0 .707l-.94.94a.5.5 0 1 1-.707-.708l.94-.94a.5.5 0 0 1 .707 0zM9.67 11.71a2 2 0 1 1-3.34-2.19l3.95-3.95a.5.5 0 0 1 .8.6l-1.41 5.54zM8 1a7 7 0 0 0-7 7c0 1.71.61 3.28 1.63 4.5a.5.5 0 0 0 .38.17h9.98a.5.5 0 0 0 .38-.17A6.97 6.97 0 0 0 15 8a7 7 0 0 0-7-7z",
  table: "M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm15 2h-4v3h4V4zm0 4h-4v3h4V8zm0 4h-4v3h3a1 1 0 0 0 1-1v-2zm-5 3v-3H6v3h4zm-5 0v-3H1v2a1 1 0 0 0 1 1h3zm-4-4h4V8H1v3zm0-4h4V4H1v3zm5-3v3h4V4H6zm4 4H6v3h4V8z",
  reference: "M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z",
  asset: "M2 1a2 2 0 0 1 2-2h5.6a2 2 0 0 1 1.414.586l2.4 2.4A2 2 0 0 1 14 3.4V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V1zm2 .8a.8.8 0 0 0-.8.8v10.8a.8.8 0 0 0 .8.8h8a.8.8 0 0 0 .8-.8V4.4h-2.2a1.8 1.8 0 0 1-1.8-1.8V.8H4zm1.25 5.05a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 0 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3zm-2.05 4.6a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 1 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3z",
  grid: "M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z",
  people: "M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm-1.559 4.27A4.985 4.985 0 0 0 8 10c-2.67 0-4.9 2.1-4.99 4.71A1 1 0 0 0 4 15h8a1 1 0 0 0 .99-1.29 5.002 5.002 0 0 0-3.549-3.44zM13.5 7a2.5 2.5 0 0 1-1.18 2.12 6.01 6.01 0 0 1 2.2 2.56A1 1 0 0 0 15.5 10.5 3.5 3.5 0 0 0 12 7h1.5z",
  sliders: "M3 4h10v1H3V4zm2 3h6v1H5V7zm-2 3h10v1H3v-1z",
  shield: "M5.338 1.59a61.44 61.44 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188A10.7 10.7 0 0 0 8 15a10.7 10.7 0 0 0 3.574-2.976c1.527-1.998 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39 61.44 61.44 0 0 0-2.837-.856C9.552 1.29 8.531 1.067 8 1.067c-.531 0-1.552.223-2.662.523z",
  activity: "M6.5 12a.5.5 0 0 1-.447-.276L3.382 6.382 1.894 9.36A.5.5 0 0 1 1.447 9.636H.5a.5.5 0 0 1 0-1h.638l1.915-3.83a.5.5 0 0 1 .894 0L6.5 9.91l2.553-5.105a.5.5 0 0 1 .894 0l1.915 3.83h3.638a.5.5 0 0 1 0 1h-3.947a.5.5 0 0 1-.447-.276L9.5 6.382l-2.553 5.342A.5.5 0 0 1 6.5 12z"
};

const DCIM_REFERENCE_FIELDS = new Set(["site", "site_code", "building", "building_code", "floor", "floor_code", "room", "room_code", "zone", "zone_code", "rack", "row", "column"]);
const DCIM_REFERENCE_LABELS = { site: "Site", site_code: "Site", building: "Bâtiment", building_code: "Bâtiment", floor: "Étage", floor_code: "Étage", room: "Salle", room_code: "Salle", zone: "Zone", zone_code: "Zone", rack: "Rack", row: "Ligne salle", column: "Colonne salle" };

function validateModuleManifest(modules) {
  if (!Array.isArray(modules) || modules.length === 0) {
    throw new Error("Le manifeste des composants OpenInfra est vide ou invalide.");
  }
  const moduleIds = new Set();
  for (const module of modules) {
    if (!module || typeof module !== "object" || !module.id || !module.label || !Array.isArray(module.operations)) {
      throw new Error("Un composant du manifeste OpenInfra est invalide.");
    }
    if (moduleIds.has(module.id)) throw new Error(`Identifiant de composant dupliqué : ${module.id}.`);
    moduleIds.add(module.id);
    if (!module.stats || !Number.isInteger(module.stats.operations) || module.stats.operations < module.operations.length) {
      throw new Error(`Statistiques du composant ${module.id} invalides.`);
    }
  }
}

function validateOperationCatalog(modules) {
  const operationIds = new Set();
  for (const module of modules.filter((entry) => entry.loaded)) {
    for (const operation of module.operations) {
      if (!operation || typeof operation !== "object" || !operation.id || !operation.path || !operation.method) {
        throw new Error(`Une opération du composant ${module.id || "inconnu"} est invalide.`);
      }
      if (operationIds.has(operation.id)) throw new Error(`Identifiant d’opération dupliqué : ${operation.id}.`);
      operationIds.add(operation.id);
      const fields = [...(operation.query || []), ...(operation.body || [])];
      for (const [fieldIndex, field] of fields.entries()) {
        const validLegacyLabel = typeof field === "string" && field.trim() !== "";
        const validDefinition = field && typeof field === "object" && Boolean(field.name);
        if (!validLegacyLabel && !validDefinition) {
          throw new Error(`Champ invalide dans ${operation.id} à l’index ${fieldIndex}.`);
        }
      }
    }
  }
}

function renderFatalStartupError(root, error) {
  const message = error instanceof Error ? error.message : String(error || "Erreur inconnue");
  console.error("OpenInfra web startup failed", error);
  if (!root) {
    return;
  }
  const wrapper = document.createElement("main");
  wrapper.className = "container py-5";
  wrapper.setAttribute("role", "main");
  const alert = document.createElement("div");
  alert.className = "alert alert-danger";
  alert.setAttribute("role", "alert");
  const title = document.createElement("h1");
  title.className = "h4";
  title.textContent = "OpenInfra Web ne peut pas démarrer";
  const detail = document.createElement("p");
  detail.className = "mb-0";
  detail.textContent = message;
  alert.append(title, detail);
  wrapper.append(alert);
  root.replaceChildren(wrapper);
}

class OpenInfraDashboard {
  constructor(root) {
    if (!root) {
      throw new Error("Le point de montage #openinfra-root est introuvable.");
    }
    validateModuleManifest(OPENINFRA_MODULES);
    validateOperationCatalog(OPENINFRA_MODULES);
    this.root = root;
    this.i18n = new OpenInfraI18n();
    this.applyLanguage();
    this.state = {
      activeModuleId: "overview",
      activeNavigationModuleId: "overview",
      selected: OPENINFRA_MODULES[0].operations[0],
      openedModules: new Set(),
      openedContexts: new Set(),
      organization: "default",
      organizationCatalog: null,
      organizationCatalogError: null,
      tenant: "default",
      tenantCatalog: null,
      tenantCatalogError: null,
      partnerCatalog: null,
      partnerCatalogError: null,
      countryCatalog: null,
      countryCatalogError: null,
      dcimCatalog: null,
      dcimCatalogError: null,
      config: null,
      ready: null,
      status: null,
      version: null,
      result: null,
      error: null,
      globalSearchQuery: "",
      globalSearchBackend: null,
      globalSearchLoading: false,
      globalSearchError: null,
      catalogLoading: false,
      mobileSidebarOpen: false,
      megaMenuModuleId: null,
      management: {
        resourceId: null,
        mode: "list",
        items: [],
        loading: false,
        error: null,
        filters: {},
        query: "",
        includeRetired: false,
        sortKey: null,
        sortDirection: "asc",
        page: 1,
        pageSize: 25,
        selectedItem: null,
        detailItem: null,
        detailLoading: false,
        deleteItem: null,
        notice: null
      }
    };
    this.catalogPromises = new Map();
    this.catalogLoadSequence = 0;
    this.queryCache = new OpenInfraQueryCache({ defaultTtlMs: 30_000, maxEntries: 192 });
    this.modulePromises = new Map();
    this.searchIndex = null;
    this.resourceTaxonomy = {};
    this.resourceCategories = [];
    this.virtualLists = [];
    this.disposeVitals = null;
    this.handleResize = () => {
      this.syncFixedHeaderOffset();
      if (!this.isMegamenuViewport() && this.state.megaMenuModuleId !== null) {
        this.state = { ...this.state, megaMenuModuleId: null };
        this.render();
      }
      if (!this.isCompactViewport() && this.state.mobileSidebarOpen) {
        this.state = { ...this.state, mobileSidebarOpen: false };
        this.render();
      }
    };
    this.handleDocumentKeydown = (event) => {
      if (event.key === "Escape" && (this.state.management.detailItem || this.state.management.deleteItem)) {
        event.preventDefault();
        this.closeManagementDialogs();
        return;
      }
      if (event.key === "Escape" && (this.state.mobileSidebarOpen || this.state.megaMenuModuleId)) {
        event.preventDefault();
        this.closeResponsiveNavigation(true);
      }
    };
  }


  applyLanguage() {
    localizeOpenInfraCatalog({
      modules: OPENINFRA_MODULES.filter((module) => module.loaded),
      contexts: OPENINFRA_SIDEBAR_CONTEXTS,
      resourceTaxonomy: this.resourceTaxonomy,
      resourceCategories: this.resourceCategories,
      dcimReferenceLabels: DCIM_REFERENCE_LABELS
    }, this.i18n.language);
  }

  setLanguage(language) {
    this.i18n.setLanguage(language);
    document.documentElement.lang = this.i18n.language;
    this.applyLanguage();
    this.render();
  }

  async start() {
    document.documentElement.lang = this.i18n.language;
    window.addEventListener("resize", this.handleResize);
    document.addEventListener("keydown", this.handleDocumentKeydown);
    this.disposeVitals = installOpenInfraWebVitals({ target: window });
    this.render();
    await this.refreshRuntime();
    this.render();
    void this.refreshReadiness();
  }

  async ensureModuleLoaded(moduleId) {
    const current = OPENINFRA_MODULES.find((module) => module.id === moduleId);
    if (!current) throw new Error(`Composant OpenInfra inconnu : ${moduleId}`);
    if (current.loaded) {
      if (moduleId === "dcim" || moduleId === "itam") await ensureManagementRegistryLoaded();
      return current;
    }
    const existing = this.modulePromises.get(moduleId);
    if (existing) return existing;
    const loader = OPENINFRA_DOMAIN_LOADERS[moduleId];
    if (!loader) throw new Error(`Aucun chunk n’est déclaré pour le composant ${moduleId}.`);
    const promise = Promise.all([
      loader(),
      moduleId === "dcim" || moduleId === "itam" ? ensureManagementRegistryLoaded() : Promise.resolve(null)
    ]).then(([loaded]) => {
      const index = OPENINFRA_MODULES.findIndex((module) => module.id === moduleId);
      const definition = { ...loaded.default, stats: current.stats, loaded: true };
      OPENINFRA_MODULES.splice(index, 1, definition);
      if (moduleId === "rsot") {
        this.resourceTaxonomy = loaded.resourceTaxonomy || {};
        this.resourceCategories = loaded.resourceCategories || [];
      }
      this.applyLanguage();
      validateOperationCatalog(OPENINFRA_MODULES);
      return definition;
    }).finally(() => this.modulePromises.delete(moduleId));
    this.modulePromises.set(moduleId, promise);
    return promise;
  }

  async loadSearchIndex() {
    if (this.searchIndex) return this.searchIndex;
    const loaded = await import("./openinfra-search-index.js?v=0.33.3");
    const syntheticModules = OPENINFRA_MODULES.map((module) => ({
      ...module,
      operations: loaded.default.filter((entry) => entry.moduleId === module.id).map((entry) => ({ ...entry }))
    }));
    localizeOpenInfraCatalog({ modules: syntheticModules, contexts: {}, resourceTaxonomy: {}, resourceCategories: [], dcimReferenceLabels: {} }, this.i18n.language);
    this.searchIndex = syntheticModules.flatMap((module) => module.operations.map((operation) => ({ ...operation, moduleId: module.id, moduleLabel: module.shortLabel || module.label, moduleDescription: module.description || "" })));
    return this.searchIndex;
  }

  async refreshRuntime() {
    try {
      const bootstrap = await this.queryCache.run("bootstrap", async (signal) => {
        const response = await fetch("/bootstrap.json", { credentials: "same-origin", headers: { Accept: "application/json" }, signal });
        if (!response.ok) throw new Error(`Bootstrap unavailable: ${response.status}`);
        return response.json();
      }, { ttlMs: 60_000, scope: "bootstrap" });
      this.state = {
        ...this.state,
        config: bootstrap.config || null,
        version: bootstrap.version || null,
        status: bootstrap.status || null,
        error: null
      };
    } catch (error) {
      this.state = { ...this.state, error };
    }
  }

  async refreshReadiness() {
    try {
      const ready = await this.queryCache.run("readiness", async (signal) => {
        const response = await fetch("/ready", { credentials: "same-origin", headers: { Accept: "application/json" }, signal });
        return response.ok ? response.json() : { ready: false };
      }, { ttlMs: 5_000, force: true, scope: "readiness" });
      this.state = { ...this.state, ready };
    } catch (_error) {
      this.state = { ...this.state, ready: { ready: false } };
    }
    this.updateRuntimeStatus();
  }

  updateRuntimeStatus() {
    const markup = this.renderRuntimeStatus();
    for (const element of document.querySelectorAll(".openinfra-runtime-status")) {
      element.outerHTML = markup;
    }
  }

  operationCatalogDependencies(operation) {
    if (!operation || operation.id === "overview") {
      return [];
    }
    const fields = [...(operation.query || []), ...(operation.body || [])];
    const dependencies = new Set();
    const fieldTypes = new Set(fields.map((field) => String(field?.type || "")));
    const fieldNames = new Set(fields.map((field) => String(field?.name || "").toLowerCase()));
    if (this.operationNeedsGlobalScopeSelectors(operation)
      || fieldTypes.has("organization-select")
      || fieldTypes.has("tenant-select")
      || fieldTypes.has("partner-select")) {
      dependencies.add("scope");
    }
    if (fieldTypes.has("country-select") || fieldNames.has("country") || fieldNames.has("country_code")) {
      dependencies.add("countries");
    }
    if (fieldTypes.has("partner-select")) {
      dependencies.add("partners");
    }
    if (fields.some((field) => this.isDcimReferenceField(field))) {
      dependencies.add("dcim");
    }
    return [...dependencies];
  }

  catalogDependencyLoaded(dependency) {
    if (dependency === "scope") return Boolean(this.state.organizationCatalog && this.state.tenantCatalog);
    if (dependency === "countries") return Boolean(this.state.countryCatalog);
    if (dependency === "partners") return Boolean(this.state.partnerCatalog);
    if (dependency === "dcim") return Boolean(this.state.dcimCatalog);
    return true;
  }

  operationCatalogsNeedLoading(operation) {
    return this.operationCatalogDependencies(operation).some((dependency) => !this.catalogDependencyLoaded(dependency));
  }

  async loadCatalogsForOperation(operation) {
    const dependencies = this.operationCatalogDependencies(operation);
    if (dependencies.length === 0 || !this.operationCatalogsNeedLoading(operation)) {
      return;
    }
    const sequence = ++this.catalogLoadSequence;
    const independent = [];
    if (dependencies.includes("scope") && !this.catalogDependencyLoaded("scope")) {
      independent.push(this.catalogPromise("scope", () => this.refreshScopeCatalogs()));
    }
    if (dependencies.includes("countries") && !this.catalogDependencyLoaded("countries")) {
      independent.push(this.catalogPromise("countries", () => this.refreshCountryCatalog()));
    }
    if (dependencies.includes("dcim") && !this.catalogDependencyLoaded("dcim")) {
      independent.push(this.catalogPromise("dcim", () => this.refreshDcimCatalog()));
    }
    await Promise.all(independent);
    if (dependencies.includes("partners") && !this.catalogDependencyLoaded("partners")) {
      await this.catalogPromise("partners", () => this.refreshPartnerCatalog());
    }
    const activeOperationId = this.managementActionOperation()?.id || this.state.selected.id;
    if (sequence !== this.catalogLoadSequence || activeOperationId !== operation.id) {
      return;
    }
    this.state = { ...this.state, catalogLoading: false };
    this.render();
  }

  catalogPromise(key, loader) {
    const current = this.catalogPromises.get(key);
    if (current) {
      return current;
    }
    const promise = Promise.resolve().then(loader).finally(() => this.catalogPromises.delete(key));
    this.catalogPromises.set(key, promise);
    return promise;
  }


  async fetchJsonCached(key, url, { ttlMs = 60_000, force = false, scope = null } = {}) {
    return this.queryCache.run(key, async (signal) => {
      const response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" }, signal });
      if (!response.ok) throw new Error(`${key} returned ${response.status}`);
      return response.json();
    }, { ttlMs, force, scope });
  }

  async refreshScopeCatalogs() {
    const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
    const tenantId = encodeURIComponent(this.state.tenant || "default");
    const [organizationResult, tenantResult] = await Promise.allSettled([
      this.fetchJsonCached(`catalog:organizations:${tenantId}`, `${base}/v1/itam/organizations?tenant_id=${tenantId}`),
      this.fetchJsonCached(`catalog:tenants:${tenantId}`, `${base}/v1/itam/tenants?tenant_id=${tenantId}`)
    ]);
    let organization = this.state.organization;
    let tenant = this.state.tenant;
    const updates = {};
    if (organizationResult.status === "fulfilled") {
      const catalog = organizationResult.value;
      const selectable = (catalog.items || []).filter((item) => item.selectable !== false && item.status === "active");
      const selected = catalog.auto_selected_organization_id || catalog.default_organization_id || organization;
      organization = selectable.some((item) => item.organization_id === selected) ? selected : organization;
      Object.assign(updates, { organizationCatalog: catalog, organizationCatalogError: null, organization });
    } else {
      Object.assign(updates, { organizationCatalog: null, organizationCatalogError: organizationResult.reason });
    }
    if (tenantResult.status === "fulfilled") {
      const catalog = tenantResult.value;
      const selectable = (catalog.items || []).filter((item) => item.selectable !== false && item.status === "active" && item.organization_id === organization);
      const selected = catalog.auto_selected_tenant_id || catalog.default_tenant_id || tenant;
      tenant = selectable.some((item) => item.tenant_id === selected)
        ? selected
        : (selectable[0]?.tenant_id || organization || tenant);
      Object.assign(updates, { tenantCatalog: catalog, tenantCatalogError: null, tenant });
    } else {
      Object.assign(updates, { tenantCatalog: null, tenantCatalogError: tenantResult.reason });
    }
    this.state = { ...this.state, ...updates };
  }


  async refreshCountryCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const catalog = await this.fetchJsonCached("catalog:countries", `${base}/v1/reference/countries`, { ttlMs: 300_000 });
      this.state = { ...this.state, countryCatalog: catalog, countryCatalogError: null };
    } catch (error) {
      this.state = { ...this.state, countryCatalog: null, countryCatalogError: error };
    }
  }


  async refreshOrganizationCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const tenantId = encodeURIComponent(this.state.tenant || "default");
      const catalog = await this.fetchJsonCached(`catalog:organizations:${tenantId}`, `${base}/v1/itam/organizations?tenant_id=${tenantId}`);
      const selectable = (catalog.items || []).filter((item) => item.selectable !== false && item.status === "active");
      const selected = catalog.auto_selected_organization_id || catalog.default_organization_id || this.state.organization;
      const organization = selectable.some((item) => item.organization_id === selected) ? selected : this.state.organization;
      this.state = { ...this.state, organizationCatalog: catalog, organizationCatalogError: null, organization };
    } catch (error) {
      this.state = { ...this.state, organizationCatalog: null, organizationCatalogError: error };
    }
  }

  async refreshTenantCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const tenantId = encodeURIComponent(this.state.tenant || "default");
      const catalog = await this.fetchJsonCached(`catalog:tenants:${tenantId}`, `${base}/v1/itam/tenants?tenant_id=${tenantId}`);
      const selectable = (catalog.items || []).filter((item) => {
        return item.selectable !== false && item.status === "active" && item.organization_id === this.state.organization;
      });
      const selected = catalog.auto_selected_tenant_id || catalog.default_tenant_id || this.state.tenant;
      const tenant = selectable.some((item) => item.tenant_id === selected)
        ? selected
        : (selectable[0]?.tenant_id || this.state.organization || this.state.tenant);
      this.state = {
        ...this.state,
        tenantCatalog: catalog,
        tenantCatalogError: null,
        tenant
      };
    } catch (error) {
      this.state = { ...this.state, tenantCatalog: null, tenantCatalogError: error };
    }
  }

  async refreshPartnerCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const params = new URLSearchParams({ tenant_id: this.state.tenant || "default" });
      if (this.state.organization) {
        params.set("organization_id", this.state.organization);
      }
      const catalog = await this.fetchJsonCached(`catalog:partners:${params.toString()}`, `${base}/v1/itam/partners?${params.toString()}`);
      this.state = { ...this.state, partnerCatalog: catalog, partnerCatalogError: null };
    } catch (error) {
      this.state = { ...this.state, partnerCatalog: null, partnerCatalogError: error };
    }
  }

  async refreshDcimCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const params = new URLSearchParams({ tenant_id: this.state.tenant || "default" });
      const catalog = await this.fetchJsonCached(`catalog:dcim:${params.toString()}`, `${base}/v1/dcim/topology-catalog?${params.toString()}`);
      this.state = { ...this.state, dcimCatalog: catalog, dcimCatalogError: null };
    } catch (error) {
      this.state = { ...this.state, dcimCatalog: null, dcimCatalogError: error };
    }
  }

  organizationOptions() {
    return (this.state.organizationCatalog?.items || [])
      .filter((organization) => organization.selectable !== false && organization.status === "active")
      .map((organization) => ({
        value: organization.organization_id,
        label: `${organization.display_name || organization.legal_name || organization.organization_id} — ${organization.organization_id}`
      }));
  }

  organizationLabel(organizationId) {
    const organization = (this.state.organizationCatalog?.items || []).find((item) => item.organization_id === organizationId);
    return organization?.display_name || organization?.legal_name || organizationId;
  }

  tenantOptions(organizationId = this.state.organization) {
    const tenants = (this.state.tenantCatalog?.items || [])
      .filter((tenant) => tenant.selectable !== false && tenant.status === "active" && tenant.organization_id === organizationId)
      .map((tenant) => ({
        value: tenant.tenant_id,
        label: `${tenant.name || tenant.tenant_id}${tenant.is_default ? ` — ${this.i18n.t("defaultMarker")}` : ""}`
      }));
    if (tenants.length > 0) {
      return tenants;
    }
    if (organizationId) {
      return [{ value: organizationId, label: `${this.organizationLabel(organizationId)} — ${this.i18n.t("implicitTenant")}` }];
    }
    return [];
  }

  partnerOptions(kind = null, organizationId = this.state.organization) {
    return (this.state.partnerCatalog?.items || [])
      .filter((partner) => {
        return partner.selectable !== false
          && partner.status === "active"
          && partner.organization_id === organizationId
          && (!kind || partner.kind === kind);
      })
      .map((partner) => ({
        value: partner.partner_id,
        label: `${partner.display_name || partner.legal_name || partner.partner_id} — ${partner.kind}`
      }));
  }

  renderOrganizationSelector() {
    const options = this.organizationOptions();
    const fallback = this.state.organization || "default";
    const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
    return `<label class="col-md-4 form-label">${this.escape(this.i18n.t("organization"))}<select id="openinfra-organization" class="form-select">${this.renderOptions(renderedOptions, fallback)}</select></label>`;
  }

  renderTenantSelector() {
    const options = this.tenantOptions(this.state.organization);
    const fallback = this.state.tenant || this.state.organization || "default";
    const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
    return `<label class="col-md-4 form-label">${this.escape(this.i18n.t("tenant"))}<select id="openinfra-tenant" class="form-select">${this.renderOptions(renderedOptions, fallback)}</select></label>`;
  }

  client() {
    return new OpenInfraApiClient(this.state.config?.apiBaseUrl || "/api", () => this.state.tenant, this.i18n);
  }

  globalSearchUrl(query, limit = 6) {
    const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
    const params = new URLSearchParams({
      tenant_id: this.state.tenant || "default",
      query,
      limit: String(limit)
    });
    return `${base}/v1/search/global?${params.toString()}`;
  }

  buildApiDocumentationUrl(route) {
    const normalizedRoute = String(route || "/docs").startsWith("/") ? String(route || "/docs") : `/${route}`;
    const value = String(this.state.config?.apiBaseUrl || "/api").trim();
    if (/^https?:\/\//i.test(value)) {
      const url = new URL(value);
      return `${url.origin}${normalizedRoute}`;
    }
    return normalizedRoute;
  }

  apiDocumentationLinks() {
    const published = this.state.config?.apiDocumentation || {};
    return {
      swaggerUrl: published.swaggerUrl || this.buildApiDocumentationUrl("/docs"),
      redocUrl: published.redocUrl || this.buildApiDocumentationUrl("/redoc"),
      openapiUrl: published.openapiUrl || this.buildApiDocumentationUrl("/openapi.yaml")
    };
  }


  syncFixedHeaderOffset() {
    const header = document.querySelector(".openinfra-header-stack");
    if (!header || typeof header.getBoundingClientRect !== "function") {
      return;
    }
    const height = Math.ceil(header.getBoundingClientRect().height);
    if (height > 0) {
      document.documentElement.style.setProperty("--openinfra-fixed-header-height", `${height}px`);
    }
  }

  isMegamenuViewport() {
    return typeof window !== "undefined"
      && window.matchMedia("(min-width: 768px) and (max-width: 1199.98px)").matches;
  }

  isCompactViewport() {
    return typeof window !== "undefined"
      && window.matchMedia("(max-width: 767.98px)").matches;
  }

  closeResponsiveNavigation(restoreFocus = false) {
    const focusId = restoreFocus && this.lastNavigationModuleId ? `openinfra-component-${this.lastNavigationModuleId}` : null;
    this.state = {
      ...this.state,
      activeNavigationModuleId: this.state.activeModuleId,
      mobileSidebarOpen: false,
      megaMenuModuleId: null
    };
    this.render();
    this.announce(this.i18n.t("navigationClosed"));
    if (focusId) {
      window.requestAnimationFrame(() => document.getElementById(focusId)?.focus());
    }
  }

  async openMegaMenu(moduleId, trigger = null) {
    let module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module || module.id === "overview" || !this.isMegamenuViewport()) return;
    if (trigger instanceof HTMLElement) this.lastNavigationModuleId = module.id;
    if (this.state.megaMenuModuleId !== module.id) {
      this.state = { ...this.state, activeNavigationModuleId: module.id, megaMenuModuleId: module.id, mobileSidebarOpen: false };
      this.render();
      this.announce(this.i18n.t("navigationOpened", { component: module.shortLabel || module.label }));
    }
    if (!module.loaded) {
      try { module = await this.ensureModuleLoaded(moduleId); } catch (error) { this.state = { ...this.state, error }; }
      if (this.state.megaMenuModuleId === moduleId) this.render();
    }
  }

  handleModuleNavigation(moduleId) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) {
      return;
    }
    if (module.id === "overview" || !this.isMegamenuViewport()) {
      void this.selectModule(moduleId);
      return;
    }
    void this.openMegaMenu(moduleId);
  }

  visibleOperations(module) {
    return module.operations;
  }

  sidebarOperationGroups(module, operations) {
    const configuredGroups = OPENINFRA_SIDEBAR_CONTEXTS[module.id] || [];
    const byId = new Map(operations.map((operation) => [operation.id, operation]));
    const groupedIds = new Set();
    const groups = configuredGroups.map((group) => {
      const existingIds = group.operationIds.filter((id) => byId.has(id));
      for (const operationId of existingIds) {
        groupedIds.add(operationId);
      }
      const groupOperations = collapseManagementOperations(
        module.id,
        operations,
        existingIds,
        this.i18n.language
      );
      return { label: group.label, operations: groupOperations };
    }).filter((group) => group.operations.length > 0);
    const remaining = operations.filter((operation) => !groupedIds.has(operation.id));
    if (remaining.length > 0) {
      groups.push({
        label: "Autres",
        operations: collapseManagementOperations(
          module.id,
          operations,
          remaining.map((operation) => operation.id),
          this.i18n.language
        )
      });
    }
    return groups;
  }

  sidebarContextKey(moduleId, label) {
    return `${moduleId}::${label}`;
  }

  contextForOperation(module, operationId) {
    return this.sidebarOperationGroups(module, module.operations).find((group) => {
      return group.operations.some((operation) => operation.id === operationId);
    });
  }

  managementResource() {
    return managementResourceById(this.state.management.resourceId);
  }

  operationById(moduleId, operationId) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    return module?.operations.find((operation) => operation.id === operationId) || null;
  }

  managementOperation(resource, role) {
    const operationId = resource?.operations?.[role];
    return operationId ? this.operationById(resource.moduleId, operationId) : null;
  }

  withManagementState(overrides) {
    return { ...this.state.management, ...overrides };
  }

  managementItemKey(resource, item) {
    return resource.identity.map((key) => String(item?.[key] ?? "")).join("::");
  }

  managementItemByKey(resource, itemKey) {
    return this.state.management.items.find((item) => this.managementItemKey(resource, item) === itemKey) || null;
  }

  managementSourceOperation(resource) {
    return this.operationById(resource.moduleId, resource.sourceOperationId || resource.operations.list);
  }

  removeModuleContexts(openedContexts, moduleId) {
    for (const key of Array.from(openedContexts)) {
      if (key.startsWith(`${moduleId}::`)) {
        openedContexts.delete(key);
      }
    }
  }

  renderSidebarOperationGroup(module, group, surface = "sidebar") {
    const contextKey = this.sidebarContextKey(module.id, group.label);
    const contextId = `openinfra-${surface}-context-${module.id}-${this.slugify(group.label)}`;
    const opened = this.state.openedContexts.has(contextKey);
    return `<section class="openinfra-sidebar-context ${opened ? "open" : ""}" role="group" aria-label="${this.escape(group.label)}">
      <button type="button" class="openinfra-sidebar-context-title ${opened && this.state.activeNavigationModuleId === module.id ? "active" : ""}" data-context-module-id="${this.escape(module.id)}" data-context-label="${this.escape(group.label)}" aria-expanded="${opened ? "true" : "false"}" aria-controls="${this.escape(contextId)}">${this.escape(group.label)}</button>
      <div id="${this.escape(contextId)}" class="openinfra-sidebar-context-panel ${opened ? "show" : ""}" role="region" aria-label="${this.escape(group.label)}">
        <div class="openinfra-sidebar-context-panel-inner">
          ${group.operations.map((operation) => `<button type="button" class="openinfra-sidebar-operation ${this.state.selected.id === operation.id ? "active" : ""}" data-operation-id="${this.escape(operation.id)}" aria-current="${this.state.selected.id === operation.id ? "page" : "false"}">${this.escape(operation.label)}</button>`).join("")}
        </div>
      </div>
    </section>`;
  }

  renderMegaMenu() {
    const module = OPENINFRA_MODULES.find((item) => item.id === this.state.megaMenuModuleId);
    if (!module || module.id === "overview") {
      return "";
    }
    const groups = this.sidebarOperationGroups(module, this.visibleOperations(module));
    return `<section id="openinfra-mega-menu" class="openinfra-mega-menu" aria-label="${this.escape(module.shortLabel || module.label)}">
      <div class="openinfra-mega-menu-header">
        <div>${this.icon(module.icon, "openinfra-mega-menu-icon", 22, 22)}<strong>${this.escape(module.label)}</strong></div>
        <button type="button" id="openinfra-mega-menu-close" class="openinfra-navigation-close" aria-label="${this.escape(this.i18n.t("closeNavigation"))}">×</button>
      </div>
      <div class="openinfra-mega-menu-grid">
        ${groups.map((group) => `<section class="openinfra-mega-menu-group" role="group" aria-label="${this.escape(group.label)}">
          <h2>${this.escape(group.label)}</h2>
          <div>${group.operations.map((operation) => `<button type="button" class="openinfra-sidebar-operation ${this.state.selected.id === operation.id ? "active" : ""}" data-operation-id="${this.escape(operation.id)}" aria-current="${this.state.selected.id === operation.id ? "page" : "false"}">${this.escape(operation.label)}</button>`).join("")}</div>
        </section>`).join("")}
      </div>
    </section>`;
  }

  renderCompactNavigation() {
    if (!this.state.mobileSidebarOpen) {
      return "";
    }
    return `<nav id="openinfra-compact-navigation" class="openinfra-compact-navigation" aria-label="${this.escape(this.i18n.t("navigation"))}">
      <div class="openinfra-compact-navigation-header">
        <strong>${this.escape(this.i18n.t("navigation"))}</strong>
        <button type="button" id="openinfra-compact-navigation-close" class="openinfra-navigation-close" aria-label="${this.escape(this.i18n.t("closeNavigation"))}">×</button>
      </div>
      <div class="openinfra-compact-navigation-body">
        <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("control"))}</div>
        ${this.renderSidebar("compact")}
        <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("runtimeStatus"))}</div>
        ${this.renderRuntimeStatus()}
      </div>
    </nav>`;
  }

  renderRuntimeStatus() {
    const displayedVersion = this.state.version?.version || this.state.config?.version || this.i18n.t("unavailable");
    const protectedForms = this.state.status?.protectedForms === "enabled" ? this.i18n.t("active") : this.i18n.t("configure");
    return `<div class="px-2 small text-muted openinfra-runtime-status" role="status" aria-live="polite" aria-atomic="true">
      <p><span class="openinfra-status-dot ${this.state.ready?.ready === true ? "ready" : "warning"}"></span>${this.escape(this.state.ready?.ready === true ? this.i18n.t("backendReady") : this.i18n.t("backendCheck"))}</p>
      <p>${this.escape(this.i18n.t("version"))} : <strong>${this.escape(displayedVersion)}</strong></p>
      <p>Trust web/backend : <strong>${this.escape(this.state.config?.webBackendTrust || "server-side")}</strong></p>
      <p>${this.escape(this.i18n.t("protectedForms"))} : <strong>${this.escape(protectedForms)}</strong></p>
    </div>`;
  }

  componentModules() {
    return OPENINFRA_MODULES.filter((module) => module.id !== "overview");
  }

  moduleStatistics(module) {
    const base = module.loaded ? {
      operations: module.operations.length,
      readOperations: module.operations.filter((operation) => operation.method === "GET").length,
      fields: module.operations.reduce((total, operation) => total + (operation.query || []).length + (operation.body || []).length, 0),
      requiredFields: module.operations.reduce((total, operation) => total + [...(operation.query || []), ...(operation.body || [])].filter((field) => field?.required).length, 0)
    } : module.stats;
    const operations = base.operations || 0;
    const readOperations = base.readOperations || 0;
    const writeOperations = base.writeOperations ?? operations - readOperations;
    const readPercent = operations === 0 ? 0 : Math.round((readOperations / operations) * 100);
    return { operations, readOperations, writeOperations, fields: base.fields || 0, requiredFields: base.requiredFields || 0, readPercent, writePercent: 100 - readPercent };
  }

  normalizeSearchText(value) {
    return String(value || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  operationSearchHaystack(module, operation) {
    const fields = [...(operation.query || []), ...(operation.body || [])];
    return [
      module.label,
      module.shortLabel,
      module.description,
      operation.id,
      operation.label,
      operation.method,
      operation.path,
      ...fields.flatMap((field) => [field.name, field.label, field.placeholder, field.target])
    ].filter(Boolean).join(" ");
  }

  globalSearchGroups() {
    const query = this.normalizeSearchText(this.state.globalSearchQuery.trim());
    if (!query || !this.searchIndex) return [];
    const byModule = new Map();
    for (const operation of this.searchIndex) {
      const haystack = [operation.moduleLabel, operation.moduleDescription, operation.id, operation.label, operation.method, operation.path].filter(Boolean).join(" ");
      if (!this.normalizeSearchText(haystack).includes(query)) continue;
      if (!byModule.has(operation.moduleId)) byModule.set(operation.moduleId, []);
      byModule.get(operation.moduleId).push(operation);
    }
    return Array.from(byModule.entries()).map(([moduleId, operations]) => ({
      module: OPENINFRA_MODULES.find((module) => module.id === moduleId),
      operations: operations.slice(0, 8),
      total: operations.length
    })).filter((group) => group.module && group.total > 0);
  }

  renderGlobalSearchToolbar() {
    const query = this.state.globalSearchQuery;
    const hasQuery = query.trim() !== "";
    const docs = this.apiDocumentationLinks();
    return `<div class="px-3 py-2 border-bottom openinfra-global-toolbar">
      <div class="container-fluid openinfra-global-toolbar-inner">
        <div class="openinfra-global-toolbar-spacer" aria-hidden="true"></div>
        <form class="openinfra-global-search-form" role="search" aria-label="${this.escape(this.i18n.t("globalSearch"))}" autocomplete="off">
          <label class="visually-hidden" for="openinfra-global-search">${this.escape(this.i18n.t("globalSearch"))}</label>
          <div class="openinfra-global-search-control">
            ${this.icon("search", "openinfra-global-search-icon", 18, 18)}
            <input type="search" id="openinfra-global-search" class="form-control" placeholder="${this.escape(this.i18n.t("globalSearchPlaceholder"))}" aria-label="${this.escape(this.i18n.t("globalSearch"))}" role="combobox" aria-autocomplete="list" aria-haspopup="listbox" aria-controls="openinfra-global-search-results" aria-expanded="${hasQuery ? "true" : "false"}" value="${this.escape(query)}">
          </div>
          <div id="openinfra-global-search-results" class="openinfra-global-search-results" role="listbox" aria-label="${this.escape(this.i18n.t("globalSearchResults"))}" aria-live="polite" aria-atomic="false" aria-busy="${this.state.globalSearchLoading ? "true" : "false"}" ${hasQuery ? "" : "hidden"}>${this.renderGlobalSearchResults()}</div>
        </form>
        <div class="openinfra-toolbar-actions">
          <div class="openinfra-language-control">
            <label for="openinfra-language" class="visually-hidden">${this.i18n.t("language")}</label>
            <select id="openinfra-language" class="form-select form-select-sm" aria-label="${this.escape(this.i18n.t("language"))}">
              <option value="en" ${this.i18n.language === "en" ? "selected" : ""}>EN</option>
              <option value="fr" ${this.i18n.language === "fr" ? "selected" : ""}>FR</option>
            </select>
          </div>
          <div class="text-end openinfra-api-doc-actions">
            <a class="btn btn-light text-dark" href="${this.escape(docs.swaggerUrl)}" target="_blank" rel="noopener noreferrer" aria-label="${this.escape(`${this.i18n.t("openSwagger")} — ${this.i18n.t("opensNewWindow")}`)}">Swagger</a>
            <a class="btn btn-primary" href="${this.escape(docs.redocUrl)}" target="_blank" rel="noopener noreferrer" aria-label="${this.escape(`${this.i18n.t("openRedoc")} — ${this.i18n.t("opensNewWindow")}`)}">ReDoc</a>
          </div>
        </div>
      </div>
    </div>`;
  }

  renderGlobalSearchResults() {
    const query = this.state.globalSearchQuery.trim();
    if (!query) {
      return "";
    }
    const groups = this.globalSearchGroups();
    const backend = this.state.globalSearchBackend;
    if (this.state.globalSearchLoading) {
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("loadingSearch", { query }))}</div>`;
    }
    if (backend && backend.query === query) {
      return this.renderBackendGlobalSearchResults(backend, query, groups);
    }
    if (this.state.globalSearchError) {
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("backendSearchUnavailable"))}</div>${this.renderOperationSearchResults(groups, query)}`;
    }
    return this.renderOperationSearchResults(groups, query);
  }

  renderBackendGlobalSearchResults(backend, query, operationGroups) {
    this.pendingVirtualResults = [];
    const groups = Array.isArray(backend.groups) ? backend.groups : [];
    const visibleGroups = groups.filter((group) => group.status === "ok" && Array.isArray(group.items) && group.items.length > 0);
    const skipped = groups.filter((group) => group.status === "skipped");
    const sections = visibleGroups.map((group, index) => {
      const label = group.label || group.component;
      const title = `<div class="openinfra-global-search-group-title"><span>${this.escape(label)}</span><span>${this.escape(this.i18n.count(group.total, "result", "results"))}</span></div>`;
      let body;
      if (group.items.length > 40) {
        const id = `openinfra-virtual-results-${index}`;
        this.pendingVirtualResults.push({ id, items: group.items, component: group.component, label });
        body = `<div id="${id}" class="openinfra-virtual-results" data-virtual-result-list="true"></div>`;
      } else {
        body = group.items.map((item) => this.renderBackendSearchItem(item, group.component)).join("");
      }
      const more = group.total > group.items.length ? `<div class="openinfra-global-search-more">${this.escape(this.i18n.t(group.total - group.items.length === 1 ? "additionalResults" : "additionalResultsPlural", { count: group.total - group.items.length }))}</div>` : "";
      return `<section class="openinfra-global-search-group" role="group" aria-label="${this.escape(this.i18n.t("globalSearchResults"))} ${this.escape(label)}">${title}${body}${more}</section>`;
    });
    const skippedNotice = skipped.length > 0
      ? `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("skippedComponents", { components: skipped.map((group) => group.label || group.component).join(", ") }))}</div>`
      : "";
    if (sections.length === 0) {
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("noGlobalResult", { query }))}</div>${skippedNotice}${this.renderOperationSearchResults(operationGroups, query)}`;
    }
    return sections.join("") + skippedNotice;
  }

  renderBackendSearchItem(item, component) {
    return `<button type="button" class="openinfra-global-search-item" role="option" aria-selected="false" data-search-route="${this.escape(item.route || "")}"><span>${this.escape(item.label || item.kind || this.i18n.t("result"))}</span><small>${this.escape(item.kind || component)} · ${this.escape(item.description || "")}</small></button>`;
  }

  mountVirtualizedResults() {
    for (const list of this.virtualLists) list.destroy();
    this.virtualLists = [];
    for (const definition of this.pendingVirtualResults || []) {
      const container = document.getElementById(definition.id);
      if (!container) continue;
      const list = new OpenInfraVirtualList(container, {
        items: definition.items,
        ariaLabel: `${this.i18n.t("globalSearchResults")} ${definition.label}`,
        renderItem: (item) => this.renderBackendSearchItem(item, definition.component)
      }).mount();
      container.addEventListener("click", (event) => {
        const button = event.target.closest("[data-search-route]");
        if (button) void this.selectSearchRoute(button.dataset.searchRoute);
      });
      this.virtualLists.push(list);
    }
  }

  renderOperationSearchResults(groups, query) {
    if (groups.length === 0) {
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("noGlobalResult", { query }))}</div>`;
    }
    return groups.map(({ module, operations, total }) => `<section class="openinfra-global-search-group" role="group" aria-label="${this.escape(this.i18n.t("globalSearchResults"))} ${this.escape(module.shortLabel || module.label)}">
      <div class="openinfra-global-search-group-title"><span>${this.escape(module.shortLabel || module.label)}</span><span>${this.escape(this.i18n.count(total, "result", "results"))}</span></div>
      ${operations.map((operation) => `<button type="button" class="openinfra-global-search-item" role="option" aria-selected="false" data-search-operation-id="${this.escape(operation.id)}">
        <span>${this.escape(operation.label)}</span><small>${this.escape(operation.method)} ${this.escape(operation.path)}</small>
      </button>`).join("")}
      ${total > operations.length ? `<div class="openinfra-global-search-more">${this.escape(this.i18n.t(total - operations.length === 1 ? "additionalResults" : "additionalResultsPlural", { count: total - operations.length }))}</div>` : ""}
    </section>`).join("");
  }

  render() {
    const { activeModuleId, activeNavigationModuleId, selected, config, ready, status, version, error, result } = this.state;
    const displayedVersion = version?.version || config?.version || this.i18n.t("unavailable");
    const protectedForms = status?.protectedForms === "enabled" ? this.i18n.t("active") : this.i18n.t("configure");
    const activeModule = OPENINFRA_MODULES.find((module) => module.id === activeModuleId) || OPENINFRA_MODULES[0];
    const pageTitle = activeModuleId === "overview" ? "Dashboard" : activeModule.shortLabel || activeModule.label;
    const pageSubtitle = activeModuleId === "overview"
      ? this.i18n.t("dashboardSubtitle")
      : selected?.managementResourceId
        ? this.i18n.t("managementSubtitle", { operation: selected.label })
        : this.i18n.t("operationSubtitle", { operation: selected.label });
    this.root.innerHTML = `
      <div class="openinfra-skip-links" aria-label="${this.escape(this.i18n.t("accessibilityStatus"))}">
        <a class="openinfra-skip-link" href="#openinfra-main-content">${this.escape(this.i18n.t("skipToContent"))}</a>
        <a class="openinfra-skip-link" href="#openinfra-component-navigation">${this.escape(this.i18n.t("skipToNavigation"))}</a>
        <a class="openinfra-skip-link" href="#openinfra-global-search">${this.escape(this.i18n.t("skipToSearch"))}</a>
      </div>
      <div id="openinfra-live-region" class="openinfra-live-region" role="status" aria-live="polite" aria-atomic="true"></div>
      <header class="openinfra-header-stack" role="banner">
        <div class="px-3 py-2 bg-dark text-white openinfra-top-header">
          <div class="container-fluid">
            <div class="d-flex align-items-center openinfra-top-header-inner">
              <a href="/" class="d-flex align-items-center openinfra-brand-link text-white text-decoration-none" aria-label="${this.escape(this.i18n.t("home"))}">
                <span class="openinfra-brand-mark me-2">OI</span><span class="fs-5 fw-semibold openinfra-brand-name">OpenInfra</span><span class="badge openinfra-edition-badge ms-3">${this.escape(config?.edition || "runtime")}</span>
              </a>
              <nav id="openinfra-component-navigation" class="openinfra-component-navigation" aria-label="${this.escape(this.i18n.t("navigation"))}" aria-describedby="openinfra-component-navigation-instructions">
                <p id="openinfra-component-navigation-instructions" class="openinfra-component-navigation-instructions">${this.escape(this.i18n.t("componentNavigationInstructions"))}</p>
                <ul class="nav justify-content-center text-small openinfra-component-nav">
                  ${OPENINFRA_MODULES.map((module, index) => `
                    <li><button id="openinfra-component-${this.escape(module.id)}" data-component-index="${index}" type="button" class="nav-link border-0 bg-transparent openinfra-component-link ${activeNavigationModuleId === module.id ? "active" : ""}" data-module-id="${this.escape(module.id)}" aria-current="${activeNavigationModuleId === module.id ? "page" : "false"}" ${module.id === "overview" ? "" : `aria-haspopup="true" aria-expanded="${this.state.megaMenuModuleId === module.id ? "true" : "false"}" aria-controls="openinfra-mega-menu"`}>
                      ${this.icon(module.icon, "bi d-block mx-auto mb-1 openinfra-top-icon", 24, 24)}<span>${this.escape(module.shortLabel || module.label)}</span>
                    </button></li>
                  `).join("")}
                </ul>
              </nav>
              <button type="button" id="openinfra-compact-menu-button" class="btn btn-primary openinfra-compact-menu-button" aria-label="${this.escape(this.i18n.t(this.state.mobileSidebarOpen ? "closeNavigation" : "openNavigation"))}" aria-expanded="${this.state.mobileSidebarOpen ? "true" : "false"}" aria-controls="openinfra-compact-navigation">
                ${this.icon("menu", "openinfra-mobile-menu-icon", 20, 20)}<span class="visually-hidden">Menu</span>
              </button>
            </div>
          </div>
        </div>
        ${this.renderGlobalSearchToolbar()}
        ${this.renderMegaMenu()}
        ${this.renderCompactNavigation()}
      </header>
      ${this.state.mobileSidebarOpen || this.state.megaMenuModuleId ? `<button type="button" class="openinfra-navigation-backdrop" id="openinfra-navigation-backdrop" aria-label="${this.escape(this.i18n.t("closeNavigation"))}"></button>` : ""}
      <div class="container-fluid">
        <div class="row">
          <nav id="openinfra-sidebar" class="col-xl-2 openinfra-sidebar" aria-label="${this.escape(this.i18n.t("navigation"))}">
            <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("control"))}</div>
            ${this.renderSidebar()}
            <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("runtimeStatus"))}</div>
            ${this.renderRuntimeStatus()}
          </nav>
          <main id="openinfra-main-content" class="col-xl-10 ms-sm-auto openinfra-main" tabindex="-1">
            <div class="pb-2 mb-3 openinfra-titlebar">
              <h1 class="h2">${this.escape(pageTitle)}</h1><p class="text-muted mb-0">${this.escape(pageSubtitle)}</p>
            </div>
            ${error ? `<div class="alert alert-warning openinfra-error-summary" role="alert" tabindex="-1">${this.escape(error.message)}</div>` : ""}
            ${result && activeModuleId !== "overview" ? `<div class="alert alert-success" role="status">${this.escape(this.i18n.t("success"))}</div>` : ""}
            ${this.renderWorkspace(selected, result, displayedVersion, config, protectedForms)}
          </main>
        </div>
      </div>
    `;
    this.i18n.translateDom(this.root);
    this.syncFixedHeaderOffset();
    this.bindEvents();
    this.focusManagementDialog();
    this.mountVirtualizedResults();
    this.focusMainContentIfRequested();
  }

  focusManagementDialog() {
    const dialog = this.root.querySelector(".openinfra-management-dialog");
    if (!dialog) return;
    const target = dialog.querySelector("input:not([type=hidden]), button, select, textarea");
    target?.focus({ preventScroll: true });
  }

  focusMainContentIfRequested() {
    if (!this.pendingMainFocus) {
      return;
    }
    this.pendingMainFocus = false;
    document.getElementById("openinfra-main-content")?.focus({ preventScroll: false });
  }

  renderWorkspace(selected, result, displayedVersion, config, protectedForms) {
    if (this.state.activeModuleId === "overview") {
      return `${this.renderOverviewRuntimeMetrics(displayedVersion, config, protectedForms)}${this.renderOverviewDashboard()}`;
    }
    if (selected?.managementResourceId) {
      return this.renderManagementWorkspace();
    }
    if (this.state.catalogLoading) {
      return `<section class="card openinfra-operation-card"><div class="card-body"><div class="d-flex align-items-center gap-3" role="status" aria-live="polite"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span><span>${this.escape(this.i18n.t("loadingFormReferences"))}</span></div></div></section>`;
    }
    return `<section class="card openinfra-operation-card"><div class="card-body">${this.renderOperationPanel(selected, result)}</div></section>`;
  }

  renderOverviewRuntimeMetrics(displayedVersion, config, protectedForms) {
    const operationsCount = OPENINFRA_MODULES.reduce((total, module) => total + this.moduleStatistics(module).operations, 0);
    return `<div class="row g-3 mb-4 openinfra-dashboard-metrics" aria-label="${this.escape(this.i18n.t("componentStatistics"))}">
      ${this.metric(this.i18n.t("version"), this.escape(displayedVersion))}
      ${this.metric("API", this.escape(config?.apiBaseUrl || "/api"))}
      ${this.metric(this.i18n.t("trust"), this.escape(config?.webBackendTrust || "server-side"))}
      ${this.metric(this.i18n.t("forms"), this.escape(protectedForms))}
      ${this.metric(this.i18n.t("modules"), `${operationsCount} ${this.i18n.t("operations")}`)}
    </div>`;
  }

  renderOverviewDashboard() {
    const components = this.componentModules();
    const totalOperations = components.reduce((total, module) => total + this.moduleStatistics(module).operations, 0);
    const totalFields = components.reduce((total, module) => total + this.moduleStatistics(module).fields, 0);
    const totalRequiredFields = components.reduce((total, module) => total + this.moduleStatistics(module).requiredFields, 0);
    return `<section class="openinfra-overview" aria-label="${this.escape(this.i18n.t("componentStatistics"))}">
      <div class="card openinfra-overview-summary mb-4">
        <div class="card-body">
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-3">
            <div>
              <h2 class="h4 mb-1">${this.escape(this.i18n.t("overviewTitle"))}</h2>
              <p class="text-muted mb-0">${this.escape(this.i18n.t("overviewDescription"))}</p>
            </div>
            <div class="text-end">
              <span class="badge text-bg-primary">${components.length} ${this.escape(this.i18n.t("components"))}</span>
              <span class="badge text-bg-secondary ms-2">${totalOperations} ${this.escape(this.i18n.t("operations"))}</span>
            </div>
          </div>
          <div class="row g-3 mt-3">
            ${this.metric(this.i18n.t("fields"), String(totalFields))}
            ${this.metric(this.i18n.t("requiredFields"), String(totalRequiredFields))}
            ${this.metric(this.i18n.t("navigationMode"), this.i18n.t("accordions")) }
            ${this.metric(this.i18n.t("browserSecrets"), this.i18n.t("noneExposed"))}
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
            <div class="openinfra-pie-chart" role="img" aria-label="${this.escape(this.i18n.t("distributionChart", { module: module.label, reads: stats.readOperations, mutations: stats.writeOperations }))}" style="--oi-read-end: ${readEnd}; --oi-write-end: ${writeEnd};">
              <span>${stats.operations}</span>
            </div>
            <div class="openinfra-pie-legend small">
              <span><i class="openinfra-legend-read"></i>${stats.readOperations} ${this.escape(this.i18n.t("reads").toLowerCase())}</span>
              <span><i class="openinfra-legend-write"></i>${stats.writeOperations} ${this.escape(this.i18n.t("mutations").toLowerCase())}</span>
            </div>
          </div>
          <div class="row g-2 mt-3 openinfra-component-metrics">
            <div class="col-6"><strong>${stats.operations}</strong><span>${this.escape(this.i18n.t("operations"))}</span></div>
            <div class="col-6"><strong>${stats.fields}</strong><span>${this.escape(this.i18n.t("fields"))}</span></div>
            <div class="col-6"><strong>${stats.requiredFields}</strong><span>${this.escape(this.i18n.t("required"))}</span></div>
            <div class="col-6"><strong>${stats.writeOperations}</strong><span>${this.escape(this.i18n.t("mutations"))}</span></div>
          </div>
        </div>
      </div>
    </article>`;
  }

  renderSidebar(surface = "sidebar") {
    return OPENINFRA_MODULES.map((module) => {
      if (module.id === "overview") {
        return `<button type="button" class="nav-link openinfra-sidebar-dashboard w-100 text-start ${this.state.activeNavigationModuleId === module.id ? "active" : ""}" data-operation-id="${this.escape(module.operations[0].id)}" aria-current="${this.state.activeNavigationModuleId === module.id ? "page" : "false"}">${this.icon(module.icon)}Dashboard</button>`;
      }
      const opened = this.state.openedModules.has(module.id);
      const visibleOperations = this.visibleOperations(module);
      if (module.loaded && visibleOperations.length === 0 && !module.label.toLowerCase().includes(this.state.filter.toLowerCase())) return "";
      return `<section class="openinfra-accordion ${opened ? "open" : ""}">
        <button type="button" id="openinfra-${surface}-accordion-${this.escape(module.id)}" class="openinfra-accordion-toggle ${this.state.activeNavigationModuleId === module.id ? "active" : ""}" data-accordion-id="${this.escape(module.id)}" aria-expanded="${opened ? "true" : "false"}" aria-controls="openinfra-${surface}-panel-${this.escape(module.id)}" aria-current="${this.state.activeNavigationModuleId === module.id ? "page" : "false"}">
          <span>${this.icon(module.icon)}${this.escape(module.shortLabel || module.label)}</span><span class="openinfra-chevron">›</span>
        </button>
        <div id="openinfra-${surface}-panel-${this.escape(module.id)}" class="openinfra-accordion-panel fade ${opened ? "show" : ""}" role="region" aria-labelledby="openinfra-${surface}-accordion-${this.escape(module.id)}">
          <div class="openinfra-accordion-panel-inner">
            ${module.loaded ? this.sidebarOperationGroups(module, visibleOperations).map((group) => this.renderSidebarOperationGroup(module, group, surface)).join("") : `<div class="px-3 py-2 small text-muted" role="status">${this.escape(this.i18n.t("loadingFormReferences"))}</div>`}
          </div>
        </div>
      </section>`;
    }).join("");
  }

  operationNeedsGlobalScopeSelectors(operation) {
    const id = String(operation?.id || "");
    if (id.startsWith("itam-organization") || id.startsWith("itam-partner") || id.startsWith("itam-tenant")) {
      return false;
    }
    return true;
  }

  renderOperationScopeSelectors(operation) {
    if (!this.operationNeedsGlobalScopeSelectors(operation)) {
      return "";
    }
    return `<div class="row g-3 mb-3">${this.renderOrganizationSelector()}${this.renderTenantSelector()}</div>`;
  }

  managementActionOperation() {
    const resource = this.managementResource();
    if (!resource) return null;
    if (this.state.management.mode === "create") return this.managementOperation(resource, "create");
    if (this.state.management.mode === "edit") return this.managementOperation(resource, "update");
    return null;
  }

  managementFormFields(resource, operation, item = null) {
    const fields = [...(operation?.query || []), ...(operation?.body || [])];
    return fields.map((field) => {
      if (!item) return { ...field };
      const value = managementFieldValue(item, field.name);
      if (resource.immutable.includes(field.name)) {
        return { ...field, type: "hidden", defaultValue: value };
      }
      return value === "" ? { ...field } : { ...field, defaultValue: value };
    });
  }

  managementFilteredItems(resource) {
    const query = String(this.state.management.query || "").trim().toLocaleLowerCase(this.i18n.language);
    const activeFilters = this.state.management.filters || {};
    let items = this.state.management.items.filter((item) => {
      if (query) {
        const haystack = Object.values(item || {}).map((value) => {
          if (Array.isArray(value)) return value.join(" ");
          if (value && typeof value === "object") return JSON.stringify(value);
          return String(value ?? "");
        }).join(" ").toLocaleLowerCase(this.i18n.language);
        if (!haystack.includes(query)) return false;
      }
      return Object.entries(activeFilters).every(([key, expected]) => {
        if (expected === undefined || expected === null || String(expected) === "") return true;
        return String(item?.[key] ?? "") === String(expected);
      });
    });
    const sortKey = this.state.management.sortKey || resource.columns[0]?.key;
    const direction = this.state.management.sortDirection === "desc" ? -1 : 1;
    if (sortKey) {
      items = [...items].sort((left, right) => String(left?.[sortKey] ?? "").localeCompare(
        String(right?.[sortKey] ?? ""),
        this.i18n.language,
        { numeric: true, sensitivity: "base" }
      ) * direction);
    }
    return items;
  }

  managementFilterOptions(key) {
    const values = new Set();
    for (const item of this.state.management.items) {
      const value = item?.[key];
      if (value !== undefined && value !== null && String(value) !== "") values.add(String(value));
    }
    return [...values].sort((left, right) => left.localeCompare(right, this.i18n.language, { numeric: true, sensitivity: "base" }));
  }

  managementRenderedValue(value) {
    if (value === true) return this.i18n.t("yes");
    if (value === false) return this.i18n.t("no");
    if (Array.isArray(value)) return value.join(", ") || "—";
    if (value && typeof value === "object") return JSON.stringify(value);
    return value === undefined || value === null || String(value) === "" ? "—" : String(value);
  }

  managementDetailLinkKey(resource) {
    const columnKeys = new Set(resource.columns.map((column) => column.key));
    return resource.display.find((key) => columnKeys.has(key)) || resource.columns[0]?.key;
  }

  renderManagementWorkspace() {
    const resource = this.managementResource();
    if (!resource) {
      return `<section class="card openinfra-operation-card"><div class="card-body"><div class="alert alert-warning" role="alert">${this.escape(this.i18n.t("managementUnavailable"))}</div></div></section>`;
    }
    if (this.state.management.mode === "create" || this.state.management.mode === "edit") {
      return this.renderManagementForm(resource);
    }
    return this.renderManagementList(resource);
  }

  renderManagementList(resource) {
    const filtered = this.managementFilteredItems(resource);
    const pageSize = Number(this.state.management.pageSize) || 25;
    const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
    const page = Math.min(Math.max(1, Number(this.state.management.page) || 1), pageCount);
    const start = (page - 1) * pageSize;
    const visible = filtered.slice(start, start + pageSize);
    const linkKey = this.managementDetailLinkKey(resource);
    const label = localizedManagementLabel(resource, this.i18n.language);
    const plural = localizedManagementLabel(resource, this.i18n.language, "plural");
    const filters = resource.filters.map((filter) => {
      const selected = String(this.state.management.filters?.[filter.key] ?? "");
      const options = this.managementFilterOptions(filter.key);
      return `<label class="form-label openinfra-management-filter"><span>${this.escape(filter.label)}</span><select class="form-select form-select-sm" data-management-filter="${this.escape(filter.key)}"><option value="">${this.escape(this.i18n.t("allValues"))}</option>${options.map((value) => `<option value="${this.escape(value)}" ${selected === value ? "selected" : ""}>${this.escape(this.managementRenderedValue(value))}</option>`).join("")}</select></label>`;
    }).join("");
    const rows = visible.map((item) => {
      const itemKey = this.managementItemKey(resource, item);
      const cells = resource.columns.map((column) => {
        const value = column.key === linkKey && !item?.[column.key] ? managementDisplayName(resource, item) : this.managementRenderedValue(item?.[column.key]);
        if (column.key === linkKey) {
          return `<th scope="row"><button type="button" class="openinfra-management-detail-link" data-management-detail="${this.escape(itemKey)}">${this.escape(value)}</button></th>`;
        }
        return `<td>${this.escape(value)}</td>`;
      }).join("");
      return `<tr>${cells}<td class="openinfra-management-actions"><button type="button" class="btn btn-sm btn-outline-primary" data-management-edit="${this.escape(itemKey)}">${this.escape(this.i18n.t("edit"))}</button><button type="button" class="btn btn-sm btn-outline-danger" data-management-delete="${this.escape(itemKey)}">${this.escape(this.i18n.t("delete"))}</button></td></tr>`;
    }).join("");
    const firstItem = filtered.length === 0 ? 0 : start + 1;
    const lastItem = Math.min(start + pageSize, filtered.length);
    const notice = this.state.management.notice ? `<div class="alert alert-success openinfra-management-notice" role="status">${this.escape(this.state.management.notice)}</div>` : "";
    const error = this.state.management.error ? `<div class="alert alert-warning" role="alert">${this.escape(this.state.management.error.message || this.state.management.error)}</div>` : "";
    const loading = this.state.management.loading ? `<div class="openinfra-management-loading" role="status" aria-live="polite"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span><span>${this.escape(this.i18n.t("loadingManagementData"))}</span></div>` : "";
    return `<section class="card openinfra-operation-card openinfra-management-card" aria-labelledby="openinfra-management-title"><div class="card-body">
      <div class="openinfra-management-heading"><div><p class="openinfra-management-kicker">${this.escape(this.i18n.t("managementWorkspace"))}</p><h2 id="openinfra-management-title" class="h4 mb-1">${this.escape(label)}</h2><p class="text-muted mb-0">${this.escape(this.i18n.t("managementDescription", { resource: plural }))}</p></div><button type="button" id="openinfra-management-new" class="btn btn-primary">+ ${this.escape(this.i18n.t("newItem"))}</button></div>
      ${notice}${error}
      <form id="openinfra-management-filter-form" class="openinfra-management-filter-panel" role="search" aria-label="${this.escape(this.i18n.t("managementFilters"))}">
        <label class="form-label openinfra-management-search"><span>${this.escape(this.i18n.t("search"))}</span><input type="search" class="form-control form-control-sm" id="openinfra-management-query" value="${this.escape(this.state.management.query || "")}" placeholder="${this.escape(this.i18n.t("managementSearchPlaceholder"))}"></label>
        ${filters}
        <label class="form-check openinfra-management-retired"><input class="form-check-input" type="checkbox" id="openinfra-management-include-retired" ${this.state.management.includeRetired ? "checked" : ""}><span class="form-check-label">${this.escape(this.i18n.t("includeRetired"))}</span></label>
        <button type="submit" class="btn btn-sm btn-primary" id="openinfra-management-apply-filters">${this.escape(this.i18n.t("applyFilters"))}</button>
        <button type="button" class="btn btn-sm btn-outline-secondary" id="openinfra-management-reset-filters">${this.escape(this.i18n.t("resetFilters"))}</button>
      </form>
      ${loading}
      <div class="openinfra-management-table-summary"><span>${this.escape(this.i18n.t("managementResults", { count: filtered.length }))}</span><label>${this.escape(this.i18n.t("rowsPerPage"))}<select class="form-select form-select-sm" id="openinfra-management-page-size">${[25, 50, 100].map((size) => `<option value="${size}" ${pageSize === size ? "selected" : ""}>${size}</option>`).join("")}</select></label></div>
      <div class="table-responsive openinfra-management-table-wrapper"><table class="table align-middle openinfra-management-table"><caption class="visually-hidden">${this.escape(label)}</caption><thead><tr>${resource.columns.map((column) => `<th scope="col"><button type="button" class="openinfra-management-sort" data-management-sort="${this.escape(column.key)}">${this.escape(column.label)}${this.state.management.sortKey === column.key ? `<span aria-hidden="true"> ${this.state.management.sortDirection === "desc" ? "↓" : "↑"}</span>` : ""}</button></th>`).join("")}<th scope="col">${this.escape(this.i18n.t("actions"))}</th></tr></thead><tbody>${rows || `<tr><td colspan="${resource.columns.length + 1}" class="text-center text-muted py-4">${this.escape(this.i18n.t("noManagementResults"))}</td></tr>`}</tbody></table></div>
      <div class="openinfra-management-pagination"><span>${this.escape(this.i18n.t("managementRange", { first: firstItem, last: lastItem, total: filtered.length }))}</span><div class="btn-group" role="group" aria-label="${this.escape(this.i18n.t("pagination"))}"><button type="button" class="btn btn-sm btn-outline-secondary" data-management-page="${Math.max(1, page - 1)}" ${page <= 1 ? "disabled" : ""}>${this.escape(this.i18n.t("previous"))}</button><span class="btn btn-sm btn-outline-secondary disabled" aria-current="page">${page} / ${pageCount}</span><button type="button" class="btn btn-sm btn-outline-secondary" data-management-page="${Math.min(pageCount, page + 1)}" ${page >= pageCount ? "disabled" : ""}>${this.escape(this.i18n.t("next"))}</button></div></div>
      ${this.renderManagementDetailDialog(resource)}${this.renderManagementDeleteDialog(resource)}
    </div></section>`;
  }

  renderManagementForm(resource) {
    const operation = this.managementActionOperation();
    if (!operation) return `<section class="card openinfra-operation-card"><div class="card-body"><div class="alert alert-warning" role="alert">${this.escape(this.i18n.t("managementUnavailable"))}</div></div></section>`;
    const editing = this.state.management.mode === "edit";
    const item = editing ? this.state.management.selectedItem : null;
    const fields = this.managementFormFields(resource, operation, item);
    const hasRequiredFields = fields.some((field) => field.required);
    const displayName = item ? managementDisplayName(resource, item) : localizedManagementLabel(resource, this.i18n.language, "singular");
    const title = editing ? this.i18n.t("editManagementItem", { item: displayName }) : this.i18n.t("createManagementItem", { item: localizedManagementLabel(resource, this.i18n.language, "singular") });
    const identitySummary = editing ? `<dl class="openinfra-management-identity">${resource.identity.map((key) => `<div><dt>${this.escape(key)}</dt><dd>${this.escape(this.managementRenderedValue(item?.[key]))}</dd></div>`).join("")}</dl>` : "";
    return `<section class="card openinfra-operation-card openinfra-management-card" aria-labelledby="openinfra-management-form-title"><div class="card-body"><div class="openinfra-management-heading"><div><p class="openinfra-management-kicker">${this.escape(localizedManagementLabel(resource, this.i18n.language))}</p><h2 id="openinfra-management-form-title" class="h4 mb-1">${this.escape(title)}</h2><p class="text-muted mb-0">${this.escape(this.i18n.t(editing ? "editManagementDescription" : "createManagementDescription"))}</p></div><button type="button" id="openinfra-management-back" class="btn btn-outline-secondary">${this.escape(this.i18n.t("backToManagement"))}</button></div>${identitySummary}<form id="openinfra-management-form" novalidate ${hasRequiredFields ? 'aria-describedby="openinfra-required-fields-notice"' : ""}>${hasRequiredFields ? `<p id="openinfra-required-fields-notice" class="openinfra-required-notice">${this.escape(this.i18n.t("requiredFieldsNotice"))}</p>` : ""}${this.renderOperationScopeSelectors(operation)}<div class="row g-3">${fields.map((field) => this.renderField(field)).join("")}</div><div class="openinfra-management-form-actions"><button type="button" class="btn btn-outline-secondary" id="openinfra-management-cancel">${this.escape(this.i18n.t("cancel"))}</button><button type="submit" class="btn btn-primary">${this.escape(editing ? this.i18n.t("saveChanges") : this.i18n.t("create"))}</button></div></form></div></section>`;
  }

  renderManagementDetailDialog(resource) {
    if (!this.state.management.detailItem && !this.state.management.detailLoading) return "";
    const item = this.state.management.detailItem || {};
    const title = managementDisplayName(resource, item);
    const content = this.state.management.detailLoading
      ? `<div class="openinfra-management-loading" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span><span>${this.escape(this.i18n.t("loadingDetails"))}</span></div>`
      : `<dl class="openinfra-management-detail-list">${Object.entries(item).sort(([left], [right]) => left.localeCompare(right)).map(([key, value]) => `<div><dt>${this.escape(key)}</dt><dd>${this.escape(this.managementRenderedValue(value))}</dd></div>`).join("")}</dl>`;
    return `<div class="openinfra-management-modal" role="presentation"><section class="openinfra-management-dialog" role="dialog" aria-modal="true" aria-labelledby="openinfra-management-detail-title"><div class="openinfra-management-dialog-header"><div><p class="openinfra-management-kicker">${this.escape(localizedManagementLabel(resource, this.i18n.language))}</p><h3 id="openinfra-management-detail-title" class="h5 mb-0">${this.escape(title)}</h3></div><button type="button" class="openinfra-navigation-close" data-management-close-dialog aria-label="${this.escape(this.i18n.t("close"))}">×</button></div><div class="openinfra-management-dialog-body">${content}</div><div class="openinfra-management-dialog-footer"><button type="button" class="btn btn-outline-secondary" data-management-close-dialog>${this.escape(this.i18n.t("close"))}</button></div></section></div>`;
  }

  renderManagementDeleteDialog(resource) {
    const item = this.state.management.deleteItem;
    if (!item) return "";
    const displayName = managementDisplayName(resource, item);
    return `<div class="openinfra-management-modal" role="presentation"><section class="openinfra-management-dialog openinfra-management-confirm" role="dialog" aria-modal="true" aria-labelledby="openinfra-management-delete-title"><div class="openinfra-management-dialog-header"><div><p class="openinfra-management-kicker">${this.escape(localizedManagementLabel(resource, this.i18n.language))}</p><h3 id="openinfra-management-delete-title" class="h5 mb-0">${this.escape(this.i18n.t("confirmDeletion"))}</h3></div><button type="button" class="openinfra-navigation-close" data-management-close-delete aria-label="${this.escape(this.i18n.t("close"))}">×</button></div><form id="openinfra-management-delete-form"><div class="openinfra-management-dialog-body"><p>${this.escape(this.i18n.t("deleteManagementConfirmation", { item: displayName }))}</p><p class="small text-muted">${this.escape(this.i18n.t("deleteManagementLifecycleNotice"))}</p><label class="form-label">${this.escape(this.i18n.t("operator"))}<input class="form-control" name="actor" required placeholder="admin@openinfra"></label></div><div class="openinfra-management-dialog-footer"><button type="button" class="btn btn-outline-secondary" data-management-close-delete>${this.escape(this.i18n.t("cancel"))}</button><button type="submit" class="btn btn-danger">${this.escape(this.i18n.t("delete"))}</button></div></form></section></div>`;
  }

  renderOperationPanel(operation, result) {
    const module = this.moduleForOperation(operation);
    const fields = [...(operation.query || []), ...(operation.body || [])];
    const hasRequiredFields = fields.some((field) => field.required);
    return `<div class="row g-4">
      <section class="col-12 col-xxl-8" aria-labelledby="openinfra-operation-title">
        <h2 id="openinfra-operation-title" class="h4">${this.escape(operation.label)}</h2>
        <p class="text-muted">${this.escape(module.description)}</p>
        <form id="openinfra-operation-form" novalidate ${hasRequiredFields ? 'aria-describedby="openinfra-required-fields-notice"' : ""}>
          ${hasRequiredFields ? `<p id="openinfra-required-fields-notice" class="openinfra-required-notice">${this.escape(this.i18n.t("requiredFieldsNotice"))}</p>` : ""}
          ${this.renderOperationScopeSelectors(operation)}
          <div class="row g-3">${fields.map((field) => this.renderField(field)).join("") || `<p>${this.escape(this.i18n.t("noParameters"))}</p>`}</div>
          <button class="btn btn-primary mt-3" type="submit" id="openinfra-execute">${this.escape(this.i18n.t("execute"))}</button>
        </form>
      </section>
      <aside class="col-12 col-xxl-4" aria-labelledby="openinfra-result-title">
        <h3 id="openinfra-result-title" class="h6 text-uppercase text-muted">${this.escape(this.i18n.t("resultTitle"))}</h3>
        ${this.renderGraphResult(operation, result)}
        <details class="openinfra-raw-result" ${result ? "" : "open"}>
          <summary>${this.escape(this.i18n.t("rawResult"))}</summary>
          <pre class="openinfra-result" role="status" aria-live="polite" aria-atomic="true" aria-label="${this.escape(this.i18n.t("operationResult"))}">${this.escape(result ? JSON.stringify(result, null, 2) : this.i18n.t("pendingResult"))}</pre>
        </details>
      </aside>
    </div>`;
  }

  renderGraphResult(operation, result) {
    if (!result || !String(operation?.id || "").startsWith("graph-")) {
      return "";
    }
    if (operation.id === "graph-export") {
      return `<div class="alert alert-success openinfra-download-result" role="status"><strong>${this.escape(this.i18n.t("downloadReady"))}</strong><br>${this.escape(result.filename || "")} · ${this.escape(String(result.size_bytes || 0))} octets</div>`;
    }
    if (operation.id === "graph-spof") {
      return this.renderSpofRanking(result);
    }
    return this.renderDependencyGraph(result);
  }

  renderDependencyGraph(result) {
    const nodes = Array.isArray(result.nodes) ? result.nodes : [];
    const edges = Array.isArray(result.edges) ? result.edges : [];
    if (nodes.length === 0) {
      return `<p class="text-muted">${this.escape(this.i18n.t("noGraphData"))}</p>`;
    }
    const maxVisible = 80;
    const visibleNodes = nodes.slice(0, maxVisible);
    const visibleKeys = new Set(visibleNodes.map((node) => String(node.key || "")));
    const visibleEdges = edges.filter((edge) => visibleKeys.has(String(edge.source_key || "")) && visibleKeys.has(String(edge.target_key || ""))).slice(0, 160);
    const depthGroups = new Map();
    for (const node of visibleNodes) {
      const depth = Number.isFinite(Number(node.depth)) ? Number(node.depth) : 0;
      if (!depthGroups.has(depth)) depthGroups.set(depth, []);
      depthGroups.get(depth).push(node);
    }
    const depths = [...depthGroups.keys()].sort((left, right) => left - right);
    const width = 720;
    const layerGap = Math.max(145, Math.floor(width / Math.max(depths.length, 1)));
    const maxLayer = Math.max(...[...depthGroups.values()].map((group) => group.length), 1);
    const height = Math.max(280, maxLayer * 76 + 56);
    const coordinates = new Map();
    depths.forEach((depth, layerIndex) => {
      const group = depthGroups.get(depth) || [];
      group.sort((left, right) => String(left.key || "").localeCompare(String(right.key || "")));
      group.forEach((node, rowIndex) => {
        coordinates.set(String(node.key || ""), {
          x: 70 + layerIndex * layerGap,
          y: 46 + rowIndex * 76
        });
      });
    });
    const lines = visibleEdges.map((edge) => {
      const source = coordinates.get(String(edge.source_key || ""));
      const target = coordinates.get(String(edge.target_key || ""));
      if (!source || !target) return "";
      return `<line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" marker-end="url(#openinfra-graph-arrow)"><title>${this.escape(edge.relation_type || "relation")}: ${this.escape(edge.source_key || "")} → ${this.escape(edge.target_key || "")}</title></line>`;
    }).join("");
    const circles = visibleNodes.map((node) => {
      const position = coordinates.get(String(node.key || ""));
      const label = String(node.display_name || node.key || "");
      const short = label.length > 16 ? `${label.slice(0, 15)}…` : label;
      const root = String(node.key || "") === String(result.root_key || result.source_key || "");
      return `<g class="openinfra-graph-node${root ? " is-root" : ""}" transform="translate(${position.x},${position.y})" role="listitem" aria-label="${this.escape(`${label}, ${node.resource_type || node.kind || "object"}, profondeur ${node.depth ?? 0}`)}"><circle r="24"></circle><text text-anchor="middle" y="4">${this.escape(short)}</text><title>${this.escape(label)} (${this.escape(node.key || "")})</title></g>`;
    }).join("");
    const omitted = nodes.length - visibleNodes.length;
    return `<section class="openinfra-graph-visualization" aria-labelledby="openinfra-graph-visualization-title"><h4 id="openinfra-graph-visualization-title" class="h6">${this.escape(this.i18n.t("graphVisualization"))}</h4><p class="small text-muted">${this.escape(this.i18n.t("graphVisualizationDescription"))}</p><div class="openinfra-graph-canvas" role="region" aria-label="${this.escape(this.i18n.t("graphVisualization"))}" tabindex="0"><svg viewBox="0 0 ${Math.max(width, 120 + (depths.length - 1) * layerGap)} ${height}" role="img" aria-label="${this.escape(`${nodes.length} nœuds, ${edges.length} relations`)}"><defs><marker id="openinfra-graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z"></path></marker></defs><g class="openinfra-graph-edges">${lines}</g><g class="openinfra-graph-nodes" role="list">${circles}</g></svg></div><ul class="visually-hidden" aria-label="${this.escape(this.i18n.t("graphVisualization"))}">${visibleNodes.map((node) => `<li>${this.escape(`${node.display_name || node.key}, ${node.resource_type || node.kind || "object"}, profondeur ${node.depth ?? 0}`)}</li>`).join("")}</ul>${omitted > 0 ? `<p class="small text-muted">${this.escape(this.i18n.t("graphNodesOmitted", { count: omitted }))}</p>` : ""}</section>`;
  }

  renderSpofRanking(result) {
    const items = Array.isArray(result.items) ? result.items : [];
    const complete = result.complete !== false;
    const rows = items.map((item) => {
      const node = item.node || {};
      const ratio = Math.max(0, Math.min(1, Number(item.affected_ratio || 0)));
      const sample = Array.isArray(item.affected_sample) ? item.affected_sample.join(", ") : "";
      return `<tr><td>${this.escape(item.rank)}</td><th scope="row">${this.escape(node.display_name || node.key || "")}<small>${this.escape(node.key || "")}</small></th><td>${this.escape(item.affected_count)}</td><td>${this.escape(item.direct_affected_count)}</td><td><span class="openinfra-spof-ratio" aria-label="${this.escape(`${Math.round(ratio * 100)} %`)}"><span style="width:${Math.round(ratio * 100)}%"></span></span>${Math.round(ratio * 100)} %</td><td>${this.escape(sample || "—")}</td></tr>`;
    }).join("");
    return `<section class="openinfra-spof-ranking" aria-labelledby="openinfra-spof-ranking-title"><div class="d-flex flex-wrap justify-content-between gap-2"><h4 id="openinfra-spof-ranking-title" class="h6">${this.escape(this.i18n.t("spofRanking"))}</h4><span class="badge ${complete ? "text-bg-success" : "text-bg-warning"}">${this.escape(complete ? this.i18n.t("completeAnalysis") : this.i18n.t("boundedAnalysis"))}</span></div><p class="small text-muted">${this.escape(`${result.spof_count || 0} SPOF · ${result.node_count || 0} nœuds · ${result.edge_count || 0} relations`)}</p><div class="table-responsive"><table class="table table-sm align-middle"><caption class="visually-hidden">${this.escape(this.i18n.t("spofRanking"))}</caption><thead><tr><th scope="col">#</th><th scope="col">${this.escape(this.i18n.t("candidate"))}</th><th scope="col">${this.escape(this.i18n.t("affectedNodes"))}</th><th scope="col">${this.escape(this.i18n.t("directAffected"))}</th><th scope="col">${this.escape(this.i18n.t("impactRatio"))}</th><th scope="col">${this.escape(this.i18n.t("affectedSample"))}</th></tr></thead><tbody>${rows || `<tr><td colspan="6">${this.escape(this.i18n.t("noSpofDetected"))}</td></tr>`}</tbody></table></div></section>`;
  }

  renderField(rawField) {
    const field = normalizeFieldDefinition(rawField);
    const required = field.required ? " required" : "";
    const requiredText = field.required ? `<span class="openinfra-required-marker" aria-hidden="true">*</span><span class="visually-hidden"> (${this.escape(this.i18n.t("requiredIndicator"))})</span>` : "";
    const value = field.defaultValue ?? "";
    const visibility = this.fieldVisibilityAttributes(field);
    const common = ` name="${this.escape(field.name)}" data-field="${this.escape(field.name)}" aria-invalid="false"`;
    if (this.isCountryField(field)) {
      const selected = field.defaultValue || "";
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || "Pays"))}${requiredText}<select class="form-select"${common}${required}><option value=""></option>${this.renderCountryOptionGroups(selected)}</select></label>`;
    }
    if (field.type === "organization-select") {
      const options = this.organizationOptions();
      const fallback = field.defaultValue || this.state.organization || "default";
      const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(field.label || "Organisation")}${requiredText}<select class="form-select"${common}${required}>${this.renderOptions(renderedOptions, fallback)}</select></label>`;
    }
    if (field.type === "partner-select") {
      const options = this.partnerOptions(field.partnerKind || null);
      const fallback = field.defaultValue || "";
      const renderedOptions = options.length > 0 ? options : (fallback ? [{ value: fallback, label: fallback }] : []);
      const selectedValue = renderedOptions.length === 1 ? this.optionValue(renderedOptions[0]) : fallback;
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(field.label || "Partenaire")}${requiredText}<select class="form-select"${common}${required}><option value=""></option>${this.renderOptions(renderedOptions, selectedValue)}</select></label>`;
    }
    if (field.type === "hidden") {
      return `<input type="hidden"${common} value="${this.escape(value)}">`;
    }
    if (field.type === "file") {
      const attributes = inputAttributesForField(field);
      const accept = attributes.accept ? ` accept="${this.escape(attributes.accept)}"` : "";
      const capture = attributes.capture ? ` capture="${this.escape(attributes.capture)}"` : "";
      return `<label${visibility} class="col-12 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<input class="form-control" type="file"${common}${accept}${capture}${required}><span class="form-text">JPEG, PNG, WebP ou PDF — 2 Mio maximum.</span></label>`;
    }
    if (field.type === "tenant-select") {
      const options = this.tenantOptions();
      const fallback = field.defaultValue || this.state.tenant || this.state.organization || "default";
      const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || "Filiale/Subdivision"))}${requiredText}<select class="form-select"${common}${required}>${this.renderOptions(renderedOptions, field.defaultValue || this.state.tenant || fallback)}</select></label>`;
    }
    if (this.isDcimReferenceField(field)) {
      const options = this.dcimOptions(field);
      const fallback = field.defaultValue || "";
      const renderedOptions = options.length > 0 ? options : (fallback ? [{ value: fallback, label: fallback }] : []);
      const selectedValue = renderedOptions.length === 1 ? this.optionValue(renderedOptions[0]) : fallback;
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || DCIM_REFERENCE_LABELS[this.dcimReferenceLevel(field)] || field.name))}${requiredText}<select class="form-select"${common}${required}><option value=""></option>${this.renderOptions(renderedOptions, selectedValue)}</select></label>`;
    }
    if (field.type === "select") {
      const options = this.selectOptionsForField(field);
      const source = field.optionsByField ? ` data-options-by-field="${this.escape(field.optionsByField)}"` : "";
      const map = field.optionsMap ? ` data-options-map="${this.escape(JSON.stringify(field.optionsMap))}"` : "";
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<select class="form-select"${common}${source}${map}${required}><option value=""></option>${this.renderOptions(options, value)}</select></label>`;
    }
    if (field.type === "boolean") {
      const defaultBoolean = field.defaultValue === true || String(field.defaultValue).toLowerCase() === "true";
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || field.name))}<select class="form-select"${common}><option value="false"${defaultBoolean ? "" : " selected"}>${this.escape(this.i18n.t("no"))}</option><option value="true"${defaultBoolean ? " selected" : ""}>${this.escape(this.i18n.t("yes"))}</option></select></label>`;
    }
    const attributes = inputAttributesForField(field);
    const htmlAttributes = Object.entries(attributes).map(([key, attributeValue]) => {
      if (attributeValue === undefined || attributeValue === null || attributeValue === false) {
        return "";
      }
      const htmlName = { maxLength: "maxlength", inputMode: "inputmode", autoComplete: "autocomplete" }[key] || key;
      return attributeValue === true ? ` ${htmlName}` : ` ${htmlName}="${this.escape(attributeValue)}"`;
    }).join("");
    if (field.type === "textarea" || field.type === "json") {
      return `<label${visibility} class="col-12 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<textarea class="form-control font-monospace" rows="10"${common} placeholder="${this.escape(this.i18n.label(field.placeholder || ""))}"${htmlAttributes}${required}>${this.escape(value)}</textarea></label>`;
    }
    const inputType = inputTypeForField(field);
    return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<input class="form-control" type="${this.escape(inputType)}"${common} value="${this.escape(value)}" placeholder="${this.escape(this.i18n.label(field.placeholder || ""))}"${htmlAttributes}${required}></label>`;
  }

  fieldVisibilityAttributes(field) {
    if (!field.visibleWhen) {
      return "";
    }
    return ` data-visible-when-field="${this.escape(field.visibleWhen.field)}" data-visible-when-value="${this.escape(field.visibleWhen.value)}"`;
  }

  isCountryField(field) {
    const normalized = String(field.name || "").toLowerCase();
    return field.type === "country-select" || normalized === "country" || normalized === "country_code";
  }

  renderCountryOptionGroups(selectedValue = "") {
    const groups = Array.isArray(this.state.countryCatalog?.items) ? this.state.countryCatalog.items : [];
    if (groups.length === 0) {
      return this.renderOptions([
        { value: "FR", label: this.i18n.countryName("FR", "France") },
        { value: "GB", label: this.i18n.countryName("GB", "United Kingdom") },
        { value: "US", label: this.i18n.countryName("US", "United States") }
      ], selectedValue);
    }
    return groups.map((group) => {
      const continent = this.escape(this.i18n.continentName(group.continent));
      const countries = Array.isArray(group.countries) ? group.countries : [];
      const options = countries.map((country) => {
        const code = String(country.code || "");
        const label = this.i18n.countryName(code, country.name || code);
        return `<option value="${this.escape(code)}" ${selectedValue === code ? "selected" : ""}>${this.escape(label)}</option>`;
      }).join("");
      return `<optgroup label="${continent}">${options}</optgroup>`;
    }).join("");
  }

  dcimReferenceLevel(field) {
    const name = String(field.name || "").toLowerCase();
    const normalized = name.replace(/_code$/, "");
    if (["site"].includes(normalized)) return "site";
    if (["building"].includes(normalized)) return "building";
    if (["floor"].includes(normalized)) return "floor";
    if (["room"].includes(normalized)) return "room";
    if (["zone"].includes(normalized)) return "zone";
    if (["rack"].includes(normalized)) return "rack";
    if (["row", "line"].includes(normalized)) return "row";
    if (["column"].includes(normalized)) return "column";
    return normalized;
  }

  isDcimReferenceField(field) {
    return DCIM_REFERENCE_FIELDS.has(String(field.name || "").toLowerCase());
  }

  dcimOptions(field) {
    const level = this.dcimReferenceLevel(field);
    const sites = Array.isArray(this.state.dcimCatalog?.sites) ? this.state.dcimCatalog.sites : [];
    const options = [];
    const seen = new Set();
    const selectable = (item) => item && item.selectable !== false && item.status !== "retired";
    const push = (value, label) => {
      const normalized = String(value || "").trim();
      if (!normalized || seen.has(`${level}:${normalized}`)) {
        return;
      }
      seen.add(`${level}:${normalized}`);
      options.push({ value: normalized, label: label || normalized });
    };
    for (const site of sites) {
      if (!selectable(site)) {
        continue;
      }
      const siteCode = site.code;
      if (level === "site") {
        push(siteCode, `${site.code}${site.name ? ` — ${site.name}` : ""}`);
      }
      for (const building of Array.isArray(site.buildings) ? site.buildings : []) {
        if (!selectable(building)) {
          continue;
        }
        const buildingCode = building.code;
        if (level === "building") {
          push(buildingCode, `${building.code}${building.name ? ` — ${building.name}` : ""} (${siteCode})`);
        }
        for (const floor of Array.isArray(building.floors) ? building.floors : []) {
          if (!selectable(floor)) {
            continue;
          }
          if (level === "floor") {
            push(floor.code, `${floor.code} — ${this.i18n.floorName(floor.level_index, floor.name)} (${siteCode}/${buildingCode})`);
          }
        }
        for (const room of Array.isArray(building.rooms) ? building.rooms : []) {
          if (!selectable(room)) {
            continue;
          }
          const roomCode = room.code;
          if (level === "room") {
            push(roomCode, `${room.code}${room.name ? ` — ${room.name}` : ""} (${siteCode}/${buildingCode})`);
          }
          for (const zone of Array.isArray(room.zones) ? room.zones : []) {
            if (selectable(zone) && level === "zone") {
              push(zone.code, `${zone.code}${zone.name ? ` — ${zone.name}` : ""} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
          for (const rack of Array.isArray(room.racks) ? room.racks : []) {
            const rackCode = rack.code || rack.rack || rack.name;
            if (selectable(rack) && level === "rack") {
              push(rackCode, `${rackCode}${rack.label ? ` — ${rack.label}` : ""} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
          for (const row of Array.isArray(room.rows) ? room.rows : []) {
            if (level === "row") {
              push(row, `${row} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
          for (const column of Array.isArray(room.columns) ? room.columns : []) {
            if (level === "column") {
              push(column, `${column} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
        }
      }
    }
    return options;
  }

  selectOptionsForField(field) {
    if (!field.optionsByField || !field.optionsMap) {
      return field.options || [];
    }
    const controller = field.defaultControllerValue || this.optionValue((field.controllerOptions || [])[0]) || Object.keys(field.optionsMap)[0];
    return field.optionsMap[controller] || [];
  }

  renderOptions(options, selectedValue = "") {
    return options.map((option) => {
      const value = this.optionValue(option);
      const label = this.optionLabel(option);
      return `<option value="${this.escape(value)}" ${selectedValue === value ? "selected" : ""}>${this.escape(label)}</option>`;
    }).join("");
  }

  optionValue(option) {
    if (option && typeof option === "object" && Object.hasOwn(option, "value")) {
      return String(option.value);
    }
    return String(option || "");
  }

  optionLabel(option) {
    if (option && typeof option === "object" && Object.hasOwn(option, "label")) {
      return this.i18n.label(String(option.label));
    }
    return this.i18n.optionLabel(String(option || ""));
  }

  bindDependentSelects() {
    for (const dependent of document.querySelectorAll("select[data-options-by-field]")) {
      const source = document.querySelector(`[data-field="${dependent.dataset.optionsByField}"]`);
      if (!source) {
        continue;
      }
      const refresh = () => {
        const selected = dependent.value;
        const optionsMap = JSON.parse(dependent.dataset.optionsMap || "{}");
        const options = optionsMap[source.value] || [];
        dependent.innerHTML = `<option value=""></option>${this.renderOptions(options, selected)}`;
        if (options.some((option) => this.optionValue(option) === selected)) {
          dependent.value = selected;
        } else if (options.length === 1) {
          dependent.value = this.optionValue(options[0]);
        }
      };
      source.addEventListener("change", refresh);
      refresh();
    }
  }

  bindConditionalFields() {
    for (const target of document.querySelectorAll("[data-visible-when-field]")) {
      const source = document.querySelector(`[data-field="${target.dataset.visibleWhenField}"]`);
      if (!source) {
        continue;
      }
      const refresh = () => {
        const visible = source.value === target.dataset.visibleWhenValue;
        target.hidden = !visible;
        for (const input of target.querySelectorAll("[data-field]")) {
          input.disabled = !visible;
        }
      };
      source.addEventListener("change", refresh);
      refresh();
    }
  }

  operationFieldDefinitions() {
    const operation = this.managementActionOperation() || this.state.selected || {};
    return [...(operation.query || []), ...(operation.body || [])].map((field, index) => normalizeFieldDefinition(field, index));
  }

  validateOperationForm(form) {
    const fields = this.operationFieldDefinitions();
    const countryCode = formCountryCode(form);
    let valid = true;
    for (const field of fields) {
      const control = [...form.querySelectorAll("[data-field]")].find((candidate) => candidate.dataset.field === field.name);
      if (!control || control.disabled) {
        continue;
      }
      if (field.type === "file") {
        const file = control.files?.[0];
        const accepted = new Set(["image/jpeg", "image/png", "image/webp", "application/pdf"]);
        let message = "";
        if (file && file.size > 2 * 1024 * 1024) {
          message = "Le fichier dépasse la limite de 2 Mio.";
        } else if (file && !accepted.has(file.type)) {
          message = "Le format de fichier n’est pas autorisé.";
        }
        control.setCustomValidity(message);
        valid = valid && !message;
      } else if (!validateControl(control, field, this.i18n, { countryCode })) {
        valid = false;
      }
    }
    for (const control of form.querySelectorAll("input, select, textarea")) {
      const controlValid = control.disabled || control.checkValidity();
      control.setAttribute("aria-invalid", controlValid ? "false" : "true");
      valid = valid && controlValid;
    }
    return valid;
  }

  bindOperationFieldValidation() {
    const form = document.getElementById("openinfra-operation-form") || document.getElementById("openinfra-management-form");
    if (!form) {
      return;
    }
    const fieldMap = new Map(this.operationFieldDefinitions().map((field) => [field.name, field]));
    const validateOne = (control) => {
      const field = fieldMap.get(control.dataset.field);
      if (field && !control.disabled) {
        if (field.type === "file") {
          control.setCustomValidity("");
          control.setAttribute("aria-invalid", "false");
        } else {
          validateControl(control, field, this.i18n, { countryCode: formCountryCode(form) });
        }
      }
    };
    const validateAll = () => {
      for (const control of form.querySelectorAll("[data-field]")) {
        validateOne(control);
      }
    };
    for (const control of form.querySelectorAll("[data-field]")) {
      control.addEventListener("input", () => validateOne(control));
      control.addEventListener("change", () => {
        validateOne(control);
        if (["country", "country_code"].includes(control.dataset.field)) {
          validateAll();
        }
      });
      control.addEventListener("blur", () => validateOne(control));
    }
  }

  bindEvents() {
    this.bindConditionalFields();
    this.bindOperationFieldValidation();
    document.getElementById("openinfra-language")?.addEventListener("change", (event) => {
      this.setLanguage(event.target.value);
    });
    document.getElementById("openinfra-operation-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = event.currentTarget;
      if (!this.validateOperationForm(form)) {
        form.reportValidity();
        return;
      }
      this.executeSelected();
    });
    document.getElementById("openinfra-management-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.executeManagementForm();
    });
    document.getElementById("openinfra-management-new")?.addEventListener("click", () => {
      const resource = this.managementResource();
      if (resource) void this.selectManagementResource(resource.id, { mode: "create", focusMain: true });
    });
    for (const id of ["openinfra-management-back", "openinfra-management-cancel"]) {
      document.getElementById(id)?.addEventListener("click", () => {
        const resource = this.managementResource();
        if (resource) void this.selectManagementResource(resource.id, { mode: "list", focusMain: true });
      });
    }
    document.getElementById("openinfra-management-filter-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const filters = {};
      for (const select of event.currentTarget.querySelectorAll("[data-management-filter]")) {
        filters[select.dataset.managementFilter] = select.value;
      }
      const includeRetired = Boolean(document.getElementById("openinfra-management-include-retired")?.checked);
      const includeChanged = includeRetired !== this.state.management.includeRetired;
      this.state = {
        ...this.state,
        management: this.withManagementState({
          query: document.getElementById("openinfra-management-query")?.value || "",
          filters,
          includeRetired,
          page: 1,
          notice: null
        })
      };
      if (includeChanged) void this.loadManagementItems();
      else this.render();
    });
    document.getElementById("openinfra-management-reset-filters")?.addEventListener("click", () => {
      const includeChanged = this.state.management.includeRetired;
      this.state = {
        ...this.state,
        management: this.withManagementState({ query: "", filters: {}, includeRetired: false, page: 1, notice: null })
      };
      if (includeChanged) void this.loadManagementItems();
      else this.render();
    });
    document.getElementById("openinfra-management-page-size")?.addEventListener("change", (event) => {
      this.state = { ...this.state, management: this.withManagementState({ pageSize: Number(event.target.value) || 25, page: 1 }) };
      this.render();
    });
    for (const button of document.querySelectorAll("[data-management-page]")) {
      button.addEventListener("click", () => {
        this.state = { ...this.state, management: this.withManagementState({ page: Number(button.dataset.managementPage) || 1 }) };
        this.render();
      });
    }
    for (const button of document.querySelectorAll("[data-management-sort]")) {
      button.addEventListener("click", () => {
        const sortKey = button.dataset.managementSort;
        const sortDirection = this.state.management.sortKey === sortKey && this.state.management.sortDirection === "asc" ? "desc" : "asc";
        this.state = { ...this.state, management: this.withManagementState({ sortKey, sortDirection, page: 1 }) };
        this.render();
      });
    }
    const managementResource = this.managementResource();
    if (managementResource) {
      for (const button of document.querySelectorAll("[data-management-detail]")) {
        button.addEventListener("click", () => {
          const item = this.managementItemByKey(managementResource, button.dataset.managementDetail);
          if (item) void this.openManagementDetail(item);
        });
      }
      for (const button of document.querySelectorAll("[data-management-edit]")) {
        button.addEventListener("click", () => {
          const item = this.managementItemByKey(managementResource, button.dataset.managementEdit);
          if (item) void this.selectManagementResource(managementResource.id, { mode: "edit", item, focusMain: true });
        });
      }
      for (const button of document.querySelectorAll("[data-management-delete]")) {
        button.addEventListener("click", () => {
          const item = this.managementItemByKey(managementResource, button.dataset.managementDelete);
          if (!item) return;
          this.state = { ...this.state, management: this.withManagementState({ deleteItem: item, detailItem: null, detailLoading: false }) };
          this.render();
        });
      }
    }
    for (const button of document.querySelectorAll("[data-management-close-dialog], [data-management-close-delete]")) {
      button.addEventListener("click", () => this.closeManagementDialogs());
    }
    document.getElementById("openinfra-management-delete-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.executeManagementDelete(event.currentTarget);
    });
    document.getElementById("openinfra-organization")?.addEventListener("change", async (event) => {
      const organization = event.target.value;
      const tenant = this.tenantOptions(organization)[0]?.value || organization;
      this.state = { ...this.state, organization, tenant };
      await this.refreshTenantCatalog();
      await this.refreshPartnerCatalog();
      await this.refreshDcimCatalog();
      this.render();
    });
    document.getElementById("openinfra-tenant")?.addEventListener("input", (event) => {
      this.state = { ...this.state, tenant: event.target.value };
    });
    document.getElementById("openinfra-tenant")?.addEventListener("change", async (event) => {
      this.state = { ...this.state, tenant: event.target.value };
      await this.refreshDcimCatalog();
      this.render();
    });
    for (const selector of document.querySelectorAll('select[data-field="organization_id"]')) {
      selector.addEventListener("change", async (event) => {
        const organization = event.target.value;
        const tenant = this.tenantOptions(organization)[0]?.value || organization;
        this.state = { ...this.state, organization, tenant };
        await this.refreshTenantCatalog();
        await this.refreshPartnerCatalog();
        await this.refreshDcimCatalog();
        this.render();
      });
    }
    for (const selector of document.querySelectorAll('select[data-field="tenant_id"]')) {
      selector.addEventListener("change", (event) => {
        this.state = { ...this.state, tenant: event.target.value };
      });
    }
    const globalSearchInput = document.getElementById("openinfra-global-search");
    globalSearchInput?.addEventListener("input", (event) => this.updateGlobalSearch(event.target.value));
    globalSearchInput?.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        this.updateGlobalSearch("");
      }
    });
    this.bindSearchResultButtons();
    this.bindDependentSelects();
    document.getElementById("openinfra-compact-menu-button")?.addEventListener("click", () => {
      this.state = { ...this.state, mobileSidebarOpen: !this.state.mobileSidebarOpen, megaMenuModuleId: null };
      this.render();
    });
    document.getElementById("openinfra-navigation-backdrop")?.addEventListener("click", () => this.closeResponsiveNavigation());
    document.getElementById("openinfra-mega-menu-close")?.addEventListener("click", () => this.closeResponsiveNavigation(true));
    document.getElementById("openinfra-compact-navigation-close")?.addEventListener("click", () => this.closeResponsiveNavigation(true));
    const componentButtons = Array.from(document.querySelectorAll("[data-module-id]"));
    componentButtons.forEach((button, index) => {
      button.addEventListener("mouseenter", () => this.openMegaMenu(button.dataset.moduleId, button));
      button.addEventListener("focus", () => this.openMegaMenu(button.dataset.moduleId, button));
      button.addEventListener("click", () => {
        this.lastNavigationModuleId = button.dataset.moduleId;
        this.handleModuleNavigation(button.dataset.moduleId);
      });
      button.addEventListener("keydown", (event) => {
        const focusAt = (targetIndex) => componentButtons[targetIndex]?.focus();
        if (event.key === "ArrowRight") {
          event.preventDefault();
          focusAt((index + 1) % componentButtons.length);
        } else if (event.key === "ArrowLeft") {
          event.preventDefault();
          focusAt((index - 1 + componentButtons.length) % componentButtons.length);
        } else if (event.key === "Home") {
          event.preventDefault();
          focusAt(0);
        } else if (event.key === "End") {
          event.preventDefault();
          focusAt(componentButtons.length - 1);
        } else if (event.key === "ArrowDown" && button.dataset.moduleId !== "overview") {
          event.preventDefault();
          this.openMegaMenu(button.dataset.moduleId, button);
          window.requestAnimationFrame(() => document.querySelector(".openinfra-mega-menu .openinfra-sidebar-operation")?.focus());
        }
      });
    });
    for (const button of document.querySelectorAll("[data-accordion-id]")) {
      button.addEventListener("click", () => this.toggleAccordion(button.dataset.accordionId));
    }
    for (const button of document.querySelectorAll("[data-context-module-id]")) {
      button.addEventListener("click", () => this.toggleSidebarContext(button.dataset.contextModuleId, button.dataset.contextLabel));
    }
    for (const button of document.querySelectorAll("[data-operation-id]")) {
      button.addEventListener("click", () => this.selectOperation(button.dataset.operationId));
    }
  }

  updateGlobalSearch(value) {
    this.state = { ...this.state, globalSearchQuery: value };
    const input = document.getElementById("openinfra-global-search");
    const results = document.getElementById("openinfra-global-search-results");
    const hasQuery = value.trim() !== "";
    if (input) {
      input.setAttribute("aria-expanded", hasQuery ? "true" : "false");
      input.value = value;
    }
    if (results) {
      results.hidden = !hasQuery;
      results.innerHTML = this.renderGlobalSearchResults();
      this.bindSearchResultButtons();
    }
    if (hasQuery && !this.searchIndex) {
      void this.loadSearchIndex().then(() => {
        if (this.state.globalSearchQuery === value) this.updateGlobalSearch(value);
      }).catch(() => {
        this.state = { ...this.state, globalSearchError: "search_index_unavailable" };
      });
    }
    void this.refreshBackendGlobalSearch(value);
  }

  async refreshBackendGlobalSearch(value) {
    const query = value.trim();
    if (query.length < 2) {
      this.queryCache.abort("global-search");
      this.state = { ...this.state, globalSearchBackend: null, globalSearchLoading: false, globalSearchError: null };
      return;
    }
    this.state = { ...this.state, globalSearchLoading: true, globalSearchError: null };
    try {
      const payload = await this.queryCache.run(`global-search:${this.state.tenant}:${query}`, async (signal) => {
        const response = await fetch(this.globalSearchUrl(query, 80), { credentials: "same-origin", headers: { Accept: "application/json" }, signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      }, { ttlMs: 15_000, scope: "global-search" });
      if (this.state.globalSearchQuery.trim() !== query) return;
      this.state = { ...this.state, globalSearchBackend: payload, globalSearchLoading: false, globalSearchError: null };
    } catch (error) {
      if (error?.name === "AbortError" || this.state.globalSearchQuery.trim() !== query) return;
      this.state = { ...this.state, globalSearchBackend: null, globalSearchLoading: false, globalSearchError: "backend_unavailable" };
    }
    const results = document.getElementById("openinfra-global-search-results");
    if (results && this.state.globalSearchQuery.trim() === query) {
      results.innerHTML = this.renderGlobalSearchResults();
      this.bindSearchResultButtons();
      this.mountVirtualizedResults();
    }
  }

  bindSearchResultButtons() {
    for (const button of document.querySelectorAll("[data-search-operation-id]")) {
      button.addEventListener("click", () => this.selectSearchOperation(button.dataset.searchOperationId));
    }
    for (const button of document.querySelectorAll("[data-search-route]")) {
      button.addEventListener("click", () => this.selectSearchRoute(button.dataset.searchRoute));
    }
  }

  async toggleAccordion(moduleId) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) return;
    const wasOpen = this.state.openedModules.has(moduleId);
    this.state = { ...this.state, activeNavigationModuleId: module.id, openedModules: wasOpen ? new Set() : new Set([moduleId]), openedContexts: new Set() };
    this.render();
    if (!wasOpen && !module.loaded) {
      try { await this.ensureModuleLoaded(moduleId); } catch (error) { this.state = { ...this.state, error }; }
      this.render();
    }
  }

  toggleSidebarContext(moduleId, contextLabel) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module || !contextLabel) {
      return;
    }
    const contextKey = this.sidebarContextKey(moduleId, contextLabel);
    const wasOpen = this.state.openedContexts.has(contextKey);
    const openedContexts = new Set();
    if (!wasOpen) {
      openedContexts.add(contextKey);
    }
    this.state = {
      ...this.state,
      activeNavigationModuleId: module.id,
      openedModules: new Set([moduleId]),
      openedContexts
    };
    this.render();
  }

  async selectManagementResource(resourceId, { mode = "list", item = null, focusMain = false } = {}) {
    const resource = managementResourceById(resourceId);
    if (!resource) return;
    let module = OPENINFRA_MODULES.find((candidate) => candidate.id === resource.moduleId);
    if (!module) return;
    if (!module.loaded) {
      module = await this.ensureModuleLoaded(module.id);
    }
    const selected = managementNavigationOperation(resource, this.i18n.language);
    const openedModules = new Set([module.id]);
    const openedContexts = new Set();
    const context = this.contextForOperation(module, selected.id);
    if (context) openedContexts.add(this.sidebarContextKey(module.id, context.label));
    const sameResource = this.state.management.resourceId === resource.id;
    const management = {
      resourceId: resource.id,
      mode,
      items: sameResource ? this.state.management.items : [],
      loading: false,
      error: null,
      filters: sameResource ? this.state.management.filters : {},
      query: sameResource ? this.state.management.query : "",
      includeRetired: sameResource ? this.state.management.includeRetired : false,
      sortKey: sameResource ? this.state.management.sortKey : resource.columns[0]?.key || null,
      sortDirection: sameResource ? this.state.management.sortDirection : "asc",
      page: 1,
      pageSize: sameResource ? this.state.management.pageSize : 25,
      selectedItem: item,
      detailItem: null,
      detailLoading: false,
      deleteItem: null,
      notice: mode === "list" && sameResource ? this.state.management.notice : null
    };
    const actionOperation = mode === "create"
      ? this.managementOperation(resource, "create")
      : mode === "edit"
        ? this.managementOperation(resource, "update")
        : null;
    const catalogLoading = Boolean(actionOperation && this.operationCatalogsNeedLoading(actionOperation));
    this.state = {
      ...this.state,
      activeModuleId: module.id,
      activeNavigationModuleId: module.id,
      selected,
      openedModules,
      openedContexts,
      result: null,
      error: null,
      catalogLoading,
      mobileSidebarOpen: false,
      megaMenuModuleId: null,
      management
    };
    this.pendingMainFocus = focusMain;
    this.render();
    if (actionOperation && catalogLoading) {
      await this.loadCatalogsForOperation(actionOperation);
    }
    if (mode === "list") {
      await this.loadManagementItems();
    }
  }

  async loadManagementItems() {
    const resource = this.managementResource();
    if (!resource) return;
    const operation = this.managementSourceOperation(resource);
    if (!operation) {
      this.state = { ...this.state, management: this.withManagementState({ loading: false, error: new Error(this.i18n.t("managementUnavailable")) }) };
      this.render();
      return;
    }
    this.state = { ...this.state, management: this.withManagementState({ loading: true, error: null }) };
    this.render();
    try {
      const payload = { include_retired: this.state.management.includeRetired ? "true" : "false" };
      const data = await this.client().request(operation, payload);
      const items = flattenManagementCollection(resource, data);
      if (resource.moduleId === "dcim" && resource.sourceOperationId === "dcim-topology-catalog") {
        this.state = { ...this.state, dcimCatalog: data };
      }
      this.state = {
        ...this.state,
        management: this.withManagementState({ items, loading: false, error: null, page: 1 })
      };
    } catch (error) {
      this.state = { ...this.state, management: this.withManagementState({ loading: false, error }) };
    }
    this.render();
  }

  async openManagementDetail(item) {
    const resource = this.managementResource();
    if (!resource || !item) return;
    const detailOperation = this.managementOperation(resource, "detail");
    this.state = { ...this.state, management: this.withManagementState({ detailItem: item, detailLoading: Boolean(detailOperation) }) };
    this.render();
    if (!detailOperation) return;
    try {
      const detail = await this.client().request(detailOperation, managementIdentityPayload(resource, item));
      this.state = { ...this.state, management: this.withManagementState({ detailItem: detail, detailLoading: false }) };
    } catch (error) {
      this.state = { ...this.state, management: this.withManagementState({ detailLoading: false, error }) };
    }
    this.render();
  }

  closeManagementDialogs() {
    this.state = {
      ...this.state,
      management: this.withManagementState({ detailItem: null, detailLoading: false, deleteItem: null })
    };
    this.render();
  }

  async executeManagementForm() {
    const resource = this.managementResource();
    const operation = this.managementActionOperation();
    const form = document.getElementById("openinfra-management-form");
    if (!resource || !operation || !form) return;
    if (!this.validateOperationForm(form)) {
      form.reportValidity();
      return;
    }
    try {
      const payload = {};
      for (const input of form.querySelectorAll("[data-field]")) {
        if (input.disabled) continue;
        if (input.type === "file") {
          const file = input.files?.[0];
          payload[input.dataset.field] = file ? await this.filePayload(file) : undefined;
        } else {
          payload[input.dataset.field] = input.value;
        }
      }
      await this.client().request(operation, payload);
      await this.refreshManagementReferenceCatalogs(operation);
      const notice = this.i18n.t(this.state.management.mode === "create" ? "managementCreated" : "managementUpdated");
      this.state = {
        ...this.state,
        management: this.withManagementState({ mode: "list", selectedItem: null, notice, error: null })
      };
      await this.loadManagementItems();
    } catch (error) {
      this.state = { ...this.state, management: this.withManagementState({ error }) };
      this.render();
    }
  }

  async executeManagementDelete(form) {
    const resource = this.managementResource();
    const item = this.state.management.deleteItem;
    const operation = this.managementOperation(resource, "delete");
    if (!resource || !item || !operation || !form.checkValidity()) {
      form.reportValidity();
      return;
    }
    try {
      const payload = {
        ...managementIdentityPayload(resource, item),
        actor: String(new FormData(form).get("actor") || "")
      };
      await this.client().request(operation, payload);
      await this.refreshManagementReferenceCatalogs(operation);
      this.state = {
        ...this.state,
        management: this.withManagementState({ deleteItem: null, notice: this.i18n.t("managementDeleted"), error: null })
      };
      await this.loadManagementItems();
    } catch (error) {
      this.state = { ...this.state, management: this.withManagementState({ error }) };
      this.render();
    }
  }

  async refreshManagementReferenceCatalogs(operation) {
    this.queryCache.invalidate("catalog:");
    this.queryCache.invalidate("global-search:");
    if (operation.id.startsWith("itam-organization")) {
      await this.refreshOrganizationCatalog();
      await this.refreshTenantCatalog();
    }
    if (operation.id.startsWith("itam-tenant")) await this.refreshTenantCatalog();
    if (operation.id.startsWith("itam-partner")) await this.refreshPartnerCatalog();
    if (operation.id.startsWith("dcim-")) await this.refreshDcimCatalog();
  }

  async selectModule(moduleId) {
    let module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) return;
    if (!module.loaded) {
      this.state = { ...this.state, activeNavigationModuleId: module.id, openedModules: new Set([module.id]), openedContexts: new Set(), catalogLoading: true, mobileSidebarOpen: false, megaMenuModuleId: null };
      this.render();
      try { module = await this.ensureModuleLoaded(moduleId); } catch (error) { this.state = { ...this.state, error, catalogLoading: false }; this.render(); return; }
    }
    const firstOperationManagement = managementResourceForOperation(module.operations[0]?.id);
    const eligibleManagementIds = new Set(managementResourcesForModule(module.id, module.operations).map((resource) => resource.id));
    if (firstOperationManagement && eligibleManagementIds.has(firstOperationManagement.resource.id)) {
      await this.selectManagementResource(firstOperationManagement.resource.id);
      return;
    }
    const openedModules = new Set(this.state.openedModules);
    const openedContexts = new Set(this.state.openedContexts);
    if (module.id === "overview") { openedModules.clear(); openedContexts.clear(); }
    else {
      openedModules.add(module.id);
      this.removeModuleContexts(openedContexts, module.id);
      const defaultContext = this.contextForOperation(module, module.operations[0].id);
      if (defaultContext) openedContexts.add(this.sidebarContextKey(module.id, defaultContext.label));
    }
    const operation = module.operations[0];
    const catalogLoading = module.id !== "overview" && this.operationCatalogsNeedLoading(operation);
    this.state = { ...this.state, activeModuleId: module.id, activeNavigationModuleId: module.id, selected: operation, openedModules, openedContexts, result: null, error: null, catalogLoading, mobileSidebarOpen: false, megaMenuModuleId: null };
    this.render();
    if (catalogLoading) void this.loadCatalogsForOperation(operation);
  }

  async selectSearchRoute(route) {
    if (!route) {
      return;
    }
    try {
      const response = await fetch(route, { credentials: "same-origin", headers: { Accept: "application/json" } });
      const payload = await response.json();
      this.pendingMainFocus = true;
      this.state = { ...this.state, result: JSON.stringify(payload, null, 2), globalSearchQuery: "", globalSearchBackend: null };
      this.render();
    } catch (error) {
      this.pendingMainFocus = true;
      this.state = { ...this.state, error, globalSearchQuery: "", globalSearchBackend: null };
      this.render();
    }
  }

  async selectSearchOperation(operationId) {
    const indexEntry = this.searchIndex?.find((entry) => entry.id === operationId);
    if (indexEntry) await this.ensureModuleLoaded(indexEntry.moduleId);
    this.selectOperation(operationId, true);
  }

  selectOperation(operationId, focusMain = false) {
    if (String(operationId).startsWith("management:")) {
      void this.selectManagementResource(String(operationId).slice("management:".length), { focusMain });
      return;
    }
    const managementMapping = managementResourceForOperation(operationId);
    if (managementMapping) {
      const module = OPENINFRA_MODULES.find((candidate) => candidate.id === managementMapping.resource.moduleId);
      const eligible = module && managementResourcesForModule(module.id, module.operations).some((resource) => resource.id === managementMapping.resource.id);
      if (eligible) {
        void this.selectManagementResource(managementMapping.resource.id, {
          mode: managementMapping.role === "create" ? "create" : "list",
          focusMain
        });
        return;
      }
    }
    for (const module of OPENINFRA_MODULES) {
      const operation = module.operations.find((item) => item.id === operationId);
      if (operation) {
        const openedModules = new Set(this.state.openedModules);
        const openedContexts = new Set(this.state.openedContexts);
        if (module.id === "overview") {
          openedModules.clear();
          openedContexts.clear();
        } else {
          openedModules.add(module.id);
          this.removeModuleContexts(openedContexts, module.id);
          const context = this.contextForOperation(module, operation.id);
          if (context) {
            openedContexts.add(this.sidebarContextKey(module.id, context.label));
          }
        }
        const catalogLoading = module.id !== "overview" && this.operationCatalogsNeedLoading(operation);
        this.state = { ...this.state, activeModuleId: module.id, activeNavigationModuleId: module.id, selected: operation, openedModules, openedContexts, result: null, error: null, catalogLoading, globalSearchQuery: focusMain ? "" : this.state.globalSearchQuery, globalSearchBackend: focusMain ? null : this.state.globalSearchBackend, mobileSidebarOpen: false, megaMenuModuleId: null };
        this.pendingMainFocus = focusMain;
        this.render();
        if (catalogLoading) {
          void this.loadCatalogsForOperation(operation);
        }
        return;
      }
    }
  }

  filePayload(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("Impossible de lire la preuve sélectionnée."));
      reader.onload = () => {
        const result = String(reader.result || "");
        const separator = result.indexOf(",");
        if (separator < 0) {
          reject(new Error("Le fichier sélectionné est invalide."));
          return;
        }
        resolve({
          filename: file.name,
          media_type: file.type,
          content_base64: result.slice(separator + 1)
        });
      };
      reader.readAsDataURL(file);
    });
  }

  async executeSelected() {
    try {
      const payload = {};
      for (const input of document.querySelectorAll("[data-field]")) {
        if (input.disabled) {
          continue;
        }
        if (input.type === "file") {
          const file = input.files?.[0];
          payload[input.dataset.field] = file ? await this.filePayload(file) : undefined;
        } else {
          payload[input.dataset.field] = input.value;
        }
      }
      const data = await this.client().request(this.state.selected, payload);
      if (this.state.selected.method !== "GET") {
        this.queryCache.invalidate("catalog:");
        this.queryCache.invalidate("global-search:");
      }
      if (this.state.selected.id.startsWith("itam-organization")) {
        await this.refreshOrganizationCatalog();
        await this.refreshTenantCatalog();
      }
      if (this.state.selected.id.startsWith("itam-tenant")) {
        await this.refreshTenantCatalog();
      }
      if (this.state.selected.id.startsWith("itam-partner")) {
        await this.refreshPartnerCatalog();
      }
      if (this.state.selected.id.startsWith("dcim-")) {
        await this.refreshDcimCatalog();
      }
      this.state = { ...this.state, result: data, error: null };
    } catch (error) {
      this.state = { ...this.state, error, result: null };
    }
    this.render();
  }

  moduleForOperation(operation) {
    return OPENINFRA_MODULES.find((module) => module.operations.some((item) => item.id === operation.id)) || OPENINFRA_MODULES.find((module) => module.id === this.state.activeModuleId) || OPENINFRA_MODULES[0];
  }

  announce(message) {
    const region = document.getElementById("openinfra-live-region");
    if (!region) {
      return;
    }
    region.textContent = "";
    window.requestAnimationFrame(() => {
      region.textContent = String(message || "");
    });
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

  slugify(value) {
    return String(value ?? "context")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "context";
  }
}

const openInfraRoot = document.getElementById("openinfra-root");
try {
  const dashboard = new OpenInfraDashboard(openInfraRoot);
  dashboard.start().catch((error) => renderFatalStartupError(openInfraRoot, error));
} catch (error) {
  renderFatalStartupError(openInfraRoot, error);
}
