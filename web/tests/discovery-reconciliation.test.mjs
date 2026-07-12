import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');
const reactSource = await readReactPortalSource();
const staticSource = await readRuntimePortalSource();

const operations = [
  ['discovery-evidence-list', 'GET', '/v1/discovery/evidence-list'],
  ['discovery-evidence', 'GET', '/v1/discovery/evidence'],
  ['discovery-evidence-submit', 'POST', '/v1/discovery/evidence'],
  ['discovery-reconciliation-list', 'GET', '/v1/discovery/reconciliation-list'],
  ['discovery-reconciliation', 'GET', '/v1/discovery/reconciliation'],
  ['discovery-reconcile', 'POST', '/v1/discovery/reconciliation'],
  ['discovery-reconciliation-resolve', 'POST', '/v1/discovery/reconciliation/resolve'],
];

test('React and static portals expose the complete Discovery reconciliation contract', () => {
  for (const [operationId, method, path] of operations) {
    for (const source of [reactSource, staticSource]) {
      assert.ok(source.includes(`"id": "${operationId}"`));
      assert.ok(source.includes(`"path": "${path}"`));
      assert.ok(source.includes(`"method": "${method}"`));
    }
  }
});

test('operator-facing reconciliation inputs preserve governance safeguards', () => {
  for (const source of [reactSource, staticSource]) {
    assert.match(source, /Preuve JSON sans secret/);
    assert.match(source, /Sélections par chemin JSON/);
    assert.match(source, /Justification/);
    assert.doesNotMatch(source, /Écriture RSOT automatique/);
  }
});
