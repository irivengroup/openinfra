import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');

const [packageMetadata, projectVersion, source, theme] = await Promise.all([
  readFile(resolve(webRoot, 'package.json'), 'utf8').then(JSON.parse),
  readFile(resolve(projectRoot, 'VERSION'), 'utf8').then((value) => value.trim()),
  readFile(resolve(webRoot, 'src/main.jsx'), 'utf8'),
  readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8'),
]);

assert.equal(packageMetadata.version, projectVersion, 'web and backend versions must match');
assert.equal(packageMetadata.private, true, 'the frontend package must remain private');
assert.match(source, /id: 'discovery-evidence-submit'/);
assert.match(source, /id: 'discovery-reconcile'/);
assert.match(source, /id: 'discovery-reconciliation-resolve'/);
assert.match(source, /Preuve JSON sans secret/);
assert.match(source, /Justification/);
assert.match(theme, /openinfra/);

console.log(`OpenInfra web static contract valid for ${projectVersion}`);
