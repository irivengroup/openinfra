import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');

async function sources() {
  const [reactSource, runtimeSource, reactCss, runtimeCss] = await Promise.all([
    readFile(resolve(webRoot, 'src/main.jsx'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-web.js'), 'utf8'),
    readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-web.css'), 'utf8'),
  ]);
  return { reactSource, runtimeSource, reactCss, runtimeCss };
}

test('React and packaged portals share the responsive navigation contract', async () => {
  const { reactSource, runtimeSource, reactCss, runtimeCss } = await sources();

  assert.equal(reactCss, runtimeCss);
  for (const token of [
    'openinfra-component-nav',
    'openinfra-mega-menu',
    'openinfra-compact-menu-button',
    'openinfra-compact-navigation',
    'openinfra-navigation-backdrop',
    'openinfra-toolbar-actions',
  ]) {
    assert.match(reactSource, new RegExp(token));
    assert.match(runtimeSource, new RegExp(token));
    assert.match(runtimeCss, new RegExp(token));
  }

  assert.match(reactSource, /isMegamenuViewport/);
  assert.match(runtimeSource, /isMegamenuViewport/);
  assert.match(reactSource, /closeResponsiveNavigation/);
  assert.match(runtimeSource, /closeResponsiveNavigation/);
});

test('navigation breakpoints preserve sidebar, megamenu and compact modes', async () => {
  const { runtimeCss } = await sources();

  assert.match(runtimeCss, /@media \(max-width: 1199\.98px\)[\s\S]*?\.openinfra-sidebar\s*\{[\s\S]*?display: none !important;/);
  assert.match(runtimeCss, /@media \(min-width: 768px\) and \(max-width: 1199\.98px\)[\s\S]*?\.openinfra-mega-menu\s*\{[\s\S]*?display: block;/);
  assert.match(runtimeCss, /@media \(max-width: 767\.98px\)[\s\S]*?\.openinfra-component-nav\s*\{[\s\S]*?display: none;/);
  assert.match(runtimeCss, /@media \(max-width: 767\.98px\)[\s\S]*?\.openinfra-compact-menu-button\s*\{[\s\S]*?display: inline-flex;/);
  assert.match(runtimeCss, /grid-template-columns: repeat\(10, minmax\([^)]*\)\);/);
});

test('toolbar controls remain aligned and touch targets expand on coarse pointers', async () => {
  const { runtimeCss } = await sources();

  assert.match(runtimeCss, /--openinfra-toolbar-control-height: 2rem;/);
  assert.match(runtimeCss, /\.openinfra-global-toolbar\s*\{[\s\S]*?padding-block: \.375rem !important;/);
  assert.match(runtimeCss, /\.openinfra-global-search-control \.form-control\s*\{[\s\S]*?height: var\(--openinfra-toolbar-control-height\);/);
  assert.match(runtimeCss, /\.openinfra-language-control \.form-select,[\s\S]*?\.openinfra-api-doc-actions \.btn[\s\S]*?height: var\(--openinfra-toolbar-control-height\);/);
  assert.match(runtimeCss, /@media \(pointer: coarse\)[\s\S]*?--openinfra-toolbar-control-height: 2\.75rem;/);
});
