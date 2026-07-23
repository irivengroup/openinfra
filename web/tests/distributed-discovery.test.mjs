import assert from 'node:assert/strict';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const packaged = await readRuntimePortalSource();

test('distributed discovery job submission and immutable result recording are available in both portals', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /discovery-job-submit/u);
    assert.match(source, /discovery-job-result/u);
    assert.match(source, /\/v1\/discovery\/jobs\/result/u);
    assert.match(source, /Soumettre un job distribué|Soumettre un job idempotent/u);
    assert.match(source, /Enregistrer le résultat d’un job/u);
    assert.match(source, /Empreinte certificat/u);
    assert.match(source, /Jeton de fencing/u);
    assert.match(source, /Clé objet/u);
    assert.match(source, /Résultat JSON sans secret/u);
  }
});

test('runtime lazy search index exposes the distributed discovery result operation', async () => {
  const searchSource = await import('node:fs/promises').then(({ readFile }) =>
    readFile(new URL('../..//src/openinfra/interfaces/rendering/static/assets/openinfra-search-index.js', import.meta.url), 'utf8'),
  );
  assert.match(searchSource, /"id": "discovery-job-result"/u);
  assert.match(searchSource, /"path": "\/v1\/discovery\/jobs\/result"/u);
});
