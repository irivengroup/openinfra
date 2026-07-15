import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MANAGEMENT_CONTEXT_LEVELS,
  isManagementContextAncestor,
  managementContextRank,
  managementFilterOptions,
  managementFilterGroups,
  managementItemMatchesFilter,
  normalizeManagementFilters,
  orderManagementContextEntries,
  updateManagementFilters,
} from '../src/management/context-hierarchy.js';
import { MANAGEMENT_RESOURCES } from '../src/management/resources.js';

test('parent context hierarchy is canonical and stable', () => {
  assert.deepEqual(MANAGEMENT_CONTEXT_LEVELS.map((level) => level.id), [
    'organization', 'subdivision', 'site', 'building', 'floor', 'room', 'grid', 'rack',
  ]);
  assert.equal(managementContextRank('organization_id'), 0);
  assert.equal(managementContextRank('tenant_id'), 1);
  assert.equal(managementContextRank('site'), 2);
  assert.equal(managementContextRank('building_code'), 3);
  assert.equal(managementContextRank('floor'), 4);
  assert.equal(managementContextRank('room'), 5);
  assert.equal(managementContextRank('row'), 6);
  assert.equal(managementContextRank('column'), 6);
  assert.equal(managementContextRank('rack'), 7);
});



test('only strict ancestors constrain a contextual selector', () => {
  assert.equal(isManagementContextAncestor('site', 'site'), false);
  assert.equal(isManagementContextAncestor('site', 'building'), true);
  assert.equal(isManagementContextAncestor('building', 'floor'), true);
  assert.equal(isManagementContextAncestor('row', 'column'), false);
  assert.equal(isManagementContextAncestor('column', 'row'), false);
  assert.equal(isManagementContextAncestor('row', 'rack'), true);
  assert.equal(isManagementContextAncestor('site', 'zone'), true);
  assert.equal(isManagementContextAncestor('status', 'rack'), false);
});

test('management fields keep parent context first and preserve stable order otherwise', () => {
  const fields = [
    { name: 'status' }, { name: 'room' }, { name: 'actor' }, { name: 'site' },
    { name: 'column' }, { name: 'building' }, { name: 'row' }, { name: 'floor' },
    { name: 'tenant_id' }, { name: 'organization_id' }, { name: 'rack' },
  ];
  assert.deepEqual(orderManagementContextEntries(fields).map((field) => field.name), [
    'organization_id', 'tenant_id', 'site', 'building', 'floor', 'room',
    'column', 'row', 'rack', 'status', 'actor',
  ]);
});

test('DCIM management resources expose the parent chain before business filters', () => {
  const byId = Object.fromEntries(MANAGEMENT_RESOURCES.map((resource) => [resource.id, resource]));
  assert.deepEqual(byId['dcim-sites'].filters.map((filter) => filter.key), ['organization_id', 'tenant_id', 'country', 'city', 'status']);
  assert.deepEqual(byId['dcim-buildings'].filters.map((filter) => filter.key), ['organization_id', 'tenant_id', 'site', 'building_type', 'status']);
  assert.deepEqual(byId['dcim-rooms'].filters.map((filter) => filter.key), ['organization_id', 'tenant_id', 'site', 'building', 'floor', 'status']);
  assert.deepEqual(byId['dcim-racks'].filters.map((filter) => filter.key), ['organization_id', 'tenant_id', 'site', 'building', 'floor', 'room', 'row', 'column', 'status']);
  assert.deepEqual(byId['dcim-zones'].filters.map((filter) => filter.key), ['organization_id', 'tenant_id', 'site', 'building', 'floor', 'room', 'rows', 'columns', 'status']);
  assert.deepEqual(byId['itam-tenants'].filters.map((filter) => filter.key).slice(0, 1), ['organization_id']);
  assert.deepEqual(byId['itam-partners'].filters.map((filter) => filter.key).slice(0, 1), ['organization_id']);
});


test('management filters are split into contextual and business criteria without hiding either group', () => {
  const groups = managementFilterGroups([
    { key: 'organization_id' }, { key: 'tenant_id' }, { key: 'site' },
    { key: 'country' }, { key: 'status' },
  ]);
  assert.deepEqual(groups.context.map((filter) => filter.key), ['organization_id', 'tenant_id', 'site']);
  assert.deepEqual(groups.business.map((filter) => filter.key), ['country', 'status']);
});

test('filter options cascade from parents and array coordinates remain individually selectable', () => {
  const definitions = [
    { key: 'tenant_id' }, { key: 'site' }, { key: 'building' }, { key: 'floor' },
    { key: 'room' }, { key: 'rows' }, { key: 'columns' }, { key: 'status' },
  ];
  const items = [
    { tenant_id: 'FIL-A', site: 'PAR', building: 'A', floor: 'ETG1', room: 'R1', rows: ['0', '1'], columns: ['A', 'B'], status: 'active' },
    { tenant_id: 'FIL-A', site: 'PAR', building: 'B', floor: 'ETG2', room: 'R2', rows: ['2'], columns: ['C'], status: 'active' },
    { tenant_id: 'FIL-B', site: 'LYO', building: 'C', floor: 'ETG1', room: 'R3', rows: ['0'], columns: ['A'], status: 'retired' },
  ];
  const filters = { tenant_id: 'FIL-A', site: 'PAR', building: 'A' };
  const options = managementFilterOptions(items, filters, definitions, 'fr');
  assert.deepEqual(options.site, ['PAR']);
  assert.deepEqual(options.building, ['A', 'B']);
  assert.deepEqual(options.floor, ['ETG1']);
  assert.deepEqual(options.room, ['R1']);
  assert.deepEqual(options.rows, ['0', '1']);
  assert.deepEqual(options.columns, ['A', 'B']);
  assert.equal(managementItemMatchesFilter(items[0], 'rows', '1'), true);
});

test('changing a parent clears descendants but preserves independent business filters', () => {
  const definitions = [
    { key: 'tenant_id' }, { key: 'site' }, { key: 'building' }, { key: 'floor' },
    { key: 'room' }, { key: 'row' }, { key: 'column' }, { key: 'status' },
  ];
  const current = {
    tenant_id: 'FIL-A', site: 'PAR', building: 'A', floor: 'ETG1', room: 'R1',
    row: '0', column: 'A', status: 'active',
  };
  assert.deepEqual(updateManagementFilters(current, definitions, 'site', 'LYO'), {
    tenant_id: 'FIL-A', site: 'LYO', status: 'active',
  });
});

test('stale child selections are removed when the underlying item set changes', () => {
  const definitions = [{ key: 'tenant_id' }, { key: 'site' }, { key: 'building' }, { key: 'status' }];
  const normalized = normalizeManagementFilters(
    { tenant_id: 'FIL-A', site: 'PAR', building: 'MISSING', status: 'active' },
    definitions,
    [{ tenant_id: 'FIL-A', site: 'PAR', building: 'A', status: 'active' }],
  );
  assert.deepEqual(normalized, { tenant_id: 'FIL-A', site: 'PAR', status: 'active' });
});
