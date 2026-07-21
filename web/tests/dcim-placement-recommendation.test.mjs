import assert from 'node:assert/strict';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const portals = [await readReactPortalSource(), await readRuntimePortalSource()];

test('DCIM placement recommendation keeps React and packaged runtime parity', () => {
  for (const source of portals) {
    assert.match(source, /dcim-placement-recommendations/u);
    assert.match(source, /\/v1\/dcim\/placement-recommendations/u);
    assert.match(source, /Recommander un placement en rack/u);
    assert.match(source, /required_power_watts/u);
    assert.match(source, /required_cooling_watts/u);
    assert.match(source, /required_power_feeds/u);
    assert.match(source, /preferred_face/u);
    assert.match(source, /Nombre maximal de recommandations/u);
  }
});

test('DCIM placement recommendation remains a read-only capacity operation', () => {
  for (const source of portals) {
    assert.match(
      source,
      /["']?id["']?\s*:\s*["']dcim-placement-recommendations["'][\s\S]{0,260}?["']?method["']?\s*:\s*["']GET["']/u,
    );
  }
});
