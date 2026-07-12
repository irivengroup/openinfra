import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import { resolve } from 'node:path';

const webRoot = resolve(import.meta.dirname, '..');
const distRoot = resolve(webRoot, 'dist');
const manifest = JSON.parse(await readFile(resolve(distRoot, '.vite/manifest.json'), 'utf8'));
const entry = Object.values(manifest).find((item) => item.isEntry);
assert.ok(entry, 'Vite manifest must contain one application entry');

const initial = new Set();
function collectInitial(item) {
  if (!item || initial.has(item.file)) return;
  initial.add(item.file);
  for (const imported of item.imports || []) collectInitial(manifest[imported]);
}
collectInitial(entry);

let initialRawJs = 0;
let initialGzip = 0;
for (const file of initial) {
  const payload = await readFile(resolve(distRoot, file));
  if (file.endsWith('.js')) initialRawJs += payload.length;
  initialGzip += gzipSync(payload, { level: 6, mtime: 0 }).length;
}
for (const css of entry.css || []) {
  const payload = await readFile(resolve(distRoot, css));
  initialGzip += gzipSync(payload, { level: 6, mtime: 0 }).length;
}

assert.ok(initialRawJs <= 250 * 1024, `initial JavaScript exceeds 250 KiB: ${initialRawJs}`);
assert.ok(initialGzip <= 150 * 1024, `initial shell exceeds 150 KiB gzip: ${initialGzip}`);

const dynamicSources = Object.entries(manifest).filter(([, item]) => item.isDynamicEntry);
const domainNames = ['rsot', 'ipam', 'dcim', 'itam', 'discovery', 'data', 'integrations', 'security'];
for (const domain of domainNames) {
  const chunk = dynamicSources.find(([source]) => source.endsWith(`/domains/${domain}.js`));
  assert.ok(chunk, `missing dynamic chunk for ${domain}`);
  assert.ok(!initial.has(chunk[1].file), `${domain} chunk must not be part of initial shell`);
  assert.ok((await stat(resolve(distRoot, chunk[1].file))).size > 0, `${domain} chunk is empty`);
}
assert.ok(dynamicSources.some(([source]) => source.endsWith('/search-index.js')), 'global search index must be lazy');
assert.ok(dynamicSources.some(([source]) => source.endsWith('/domains/rsot-taxonomy.js')), 'RSOT taxonomy must be lazy');

console.log(JSON.stringify({ initialRawJs, initialGzip, initialFiles: [...initial], dynamicChunks: dynamicSources.length }, null, 2));
