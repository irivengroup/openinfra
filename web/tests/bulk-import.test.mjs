import assert from 'node:assert/strict';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const packaged = await readRuntimePortalSource();

test('async bulk CSV/XLSX import is available and protected in both portals', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /import-async-bulk-submit/u);
    assert.match(source, /import-async-bulk-status/u);
    assert.match(source, /\/v1\/imports\/async-bulk-datasets/u);
    assert.match(source, /\/v1\/imports\/async-bulk-status/u);
    assert.match(source, /"binaryUpload": true/u);
    assert.match(source, /"authField": "admin_token"/u);
    assert.match(source, /\.csv,\.xlsx/u);
    assert.match(source, /"maxSizeBytes":536870912/u);
    assert.match(source, /CSV — 512 Mio maximum ; XLSX — 50 Mio maximum/u);
    assert.match(source, /Clé d’idempotence/u);
    assert.match(source, /Intervalle checkpoint/u);
  }
});

test('portal clients keep upload bytes raw and move credentials to Authorization', () => {
  assert.match(react, /selected\.binaryUpload/u);
  assert.match(react, /Authorization.*Bearer/u);
  assert.match(react, /X-OpenInfra-Filename/u);
  assert.match(packaged, /operation\.binaryUpload/u);
  assert.match(packaged, /Authorization.*Bearer/u);
  assert.match(packaged, /X-OpenInfra-Filename/u);
});
