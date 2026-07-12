import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import test from 'node:test';
import { resolve } from 'node:path';

const projectRoot = resolve(import.meta.dirname, '..', '..');
const runtimeRoot = resolve(projectRoot, 'src/openinfra/interfaces/rendering/static');
const assetRoot = resolve(runtimeRoot, 'assets');

const [runtime, react, reactBootstrap, runtimeIndex, packageMetadata, manifest] = await Promise.all([
  readFile(resolve(assetRoot, 'openinfra-web.js'), 'utf8'),
  readFile(resolve(projectRoot, 'web/src/main.jsx'), 'utf8'),
  readFile(resolve(projectRoot, 'web/src/bootstrap.js'), 'utf8'),
  readFile(resolve(runtimeRoot, 'index.html'), 'utf8'),
  readFile(resolve(projectRoot, 'web/package.json'), 'utf8').then(JSON.parse),
  readFile(resolve(assetRoot, 'openinfra-domain-manifest.js'), 'utf8'),
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

test('business catalogs and domain chunks are loaded only for the selected operation', () => {
  assert.match(runtime, /operationCatalogDependencies\(operation\)/);
  assert.match(runtime, /operationCatalogsNeedLoading\(operation\)/);
  assert.match(runtime, /loadCatalogsForOperation\(operation\)/);
  assert.match(runtime, /catalogPromise\("scope", \(\) => this\.refreshScopeCatalogs\(\)\)/);
  assert.match(runtime, /Promise\.allSettled/);
  assert.match(runtime, /ensureModuleLoaded\(moduleId\)/);
  assert.match(manifest, /import\("\.\/domains\/rsot\.js\?v=0\.31\.2"\)/);
  assert.match(manifest, /import\("\.\/domains\/security\.js\?v=0\.31\.2"\)/);
  assert.doesNotMatch(runtimeIndex, /\/assets\/domains\//);
  assert.match(reactBootstrap, /import\('\.\/main\.jsx'\)/);
});

test('packaged initial shell is versioned and remains within EPIC-2004 budgets', async () => {
  const version = packageMetadata.version;
  for (const asset of ['bootstrap.min.css', 'openinfra-web.css', 'openinfra-web.js']) {
    assert.match(runtimeIndex, new RegExp(`/assets/${asset.replace('.', '\\.') }\\?v=${version.replaceAll('.', '\\.')}`));
  }
  for (const dependency of [
    'openinfra-i18n.js',
    'openinfra-form-fields.js',
    'openinfra-domain-manifest.js',
    'openinfra-query-cache.js',
    'openinfra-virtual-list.js',
    'openinfra-web-vitals.js',
  ]) {
    assert.match(runtime, new RegExp(`${dependency.replaceAll('.', '\\.')}\\?v=${version.replaceAll('.', '\\.')}`));
  }

  const initialAssets = [
    'bootstrap.min.css',
    'openinfra-web.css',
    'openinfra-web.js',
    'openinfra-i18n.js',
    'openinfra-form-fields.js',
    'openinfra-domain-manifest.js',
    'openinfra-query-cache.js',
    'openinfra-virtual-list.js',
    'openinfra-web-vitals.js',
  ];
  const payloads = await Promise.all(initialAssets.map((name) => readFile(resolve(assetRoot, name))));
  const initialRawJs = payloads.reduce(
    (total, payload, index) => total + (initialAssets[index].endsWith('.js') ? payload.length : 0),
    0,
  );
  const initialGzip = payloads.reduce(
    (total, payload) => total + gzipSync(payload, { level: 6, mtime: 0 }).length,
    0,
  );

  assert.ok(initialRawJs <= 250 * 1024, `initial JavaScript exceeds 250 KiB: ${initialRawJs}`);
  assert.ok(initialGzip <= 150 * 1024, `initial shell exceeds 150 KiB gzip: ${initialGzip}`);
  assert.ok(initialRawJs > 0);
  assert.ok(initialGzip > 0);
});
