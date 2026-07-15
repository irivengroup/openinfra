const CONTEXT_LEVELS = [
  {
    id: 'organization',
    rank: 0,
    labels: { fr: 'Organisation', en: 'Organization' },
    aliases: ['organization_id', 'organization', 'organization_code'],
  },
  {
    id: 'subdivision',
    rank: 1,
    labels: { fr: 'Filiale/Subdivision', en: 'Subsidiary/Division' },
    aliases: ['tenant_id', 'tenant', 'subsidiary_id', 'subdivision_id', 'owner_tenant_id'],
  },
  {
    id: 'site',
    rank: 2,
    labels: { fr: 'Site', en: 'Site' },
    aliases: ['site', 'site_id', 'site_code'],
  },
  {
    id: 'building',
    rank: 3,
    labels: { fr: 'Bâtiment', en: 'Building' },
    aliases: ['building', 'building_id', 'building_code'],
  },
  {
    id: 'floor',
    rank: 4,
    labels: { fr: 'Étage', en: 'Floor' },
    aliases: ['floor', 'floor_id', 'floor_code', 'level', 'level_code'],
  },
  {
    id: 'room',
    rank: 5,
    labels: { fr: 'Salle', en: 'Room' },
    aliases: ['room', 'room_id', 'room_code'],
  },
  {
    id: 'grid',
    rank: 6,
    labels: { fr: 'Ligne/Colonne', en: 'Row/Column' },
    aliases: ['row', 'rows', 'row_code', 'line', 'line_code', 'column', 'columns', 'column_code'],
  },
  {
    id: 'rack',
    rank: 7,
    labels: { fr: 'Rack', en: 'Rack' },
    aliases: ['rack', 'rack_id', 'rack_code', 'chassis', 'chassis_id', 'chassis_code'],
  },
];

export const MANAGEMENT_CONTEXT_LEVELS = Object.freeze(CONTEXT_LEVELS.map((level) => Object.freeze({
  ...level,
  labels: Object.freeze({ ...level.labels }),
  aliases: Object.freeze([...level.aliases]),
})));

const CONTEXT_BY_ALIAS = new Map();
for (const level of MANAGEMENT_CONTEXT_LEVELS) {
  for (const alias of level.aliases) CONTEXT_BY_ALIAS.set(alias, level);
}

function fieldNameOf(value) {
  if (typeof value === 'string') return value;
  return String(value?.name || value?.key || '').trim();
}

export function managementContextLevel(value) {
  return CONTEXT_BY_ALIAS.get(fieldNameOf(value)) || null;
}

export function managementContextRank(value) {
  return managementContextLevel(value)?.rank ?? Number.POSITIVE_INFINITY;
}

export function isManagementContextAncestor(candidate, target) {
  const candidateRank = managementContextRank(candidate);
  const targetRank = managementContextRank(target);
  return Number.isFinite(candidateRank) && candidateRank < targetRank;
}

export function managementContextLabel(value, language = 'fr') {
  const level = managementContextLevel(value);
  if (!level) return '';
  return level.labels[language] || level.labels.fr || level.labels.en || level.id;
}

export function orderManagementContextEntries(entries = []) {
  return entries
    .map((entry, index) => ({ entry, index, rank: managementContextRank(entry) }))
    .sort((left, right) => left.rank - right.rank || left.index - right.index)
    .map(({ entry }) => entry);
}

export function managementFilterValues(item, fieldName) {
  const value = item?.[fieldName];
  if (Array.isArray(value)) {
    return value
      .map((entry) => String(entry ?? '').trim())
      .filter(Boolean);
  }
  if (value === undefined || value === null) return [];
  const normalized = String(value).trim();
  return normalized ? [normalized] : [];
}

export function managementItemMatchesFilter(item, fieldName, expectedValue) {
  if (!expectedValue) return true;
  return managementFilterValues(item, fieldName).includes(String(expectedValue));
}

function selectedAncestorMatches(item, filters, definitions, currentDefinition) {
  const currentRank = managementContextRank(currentDefinition);
  if (!Number.isFinite(currentRank)) return true;
  for (const definition of definitions) {
    const rank = managementContextRank(definition);
    if (!Number.isFinite(rank) || rank >= currentRank) continue;
    const selected = filters?.[definition.key];
    if (selected && !managementItemMatchesFilter(item, definition.key, selected)) return false;
  }
  return true;
}

export function managementFilterOptions(items, filters, definitions, language = 'fr') {
  const result = {};
  for (const definition of definitions) {
    const values = new Set();
    for (const item of items) {
      if (!selectedAncestorMatches(item, filters, definitions, definition)) continue;
      for (const value of managementFilterValues(item, definition.key)) values.add(value);
    }
    result[definition.key] = [...values].sort((left, right) => left.localeCompare(right, language, { numeric: true, sensitivity: 'base' }));
  }
  return result;
}

export function updateManagementFilters(currentFilters, definitions, changedKey, nextValue) {
  const updated = { ...(currentFilters || {}) };
  if (nextValue) updated[changedKey] = nextValue;
  else delete updated[changedKey];
  const changedRank = managementContextRank(changedKey);
  if (!Number.isFinite(changedRank)) return updated;
  for (const definition of definitions) {
    const rank = managementContextRank(definition);
    if (Number.isFinite(rank) && rank > changedRank) delete updated[definition.key];
  }
  return updated;
}

export function normalizeManagementFilters(filters, definitions, items) {
  const normalized = {};
  let invalidSelectedParentRank = Number.POSITIVE_INFINITY;
  for (const definition of definitions) {
    const rank = managementContextRank(definition);
    const selected = filters?.[definition.key];
    if (!Number.isFinite(rank) || !selected || rank > invalidSelectedParentRank) continue;
    const eligibleItems = items.filter((item) => {
      for (const ancestor of definitions) {
        const ancestorRank = managementContextRank(ancestor);
        if (!Number.isFinite(ancestorRank) || ancestorRank >= rank) continue;
        const ancestorValue = normalized[ancestor.key];
        if (ancestorValue && !managementItemMatchesFilter(item, ancestor.key, ancestorValue)) return false;
      }
      return true;
    });
    if (eligibleItems.some((item) => managementItemMatchesFilter(item, definition.key, selected))) {
      normalized[definition.key] = selected;
    } else {
      invalidSelectedParentRank = rank;
    }
  }
  for (const definition of definitions) {
    if (!Number.isFinite(managementContextRank(definition)) && filters?.[definition.key]) {
      normalized[definition.key] = filters[definition.key];
    }
  }
  return normalized;
}
