import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const react = fs.readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8');
const packaged = fs.readFileSync(
  new URL('../../src/openinfra/interfaces/rendering/static/assets/openinfra-web.js', import.meta.url),
  'utf8',
);
const translations = fs.readFileSync(
  new URL('../../src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js', import.meta.url),
  'utf8',
);
const service = fs.readFileSync(
  new URL('../../src/openinfra/application/multisite_services.py', import.meta.url),
  'utf8',
);

const operations = [
  'multisite-grant-upsert',
  'multisite-grant-revoke',
  'multisite-grants',
  'multisite-sites',
  'multisite-report-generate',
  'multisite-reports',
  'multisite-report-get',
];

const routes = [
  '/v1/multisite/site-access/grants/upsert',
  '/v1/multisite/site-access/grants/revoke',
  '/v1/multisite/site-access/grants',
  '/v1/multisite/sites',
  '/v1/multisite/reports/generate',
  '/v1/multisite/reports',
  '/v1/multisite/reports/get',
];

test('centralized multisite operations keep static and React route parity', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /Pilotage multisite/u);
    for (const operation of operations) assert.match(source, new RegExp(operation, 'u'));
    for (const route of routes) assert.match(source, new RegExp(route.replaceAll('/', '\\/'), 'u'));
  }
});

test('multisite forms use typed access, boolean and site-list controls', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /name:\s*['"]access_level['"][^}]*type:\s*['"]select['"]/u);
    assert.match(source, /name:\s*['"]active_only['"][^}]*type:\s*['"]boolean['"]/u);
    assert.match(source, /name:\s*['"]site_codes['"][^}]*type:\s*['"]json['"]/u);
  }
  assert.match(translations, /Multisite management/u);
  assert.match(translations, /viewer:\s*['"]Viewer['"]/u);
  assert.match(translations, /operator:\s*['"]Operator['"]/u);
  assert.match(translations, /admin:\s*['"]Local administrator['"]/u);
});

test('site-scoped access enumerates every repository page', () => {
  assert.match(service, /while True:/u);
  assert.match(service, /Pagination\.from_values\(500, cursor\)/u);
  assert.match(service, /page\.next_cursor/u);
});
