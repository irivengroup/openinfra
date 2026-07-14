import assert from 'node:assert/strict';
import test from 'node:test';

import dcim from '../../src/openinfra/interfaces/rendering/static/assets/domains/dcim.js';
import itam from '../../src/openinfra/interfaces/rendering/static/assets/domains/itam.js';
import {
  MANAGEMENT_RESOURCES,
  collapseManagementOperations,
  flattenManagementCollection,
  managementIdentityPayload,
  managementResourceForOperation,
} from '../src/management-resources.js';
import { loadManagementOperationSchema } from '../src/management-operation-schema.js';

const modules = new Map([['dcim', dcim], ['itam', itam]]);

test('the unified management registry covers the eight complete CRUD families', () => {
  assert.deepEqual(MANAGEMENT_RESOURCES.map((resource) => resource.id), [
    'dcim-sites', 'dcim-buildings', 'dcim-rooms', 'dcim-racks', 'dcim-zones',
    'itam-organizations', 'itam-tenants', 'itam-partners',
  ]);
  for (const resource of MANAGEMENT_RESOURCES) {
    const operationIds = new Set(modules.get(resource.moduleId).operations.map((operation) => operation.id));
    for (const role of ['list', 'create', 'update', 'delete']) {
      assert.ok(operationIds.has(resource.operations[role]), `${resource.id} missing ${role}`);
    }
    assert.ok(resource.identity.length > 0, `${resource.id} must have an immutable identity`);
  }
});

test('CRUD links collapse to one management entry without removing non CRUD operations', () => {
  const resource = MANAGEMENT_RESOURCES.find((candidate) => candidate.id === 'dcim-sites');
  const module = modules.get('dcim');
  const operationIds = [
    resource.operations.list,
    resource.operations.detail,
    resource.operations.create,
    resource.operations.update,
    resource.operations.delete,
    'dcim-topology-catalog',
  ];
  const collapsed = collapseManagementOperations('dcim', module.operations, operationIds, 'fr');
  assert.deepEqual(collapsed.map((operation) => operation.id), ['management:dcim-sites', 'dcim-topology-catalog']);
  assert.equal(collapsed[0].label, 'Gestion des sites');
  assert.equal(managementResourceForOperation('dcim-site-delete').resource.id, 'dcim-sites');
});

test('nested DCIM topology is flattened without mutating the source hierarchy', () => {
  const payload = {
    sites: [{
      code: 'PAR1', name: 'Paris', buildings: [{
        code: 'BAT-A', name: 'A', floors: [{ code: 'ETG1' }], rooms: [{
          code: 'ROOM-1', name: 'Salle 1', zones: [{ code: 'ZONE-A', name: 'Zone A' }],
          racks: [{ code: 'R01', units: 42 }],
        }],
      }],
    }],
  };
  const serialized = JSON.stringify(payload);
  const byId = Object.fromEntries(MANAGEMENT_RESOURCES.map((resource) => [resource.id, resource]));

  assert.deepEqual(flattenManagementCollection(byId['dcim-sites'], payload).map((item) => item.code), ['PAR1']);
  assert.deepEqual(flattenManagementCollection(byId['dcim-buildings'], payload)[0], { code: 'BAT-A', name: 'A', site: 'PAR1' });
  assert.deepEqual(flattenManagementCollection(byId['dcim-rooms'], payload)[0], { code: 'ROOM-1', name: 'Salle 1', site: 'PAR1', building: 'BAT-A' });
  assert.deepEqual(flattenManagementCollection(byId['dcim-racks'], payload)[0], { code: 'R01', units: 42, site: 'PAR1', building: 'BAT-A', room: 'ROOM-1', rack: 'R01' });
  assert.deepEqual(flattenManagementCollection(byId['dcim-zones'], payload)[0], { code: 'ZONE-A', name: 'Zone A', site: 'PAR1', building: 'BAT-A', room: 'ROOM-1' });
  assert.equal(JSON.stringify(payload), serialized);
});

test('management identity is stable and only contains business keys', () => {
  const resource = MANAGEMENT_RESOURCES.find((candidate) => candidate.id === 'itam-partners');
  assert.deepEqual(managementIdentityPayload(resource, { organization_id: 'ORG', partner_id: 'SUP', display_name: 'Supplier' }), {
    organization_id: 'ORG', partner_id: 'SUP',
  });
});

test('React management actions load the canonical packaged request schema', async () => {
  const operation = await loadManagementOperationSchema('dcim', 'dcim-room-update');
  assert.equal(operation.method, 'POST');
  assert.equal(operation.path, '/v1/dcim/room/update');
  assert.deepEqual(operation.body.slice(0, 4).map((field) => field.name), ['actor', 'site', 'building', 'code']);
});
