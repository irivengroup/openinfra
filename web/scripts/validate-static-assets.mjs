import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');
const runtimeAssets = resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets');

async function concatenate(paths) {
  return (await Promise.all(paths.map((path) => readFile(path, 'utf8')))).join('\n');
}

const reactDomainNames = ['data', 'dcim', 'discovery', 'ipam', 'itam', 'rsot', 'security'];
const runtimeDomainNames = [...reactDomainNames, 'integrations'];

const [
  packageMetadata,
  projectVersion,
  sourceShell,
  sourceCatalog,
  runtimeShell,
  runtimeCatalog,
  sourceManifest,
  runtimeManifest,
  runtimeSearchIndex,
  theme,
  sourceI18n,
  runtimeI18n,
  sourceHtml,
  runtimeHtml,
] = await Promise.all([
  readFile(resolve(webRoot, 'package.json'), 'utf8').then(JSON.parse),
  readFile(resolve(projectRoot, 'VERSION'), 'utf8').then((value) => value.trim()),
  readFile(resolve(webRoot, 'src/main.jsx'), 'utf8'),
  concatenate(reactDomainNames.map((name) => resolve(webRoot, 'src/domains', `${name}.js`))),
  readFile(resolve(runtimeAssets, 'openinfra-web.js'), 'utf8'),
  concatenate(runtimeDomainNames.map((name) => resolve(runtimeAssets, 'domains', `${name}.js`))),
  readFile(resolve(webRoot, 'src/domain-manifest.js'), 'utf8'),
  readFile(resolve(runtimeAssets, 'openinfra-domain-manifest.js'), 'utf8'),
  readFile(resolve(runtimeAssets, 'openinfra-search-index.js'), 'utf8'),
  readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8'),
  readFile(resolve(webRoot, 'src/i18n.js'), 'utf8'),
  readFile(resolve(runtimeAssets, 'openinfra-i18n.js'), 'utf8'),
  readFile(resolve(webRoot, 'index.html'), 'utf8'),
  readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/index.html'), 'utf8'),
]);

assert.equal(packageMetadata.version, projectVersion, 'web and backend versions must match');
assert.equal(packageMetadata.private, true, 'the frontend package must remain private');

for (const operationId of [
  'discovery-evidence-submit',
  'discovery-reconcile',
  'discovery-reconciliation-resolve',
  'graph-spof',
  'graph-export',
]) {
  assert.match(sourceCatalog, new RegExp(`"id": "${operationId}"`));
  assert.match(runtimeCatalog, new RegExp(`"id": "${operationId}"`));
}
for (const route of ['/v1/graph/spof', '/v1/graph/export']) {
  assert.match(sourceCatalog, new RegExp(route.replaceAll('/', '\\/')));
  assert.match(runtimeCatalog, new RegExp(route.replaceAll('/', '\\/')));
}
assert.match(sourceCatalog, /Preuve JSON sans secret/);
assert.match(sourceCatalog, /Justification/);
assert.match(runtimeCatalog, /Preuve JSON sans secret/);
assert.match(runtimeCatalog, /Justification/);
assert.match(sourceShell, /DependencyGraphVisualization/);
assert.match(sourceShell, /SpofRanking/);
assert.match(sourceShell, /URL\.createObjectURL/);
assert.match(runtimeShell, /openinfra-graph-canvas/);
assert.match(theme, /openinfra-graph-canvas/);
assert.match(theme, /openinfra-spof-ranking/);

assert.match(sourceManifest, /import\('\.\/domains\/rsot\.js'\)/);
assert.match(sourceManifest, /"operations": \[\]/);
assert.match(runtimeManifest, new RegExp(`domains\\/rsot\\.js\\?v=${projectVersion.replaceAll('.', '\\.')}`));
assert.match(runtimeManifest, /operations": \[\]/);
assert.match(runtimeSearchIndex, /discovery-evidence-submit/);
assert.doesNotMatch(sourceShell, /"id": "discovery-evidence-submit"/);
assert.doesNotMatch(runtimeShell, /"id": "discovery-evidence-submit"/);
assert.doesNotMatch(sourceShell, /localStorage|sessionStorage|indexedDB/);
assert.doesNotMatch(runtimeShell, /localStorage|sessionStorage|indexedDB/);

assert.equal(runtimeI18n, sourceI18n, 'React and packaged runtime must share the same i18n implementation');
assert.match(sourceI18n, /SUPPORTED_LANGUAGES = Object\.freeze\(\['en', 'fr'\]\)/);
assert.match(sourceI18n, /DEFAULT_LANGUAGE = 'en'/);
assert.match(sourceI18n, /navigatorObject\.languages/);
assert.match(sourceI18n, /navigatorObject\.language/);
assert.match(sourceI18n, /openinfra\.language/);
assert.match(sourceShell, /id="openinfra-language"/);
assert.match(sourceHtml, /<html lang="en">/);
assert.match(runtimeHtml, /<html lang="en">/);

console.log(`OpenInfra web static contract valid for ${projectVersion}`);
