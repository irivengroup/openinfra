import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import test from 'node:test';
import { resolve } from 'node:path';

const projectRoot = resolve(import.meta.dirname, '..', '..');
const runtimeRoot = resolve(projectRoot, 'src/openinfra/interfaces/rendering/static');

const [runtime, react, runtimeIndex, packageMetadata] = await Promise.all([
  readFile(resolve(runtimeRoot, 'assets/openinfra-web.js'), 'utf8'),
  readFile(resolve(projectRoot, 'web/src/main.jsx'), 'utf8'),
  readFile(resolve(runtimeRoot, 'index.html'), 'utf8'),
  readFile(resolve(projectRoot, 'web/package.json'), 'utf8').then(JSON.parse),
]);

test('dashboard startup uses one local bootstrap request and a non-blocking readiness probe', () => {
  const refreshRuntime = runtime
    .split('async refreshRuntime()', 2)[1]
    .split('async refreshReadiness()', 1)[0];

  assert.match(refreshRuntime, /fetch\("\/bootstrap\.json"/);
  assert.doesNotMatch(refreshRuntime, /fetch\("\/(config\.json|version|status|ready)"/);
  assert.doesNotMatch(refreshRuntime, /refresh(Country|Organization|Tenant|Partner|Dcim)Catalog/);
  assert.match(runtime, /void this\.refreshReadiness\(\);/);
  assert.match(react, /fetch\('\/bootstrap\.json'/);
  assert.match(react, /fetch\('\/ready'/);
});

test('business catalogs are loaded lazily only for the selected operation', () => {
  assert.match(runtime, /operationCatalogDependencies\(operation\)/);
  assert.match(runtime, /operationCatalogsNeedLoading\(operation\)/);
  assert.match(runtime, /loadCatalogsForOperation\(operation\)/);
  assert.match(runtime, /catalogPromise\("scope", \(\) => this\.refreshScopeCatalogs\(\)\)/);
  assert.match(runtime, /Promise\.allSettled/);
});

test('packaged assets are versioned and remain within compressed transfer budgets', async () => {
  const version = packageMetadata.version;
  for (const asset of ['bootstrap.min.css', 'openinfra-web.css', 'openinfra-web.js']) {
    assert.match(runtimeIndex, new RegExp(`/assets/${asset.replace('.', '\\.') }\\?v=${version.replaceAll('.', '\\.')}`));
  }
  assert.match(runtime, new RegExp(`openinfra-i18n\\.js\\?v=${version.replaceAll('.', '\\.')}`));
  assert.match(runtime, new RegExp(`openinfra-form-fields\\.js\\?v=${version.replaceAll('.', '\\.')}`));

  const assetNames = [
    'assets/bootstrap.min.css',
    'assets/openinfra-web.css',
    'assets/openinfra-web.js',
    'assets/openinfra-i18n.js',
    'assets/openinfra-form-fields.js',
  ];
  const payloads = await Promise.all(assetNames.map((name) => readFile(resolve(runtimeRoot, name))));
  const compressed = payloads.map((payload) => gzipSync(payload, { level: 6, mtime: 0 }));
  const totalRawBytes = payloads.reduce((total, payload) => total + payload.length, 0);
  const totalGzipBytes = compressed.reduce((total, payload) => total + payload.length, 0);
  const runtimeJsIndex = assetNames.indexOf('assets/openinfra-web.js');

  assert.ok(totalRawBytes > 500_000);
  assert.ok(totalGzipBytes <= 125_000, `compressed assets exceed budget: ${totalGzipBytes}`);
  assert.ok(compressed[runtimeJsIndex].length <= 55_000);
  assert.ok(totalGzipBytes / totalRawBytes < 0.22);
});
