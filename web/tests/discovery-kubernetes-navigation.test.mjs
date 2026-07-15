import assert from 'node:assert/strict';
import test from 'node:test';

import reactDiscovery from '../src/domains/discovery.js';
import { SIDEBAR_CONTEXTS } from '../src/domain-manifest.js';
import runtimeDiscovery from '../../src/openinfra/interfaces/rendering/static/assets/domains/discovery.js';
import { OPENINFRA_SIDEBAR_CONTEXTS } from '../../src/openinfra/interfaces/rendering/static/assets/openinfra-domain-manifest.js';

const CONTEXT_LABEL = 'Kubernetes et cloud-native';

function kubernetesOperationIds(moduleDefinition) {
  return moduleDefinition.operations
    .map((operation) => operation.id)
    .filter((operationId) => operationId.startsWith('kubernetes-'))
    .sort();
}

function configuredOperationIds(contexts, moduleDefinition) {
  const group = (contexts.discovery || []).find((candidate) => candidate.label === CONTEXT_LABEL);
  assert.ok(group, `Missing Discovery context: ${CONTEXT_LABEL}`);
  if (Array.isArray(group.operationIds)) return [...group.operationIds].sort();
  assert.equal(group.operationIdPrefix, 'kubernetes-');
  return moduleDefinition.operations
    .map((operation) => operation.id)
    .filter((operationId) => operationId.startsWith(group.operationIdPrefix))
    .sort();
}

test('Discovery exposes Kubernetes and cloud-native as a dedicated context in both frontends', () => {
  const reactIds = kubernetesOperationIds(reactDiscovery);
  const runtimeIds = kubernetesOperationIds(runtimeDiscovery);

  assert.ok(reactIds.length > 0);
  assert.ok(runtimeIds.length > 0);
  assert.deepEqual(configuredOperationIds(SIDEBAR_CONTEXTS, reactDiscovery), reactIds);
  assert.deepEqual(configuredOperationIds(OPENINFRA_SIDEBAR_CONTEXTS, runtimeDiscovery), runtimeIds);
});
