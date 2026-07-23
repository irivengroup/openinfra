import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const runtime = await readRuntimePortalSource();

test('application change impact report is exposed by both portals', () => {
  for (const source of [react, runtime]) {
    assert.match(source, /graph-change-impact/u);
    assert.match(source, /\/v1\/graph\/change-impact/u);
    assert.match(source, /Analyser l’impact d’un changement applicatif/u);
    assert.match(source, /Type de service métier/u);
    assert.match(source, /Type de ressource métier/u);
    assert.match(source, /Taille maximale des échantillons/u);
    assert.match(source, /openinfra-change-impact-report/u);
    assert.match(source, /openinfra-change-impact-services/u);
    assert.match(source, /openinfra-change-impact-dependencies/u);
  }
});

test('runtime search index exposes application change impact', async () => {
  const searchSource = await readFile(
    new URL('../../src/openinfra/interfaces/rendering/static/assets/openinfra-search-index.js', import.meta.url),
    'utf8',
  );
  assert.match(searchSource, /"id": "graph-change-impact"/u);
  assert.match(searchSource, /"path": "\/v1\/graph\/change-impact"/u);
});


test('application change impact has a dedicated accessible report in both portals', () => {
  assert.match(react, /function ChangeImpactReport/u);
  assert.match(react, /<caption>\{i18n\.t\('impactedBusinessServices'\)\}<\/caption>/u);
  assert.match(react, /<caption>\{i18n\.t\('criticalDependencies'\)\}<\/caption>/u);
  assert.match(runtime, /renderChangeImpactReport\(result, app\)/u);
  assert.match(runtime, /root_spof_risk/u);
  assert.match(runtime, /affected_business_service_keys/u);
});
