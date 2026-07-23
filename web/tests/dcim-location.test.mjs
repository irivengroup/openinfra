import assert from 'node:assert/strict';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const packaged = await readRuntimePortalSource();

test('DCIM locator sheet is searchable and grouped with physical location in both portals', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /dcim-locate-equipment/u);
    assert.match(source, /dcim-locator-sheet/u);
    assert.match(source, /\/v1\/dcim\/locator-sheet/u);
    assert.match(source, /Fiche d’intervention équipement/u);
    assert.match(source, /Localisation & capacité/u);
    assert.match(source, /Numéro d’actif/u);
    assert.match(source, /Format rendu/u);
  }
});
