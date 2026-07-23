import assert from 'node:assert/strict';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const runtime = await readRuntimePortalSource();

test('non-authoritative RSOT findings expose observed, expected and governing sources in both portals', () => {
  for (const source of [react, runtime]) {
    assert.match(source, /actual_source/u);
    assert.match(source, /expected_source/u);
    assert.match(source, /governance_rule/u);
    assert.match(source, /Source observée/u);
    assert.match(source, /Source attendue/u);
  }

  assert.match(react, /issue\.message[\s\S]*issue\.actual_source[\s\S]*issue\.expected_source[\s\S]*issue\.governance_rule/u);
  assert.match(runtime, /issue\.message[\s\S]*authorityDetails/u);
});
