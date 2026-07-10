import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');
const react = await readFile(resolve(webRoot, 'src/main.jsx'), 'utf8');
const runtime = await readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-web.js'), 'utf8');
const theme = await readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8');

for (const source of [react, runtime]) {
  test(`graph SPOF and export contracts are present in ${source === react ? 'React' : 'packaged'} runtime`, () => {
    assert.match(source, /graph-spof/);
    assert.match(source, /graph-export/);
    assert.match(source, /\/v1\/graph\/spof/);
    assert.match(source, /\/v1\/graph\/export/);
    assert.match(source, /openinfra-graph-canvas/);
    assert.match(source, /openinfra-spof-ranking/);
    assert.match(source, /URL\.createObjectURL/);
    assert.match(source, /URL\.revokeObjectURL/);
  });
}

test('graph visualizations retain non-color and raw-data alternatives', () => {
  assert.match(react, /RawGraphResult/);
  assert.match(react, /<caption className="visually-hidden">/);
  assert.match(react, /role="img"/);
  assert.match(react, /tabIndex=\{0\}/);
  assert.match(runtime, /openinfra-raw-result/);
  assert.match(runtime, /<caption class="visually-hidden">/);
  assert.match(runtime, /tabindex="0"/);
  assert.match(theme, /forced-colors: active/);
});
