const RESOURCE_DEFINITIONS = [
  {
    id: 'dcim-sites', moduleId: 'dcim', contextLabel: 'Sites & dépendances',
    labels: { fr: 'Gestion des sites', en: 'Site management' }, singular: { fr: 'site', en: 'site' }, plural: { fr: 'sites', en: 'sites' },
    operations: { list: 'dcim-sites', detail: 'dcim-site', create: 'dcim-site-create', update: 'dcim-site-update', delete: 'dcim-site-delete' },
    sourceOperationId: 'dcim-topology-catalog', collection: 'sites', identity: ['code'], display: ['name', 'code'], immutable: ['code'],
    columns: [['code', 'Code'], ['name', 'Nom'], ['country', 'Pays'], ['city', 'Ville'], ['status', 'Statut']],
    filters: [['country', 'Pays'], ['city', 'Ville'], ['status', 'Statut']],
  },
  {
    id: 'dcim-buildings', moduleId: 'dcim', contextLabel: 'Sites & dépendances',
    labels: { fr: 'Gestion des bâtiments', en: 'Building management' }, singular: { fr: 'bâtiment', en: 'building' }, plural: { fr: 'bâtiments', en: 'buildings' },
    operations: { list: 'dcim-buildings', detail: 'dcim-building', create: 'dcim-building-create', update: 'dcim-building-update', delete: 'dcim-building-delete' },
    sourceOperationId: 'dcim-topology-catalog', collection: 'buildings', identity: ['site', 'code'], display: ['name', 'code'], immutable: ['site', 'code'],
    columns: [['site', 'Site'], ['code', 'Code'], ['name', 'Nom'], ['building_type', 'Type'], ['status', 'Statut']],
    filters: [['site', 'Site'], ['building_type', 'Type'], ['status', 'Statut']],
  },
  {
    id: 'dcim-rooms', moduleId: 'dcim', contextLabel: 'Sites & dépendances',
    labels: { fr: 'Gestion des salles', en: 'Room management' }, singular: { fr: 'salle', en: 'room' }, plural: { fr: 'salles', en: 'rooms' },
    operations: { list: 'dcim-rooms-list', detail: 'dcim-room', create: 'dcim-room-create', update: 'dcim-room-update', delete: 'dcim-room-delete' },
    sourceOperationId: 'dcim-topology-catalog', collection: 'rooms', identity: ['site', 'building', 'code'], display: ['name', 'code'], immutable: ['site', 'building', 'code'],
    columns: [['site', 'Site'], ['building', 'Bâtiment'], ['code', 'Code'], ['name', 'Nom'], ['floor', 'Étage'], ['status', 'Statut']],
    filters: [['site', 'Site'], ['building', 'Bâtiment'], ['floor', 'Étage'], ['status', 'Statut']],
  },
  {
    id: 'dcim-racks', moduleId: 'dcim', contextLabel: 'Sites & dépendances',
    labels: { fr: 'Gestion des châssis/racks', en: 'Chassis/rack management' }, singular: { fr: 'châssis/rack', en: 'chassis/rack' }, plural: { fr: 'châssis/racks', en: 'chassis/racks' },
    operations: { list: 'dcim-racks', detail: 'dcim-rack', create: 'dcim-rack-create', update: 'dcim-rack-update', delete: 'dcim-rack-delete' },
    sourceOperationId: 'dcim-topology-catalog', collection: 'racks', identity: ['site', 'building', 'room', 'rack'], display: ['rack', 'code'], immutable: ['site', 'building', 'room', 'rack'],
    columns: [['site', 'Site'], ['building', 'Bâtiment'], ['room', 'Salle'], ['rack', 'Rack'], ['units', 'U'], ['status', 'Statut']],
    filters: [['site', 'Site'], ['building', 'Bâtiment'], ['room', 'Salle'], ['status', 'Statut']],
  },
  {
    id: 'dcim-zones', moduleId: 'dcim', contextLabel: 'Sites & dépendances',
    labels: { fr: 'Gestion des zones', en: 'Zone management' }, singular: { fr: 'zone', en: 'zone' }, plural: { fr: 'zones', en: 'zones' },
    operations: { list: 'dcim-zones', detail: 'dcim-zone', create: 'dcim-zone-create', update: 'dcim-zone-update', delete: 'dcim-zone-delete' },
    sourceOperationId: 'dcim-topology-catalog', collection: 'zones', identity: ['site', 'building', 'room', 'code'], display: ['name', 'code'], immutable: ['site', 'building', 'room', 'code'],
    columns: [['site', 'Site'], ['building', 'Bâtiment'], ['room', 'Salle'], ['code', 'Code'], ['name', 'Nom'], ['status', 'Statut']],
    filters: [['site', 'Site'], ['building', 'Bâtiment'], ['room', 'Salle'], ['status', 'Statut']],
  },
  {
    id: 'itam-organizations', moduleId: 'itam', contextLabel: 'Organisations',
    labels: { fr: 'Gestion des organisations', en: 'Organization management' }, singular: { fr: 'organisation', en: 'organization' }, plural: { fr: 'organisations', en: 'organizations' },
    operations: { list: 'itam-organizations', detail: 'itam-organization', create: 'itam-organization-create', update: 'itam-organization-update', delete: 'itam-organization-delete' },
    collection: 'items', identity: ['organization_id'], display: ['display_name', 'legal_name', 'organization_id'], immutable: ['organization_id'],
    columns: [['organization_id', 'Code'], ['display_name', 'Nom'], ['country_code', 'Pays'], ['city', 'Ville'], ['status', 'Statut']],
    filters: [['country_code', 'Pays'], ['city', 'Ville'], ['status', 'Statut']],
  },
  {
    id: 'itam-tenants', moduleId: 'itam', contextLabel: 'Organisations',
    labels: { fr: 'Gestion des filiales/subdivisions', en: 'Subsidiary/division management' }, singular: { fr: 'filiale/subdivision', en: 'subsidiary/division' }, plural: { fr: 'filiales/subdivisions', en: 'subsidiaries/divisions' },
    operations: { list: 'itam-tenants', detail: 'itam-tenant', create: 'itam-tenant-create', update: 'itam-tenant-update', delete: 'itam-tenant-delete' },
    collection: 'items', identity: ['organization_id', 'tenant_id'], display: ['name', 'tenant_id'], immutable: ['organization_id', 'tenant_id'],
    columns: [['organization_id', 'Organisation'], ['tenant_id', 'Code'], ['name', 'Nom'], ['is_default', 'Défaut'], ['status', 'Statut']],
    filters: [['organization_id', 'Organisation'], ['is_default', 'Défaut'], ['status', 'Statut']],
  },
  {
    id: 'itam-partners', moduleId: 'itam', contextLabel: 'Partenaires',
    labels: { fr: 'Gestion des partenaires', en: 'Partner management' }, singular: { fr: 'partenaire', en: 'partner' }, plural: { fr: 'partenaires', en: 'partners' },
    operations: { list: 'itam-partners', detail: 'itam-partner', create: 'itam-partner-create', update: 'itam-partner-update', delete: 'itam-partner-delete' },
    collection: 'items', identity: ['organization_id', 'partner_id'], display: ['display_name', 'legal_name', 'partner_id'], immutable: ['organization_id', 'partner_id'],
    columns: [['organization_id', 'Organisation'], ['partner_id', 'Code'], ['display_name', 'Nom'], ['kind', 'Type'], ['country_code', 'Pays'], ['status', 'Statut']],
    filters: [['organization_id', 'Organisation'], ['kind', 'Type'], ['country_code', 'Pays'], ['status', 'Statut']],
  },
];

export const MANAGEMENT_RESOURCES = Object.freeze(RESOURCE_DEFINITIONS.map((resource) => Object.freeze({
  ...resource,
  operations: Object.freeze({ ...resource.operations }),
  identity: Object.freeze([...resource.identity]),
  immutable: Object.freeze([...resource.immutable]),
  columns: Object.freeze(resource.columns.map(([key, label]) => Object.freeze({ key, label }))),
  filters: Object.freeze(resource.filters.map(([key, label]) => Object.freeze({ key, label }))),
})));

const BY_ID = new Map(MANAGEMENT_RESOURCES.map((resource) => [resource.id, resource]));
const BY_OPERATION = new Map();
for (const resource of MANAGEMENT_RESOURCES) {
  for (const [role, operationId] of Object.entries(resource.operations)) {
    if (operationId) BY_OPERATION.set(operationId, { resource, role });
  }
}

export function managementResourceById(resourceId) {
  return BY_ID.get(resourceId) || null;
}

export function managementResourceForOperation(operationId) {
  return BY_OPERATION.get(operationId) || null;
}

export function localizedManagementLabel(resource, language = 'fr', kind = 'labels') {
  const values = resource?.[kind] || {};
  return values[language] || values.fr || values.en || resource?.id || '';
}

export function managementNavigationOperation(resource, language = 'fr') {
  return {
    id: `management:${resource.id}`,
    label: localizedManagementLabel(resource, language),
    method: 'MANAGE',
    path: `/management/${resource.id}`,
    fields: [],
    query: [],
    body: [],
    moduleId: resource.moduleId,
    managementResourceId: resource.id,
  };
}

export function managementResourcesForModule(moduleId, operations = []) {
  const operationIds = new Set(operations.map((operation) => operation.id));
  return MANAGEMENT_RESOURCES.filter((resource) => {
    if (resource.moduleId !== moduleId) return false;
    return ['list', 'create', 'update', 'delete'].every((role) => operationIds.has(resource.operations[role]));
  });
}

export function collapseManagementOperations(moduleId, operations, operationIds, language = 'fr') {
  const available = new Map(operations.map((operation) => [operation.id, operation]));
  const eligibleResources = new Map(managementResourcesForModule(moduleId, operations).map((resource) => [resource.id, resource]));
  const emitted = new Set();
  const result = [];
  for (const operationId of operationIds) {
    const mapped = managementResourceForOperation(operationId);
    if (mapped && mapped.resource.moduleId === moduleId && eligibleResources.has(mapped.resource.id)) {
      if (!emitted.has(mapped.resource.id)) {
        result.push(managementNavigationOperation(mapped.resource, language));
        emitted.add(mapped.resource.id);
      }
      continue;
    }
    const operation = available.get(operationId);
    if (operation) result.push(operation);
  }
  return result;
}

export function managementIdentityPayload(resource, item) {
  return Object.fromEntries(resource.identity.map((key) => [key, item?.[key]]).filter(([, value]) => value !== undefined && value !== null && String(value) !== ''));
}

export function managementDisplayName(resource, item) {
  for (const key of resource.display || []) {
    const value = item?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') return String(value);
  }
  return localizedManagementLabel(resource, 'fr', 'singular');
}

export function flattenManagementCollection(resource, payload) {
  if (!payload || typeof payload !== 'object') return [];
  if (resource.collection === 'items') return Array.isArray(payload.items) ? payload.items.map((item) => ({ ...item })) : [];
  const sites = Array.isArray(payload.sites) ? payload.sites : [];
  if (resource.collection === 'sites') return sites.map(({ buildings: _buildings, ...site }) => ({ ...site }));
  const buildings = [];
  const rooms = [];
  const racks = [];
  const zones = [];
  for (const site of sites) {
    for (const building of Array.isArray(site.buildings) ? site.buildings : []) {
      const buildingBase = { ...building, site: building.site || site.code };
      delete buildingBase.floors;
      delete buildingBase.rooms;
      buildings.push(buildingBase);
      for (const room of Array.isArray(building.rooms) ? building.rooms : []) {
        const roomBase = { ...room, site: room.site || site.code, building: room.building || building.code };
        delete roomBase.zones;
        delete roomBase.racks;
        rooms.push(roomBase);
        for (const rack of Array.isArray(room.racks) ? room.racks : []) {
          racks.push({ ...rack, site: site.code, building: building.code, room: room.code, rack: rack.rack || rack.code });
        }
        for (const zone of Array.isArray(room.zones) ? room.zones : []) {
          zones.push({ ...zone, site: zone.site || site.code, building: zone.building || building.code, room: zone.room || room.code });
        }
      }
    }
  }
  if (resource.collection === 'buildings') return buildings;
  if (resource.collection === 'rooms') return rooms;
  if (resource.collection === 'racks') return racks;
  if (resource.collection === 'zones') return zones;
  return [];
}

export function managementFieldValue(item, fieldName) {
  const value = item?.[fieldName];
  if (Array.isArray(value)) return value.join(',');
  if (value === undefined || value === null) return '';
  return String(value);
}
