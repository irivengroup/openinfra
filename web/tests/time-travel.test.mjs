import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const runtime = await readRuntimePortalSource();

test('RSOT time travel is exposed by both portals with an accessible provenance report', () => {
  for (const source of [react, runtime]) {
    assert.match(source, /rsot-as-of/u);
    assert.match(source, /\/v1\/rsot\/object-as-of/u);
    assert.match(source, /Limite de relations/u);
    assert.match(source, /openinfra-time-travel-report/u);
    assert.match(source, /openinfra-time-travel-provenance/u);
    assert.match(source, /openinfra-time-travel-relations/u);
    assert.match(source, /snapshot_changed_by/u);
    assert.match(source, /relation_count/u);
  }
});

test('React and runtime time-travel reports preserve raw JSON and semantic tables', () => {
  assert.match(react, /function TimeTravelReport/u);
  assert.match(react, /<caption>\{i18n\.t\('provenance'\)\}<\/caption>/u);
  assert.match(react, /<caption>\{i18n\.t\('historicalRelations'\)\}<\/caption>/u);
  assert.match(runtime, /renderTimeTravelReport\(result, app\)/u);
  assert.match(runtime, /completeHistoricalState/u);
  assert.match(runtime, /boundedHistoricalState/u);
});

test('runtime search index keeps the time travel operation discoverable', async () => {
  const searchSource = await readFile(
    new URL('../../src/openinfra/interfaces/rendering/static/assets/openinfra-search-index.js', import.meta.url),
    'utf8',
  );
  assert.match(searchSource, /"id": "rsot-as-of"/u);
  assert.match(searchSource, /"path": "\/v1\/rsot\/object-as-of"/u);
});
