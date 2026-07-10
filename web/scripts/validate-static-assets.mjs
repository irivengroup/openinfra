import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');

const [packageMetadata, projectVersion, source, theme, sourceI18n, runtimeI18n, sourceHtml, runtimeHtml] = await Promise.all([
  readFile(resolve(webRoot, 'package.json'), 'utf8').then(JSON.parse),
  readFile(resolve(projectRoot, 'VERSION'), 'utf8').then((value) => value.trim()),
  readFile(resolve(webRoot, 'src/main.jsx'), 'utf8'),
  readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8'),
  readFile(resolve(webRoot, 'src/i18n.js'), 'utf8'),
  readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js'), 'utf8'),
  readFile(resolve(webRoot, 'index.html'), 'utf8'),
  readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/index.html'), 'utf8'),
]);

assert.equal(packageMetadata.version, projectVersion, 'web and backend versions must match');
assert.equal(packageMetadata.private, true, 'the frontend package must remain private');
assert.match(source, /id: 'discovery-evidence-submit'/);
assert.match(source, /id: 'discovery-reconcile'/);
assert.match(source, /id: 'discovery-reconciliation-resolve'/);
assert.match(source, /Preuve JSON sans secret/);
assert.match(source, /Justification/);
assert.match(theme, /openinfra/);
assert.match(source, /id: 'graph-spof'/);
assert.match(source, /id: 'graph-export'/);
assert.match(source, /\/v1\/graph\/spof/);
assert.match(source, /\/v1\/graph\/export/);
assert.match(source, /DependencyGraphVisualization/);
assert.match(source, /SpofRanking/);
assert.match(source, /URL\.createObjectURL/);
assert.match(theme, /openinfra-graph-canvas/);
assert.match(theme, /openinfra-spof-ranking/);
assert.equal(runtimeI18n, sourceI18n, 'React and packaged runtime must share the same i18n implementation');
assert.match(sourceI18n, /SUPPORTED_LANGUAGES = Object\.freeze\(\['en', 'fr'\]\)/);
assert.match(sourceI18n, /DEFAULT_LANGUAGE = 'en'/);
assert.match(sourceI18n, /navigatorObject\.languages/);
assert.match(sourceI18n, /navigatorObject\.language/);
assert.match(sourceI18n, /openinfra\.language/);
assert.match(source, /id="openinfra-language"/);
assert.match(sourceHtml, /<html lang="en">/);
assert.match(runtimeHtml, /<html lang="en">/);

console.log(`OpenInfra web static contract valid for ${projectVersion}`);
