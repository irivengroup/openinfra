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


const disasterRecoveryOperations = [
  'multisite-dr-plan-configure',
  'multisite-dr-plan-disable',
  'multisite-dr-plans',
  'multisite-dr-plan-get',
  'multisite-dr-drill-execute',
  'multisite-dr-drills',
  'multisite-dr-drill-get',
];

const disasterRecoveryRoutes = [
  '/v1/multisite/disaster-recovery/plans/configure',
  '/v1/multisite/disaster-recovery/plans/disable',
  '/v1/multisite/disaster-recovery/plans',
  '/v1/multisite/disaster-recovery/plans/get',
  '/v1/multisite/disaster-recovery/drills/execute',
  '/v1/multisite/disaster-recovery/drills',
  '/v1/multisite/disaster-recovery/drills/get',
];

const regionalOperations = [
  'multisite-route-configure',
  'multisite-route-disable',
  'multisite-routes',
  'multisite-route-get',
  'multisite-job-route',
];

const regionalRoutes = [
  '/v1/multisite/regional-discovery/routes/configure',
  '/v1/multisite/regional-discovery/routes/disable',
  '/v1/multisite/regional-discovery/routes',
  '/v1/multisite/regional-discovery/routes/get',
  '/v1/multisite/regional-discovery/jobs/route',
];

test('centralized multisite operations keep static and React route parity', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /Pilotage multisite/u);
    for (const operation of operations) assert.match(source, new RegExp(operation, 'u'));
    for (const route of routes) assert.match(source, new RegExp(route.replaceAll('/', '\\/'), 'u'));
  }
});

test('Enterprise regional discovery routes keep static and React parity', () => {
  for (const source of [react, packaged]) {
    for (const operation of regionalOperations) assert.match(source, new RegExp(operation, 'u'));
    for (const route of regionalRoutes) {
      assert.match(source, new RegExp(route.replaceAll('/', '\\/'), 'u'));
    }
    for (const field of ['region_code', 'site_code', 'vrf_code', 'collector_id', 'job_type']) {
      assert.match(source, new RegExp(`name:\\s*['"]${field}['"]`, 'u'));
    }
    assert.match(source, /name:\s*['"]max_attempts['"][^}]*type:\s*['"]number['"]/u);
  }
  assert.match(translations, /Configure regional Discovery route/u);
  assert.match(translations, /Route regional Discovery job/u);
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


test('multisite disaster recovery keeps typed static and React parity', () => {
  const fields = [
    'replication_mode', 'rpo_seconds', 'rto_seconds', 'max_backup_age_seconds',
    'replication_lag_seconds', 'backup_age_seconds', 'measured_rto_seconds',
    'restore_verified', 'recovery_available', 'vip_reachable', 'operator_confirmed',
  ];
  for (const source of [react, packaged]) {
    for (const operation of disasterRecoveryOperations) {
      assert.match(source, new RegExp(operation, 'u'));
    }
    for (const route of disasterRecoveryRoutes) {
      assert.match(source, new RegExp(route.replaceAll('/', '\\/'), 'u'));
    }
    for (const field of fields) {
      assert.match(source, new RegExp(`name:\\s*['"]${field}['"]`, 'u'));
    }
    assert.doesNotMatch(source, /automatic_promotion/u);
  }
  assert.match(translations, /Configure multisite disaster-recovery plan/u);
  assert.match(translations, /Record primary-site-loss disaster-recovery drill/u);
});
