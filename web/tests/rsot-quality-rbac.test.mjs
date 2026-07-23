import assert from 'node:assert/strict';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const runtime = await readRuntimePortalSource();

test('RSOT quality operations are executed against the protected backend in both portals', () => {
  assert.match(react, /normalized\.startsWith\('rsot-quality-'\)/u);
  assert.match(react, /credentials:\s*'same-origin'/u);
  assert.doesNotMatch(react, /rsot-quality-(?:object|summary)[\s\S]{0,500}authField/u);

  assert.match(runtime, /class OpenInfraApiClient/u);
  assert.match(runtime, /credentials:\s*"same-origin"/u);
  assert.doesNotMatch(runtime, /rsot-quality-(?:object|summary)[\s\S]{0,500}"authField"/u);
});

test('authorization failures preserve HTTP status and never display a success notification', () => {
  assert.match(react, /operationError\.status\s*=\s*response\.status/u);
  assert.match(react, /status:\s*Number\.isInteger\(error\?\.status\)/u);
  assert.match(react, /result !== null && !\(typeof result === 'object' && result\?\.error\)/u);

  assert.match(runtime, /class OpenInfraApiError extends Error/u);
  assert.match(runtime, /this\.status\s*=\s*Number\(status\)\s*\|\|\s*0/u);
  assert.match(runtime, /this\.status === 401 \|\| this\.status === 403/u);
  assert.match(runtime, /openinfra-access-denied/u);
  assert.match(runtime, /data-http-status/u);
});
