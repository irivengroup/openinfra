import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const packaged = await readRuntimePortalSource();

const operations = [
  'greenops-source-create', 'greenops-sources', 'greenops-policy-upsert', 'greenops-policy-get',
  'greenops-factor-create', 'greenops-factors', 'greenops-measurement-ingest', 'greenops-measurements',
  'greenops-report-generate', 'greenops-report-get', 'greenops-reports', 'greenops-report-export',
  'greenops-anomalies', 'greenops-forecasts', 'greenops-candidates', 'greenops-scores',
];

const routes = [
  '/v1/greenops/measurement-sources/create', '/v1/greenops/measurement-sources',
  '/v1/greenops/policies/upsert', '/v1/greenops/policies/get',
  '/v1/greenops/carbon-factors/create', '/v1/greenops/carbon-factors',
  '/v1/greenops/energy-measurements/ingest', '/v1/greenops/energy-measurements',
  '/v1/greenops/reports/generate', '/v1/greenops/reports/get', '/v1/greenops/reports',
  '/v1/greenops/reports/export', '/v1/greenops/anomalies',
  '/v1/greenops/capacity-forecasts', '/v1/greenops/consolidation-candidates',
  '/v1/greenops/green-scores',
];

test('GreenOps is grouped under DCIM with complete route parity', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /GreenOps — sources & politiques/u);
    assert.match(source, /GreenOps — mesures/u);
    assert.match(source, /GreenOps — rapports & empreinte/u);
    assert.match(source, /GreenOps — capacité & recommandations/u);
    assert.doesNotMatch(source, /id:\s*['"]greenops['"]\s*,\s*label:/u);
    for (const operation of operations) assert.match(source, new RegExp(operation, 'u'));
    for (const route of routes) assert.match(source, new RegExp(route.replaceAll('/', '\\/'), 'u'));
  }
});

test('GreenOps temporal fields use calendars and report export is downloadable', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /["']?name["']?\s*:\s*['"]period_start['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]date['"]/u);
    assert.match(source, /["']?name["']?\s*:\s*['"]period_end['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]date['"]/u);
    assert.match(source, /["']?name["']?\s*:\s*['"]period_start['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]datetime-local['"]/u);
    assert.match(source, /["']?name["']?\s*:\s*['"]period_end['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]datetime-local['"]/u);
    assert.match(source, /greenops-report-export/u);
    assert.match(source, /["']?download["']?\s*:\s*true/u);
  }
});

test('GreenOps recommendations remain advisory and require human approval', () => {
  const domain = fs.readFileSync(new URL('../../src/openinfra/domain/greenops.py', import.meta.url), 'utf8');
  const migration = fs.readFileSync(new URL('../../installers/migrations/postgresql/0047_greenops_energy_capacity.sql', import.meta.url), 'utf8');
  assert.match(domain, /requires_human_approval/u);
  assert.match(migration, /requires_human_approval/u);
  assert.match(migration, /payload\s*->>\s*'requires_human_approval'\s*=\s*'true'/iu);
});
