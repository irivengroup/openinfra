import assert from 'node:assert/strict';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const runtime = await readRuntimePortalSource();

test('RSOT quality certification report is semantic and accessible in both portals', () => {
  for (const source of [react, runtime]) {
    assert.match(source, /rsot-quality-object/u);
    assert.match(source, /rsot-quality-summary/u);
    assert.match(source, /openinfra-rsot-quality-report/u);
    assert.match(source, /openinfra-rsot-quality-dimensions/u);
    assert.match(source, /openinfra-rsot-quality-issues/u);
    assert.match(source, /certification_status/u);
    assert.match(source, /authority_score/u);
    assert.match(source, /completeness_score/u);
  }
});

test('RSOT quality report keeps raw JSON available after the semantic report', () => {
  assert.match(react, /<RsotQualityReport[^>]*\/>[\s\S]*<RawGraphResult/u);
  assert.match(runtime, /renderRsotQualityReport\(result, app\)/u);
  assert.match(runtime, /openinfra-raw-result/u);
});
