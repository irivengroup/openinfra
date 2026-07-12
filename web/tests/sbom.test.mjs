import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const packaged = await readRuntimePortalSource();

const operations = [
  'sbom-import', 'sbom-documents', 'sbom-document-get',
  'sbom-vulnerability-import', 'sbom-vulnerabilities',
  'sbom-exposure-upsert', 'sbom-exposures', 'sbom-exposure-get',
  'sbom-risk-assess', 'sbom-findings', 'sbom-risk-export',
  'sbom-compare', 'sbom-comparisons', 'sbom-comparison-get',
];

const routes = [
  '/v1/sbom/documents/import', '/v1/sbom/documents', '/v1/sbom/documents/get',
  '/v1/sbom/vulnerabilities/import', '/v1/sbom/vulnerabilities',
  '/v1/sbom/exposures/upsert', '/v1/sbom/exposures', '/v1/sbom/exposures/get',
  '/v1/sbom/risk/assess', '/v1/sbom/findings', '/v1/sbom/risk/export',
  '/v1/sbom/comparisons/create', '/v1/sbom/comparisons', '/v1/sbom/comparisons/get',
];

test('SBOM is grouped under Security with complete route parity', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /SBOM — inventaire & versions/u);
    assert.match(source, /Vulnérabilités & exposition/u);
    assert.match(source, /Risque contextualisé/u);
    assert.doesNotMatch(source, /id:\s*['"]sbom['"]\s*,\s*label:/u);
    for (const operation of operations) assert.match(source, new RegExp(operation, 'u'));
    for (const route of routes) assert.match(source, new RegExp(route.replaceAll('/', '\\/'), 'u'));
  }
});

test('SBOM vulnerability dates use calendars and risk export is downloadable', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /["']?name["']?\s*:\s*['"]published_at['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]datetime-local['"]/u);
    assert.match(source, /["']?name["']?\s*:\s*['"]modified_at['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]datetime-local['"]/u);
    assert.match(source, /sbom-risk-export/u);
    assert.match(source, /["']?download["']?\s*:\s*true/u);
  }
});

test('SBOM remains analytical without active scan or remediation', () => {
  const service = fs.readFileSync(new URL('../../src/openinfra/application/sbom_services.py', import.meta.url), 'utf8');
  const migration = fs.readFileSync(new URL('../../installers/migrations/postgresql/0048_sbom_vulnerabilities_exposure.sql', import.meta.url), 'utf8');
  assert.doesNotMatch(service, /subprocess|socket|nmap|remediat(?:e|ion)/iu);
  assert.doesNotMatch(migration, /remediation_command|execution_command/iu);
});
