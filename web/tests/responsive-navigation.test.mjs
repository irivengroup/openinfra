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
  assert.match(runtimeCss, /@media \(min-width: 768px\) and \(max-width: 1199\.98px\)[\s\S]*?grid-template-columns: repeat\(11, minmax\(0, 1fr\)\);/);
});

test('megamenu opens on hover and keyboard focus while preserving click fallback', async () => {
  const { reactSource, runtimeSource } = await sources();

  assert.match(reactSource, /onMouseEnter=\{\(event\) => openMegaMenu\(module, event\.currentTarget\)\}/);
  assert.match(reactSource, /onFocus=\{\(event\) => openMegaMenu\(module, event\.currentTarget\)\}/);
  assert.match(runtimeSource, /addEventListener\("mouseenter", \(\) => this\.openMegaMenu/);
  assert.match(runtimeSource, /addEventListener\("focus", \(\) => this\.openMegaMenu/);
  assert.match(runtimeSource, /handleModuleNavigation\(moduleId\)[\s\S]*?this\.openMegaMenu\(moduleId\);/);
});

test('toolbar controls remain aligned and touch targets expand on coarse pointers', async () => {
  const { runtimeCss } = await sources();

  assert.match(runtimeCss, /--openinfra-toolbar-control-height: 2rem;/);
  assert.match(runtimeCss, /\.openinfra-global-toolbar\s*\{[\s\S]*?padding-block: \.5rem !important;/);
  assert.match(runtimeCss, /\.openinfra-global-search-control \.form-control\s*\{[\s\S]*?height: var\(--openinfra-toolbar-control-height\);/);

  assert.match(runtimeCss, /\.openinfra-global-toolbar-inner\s*\{[\s\S]*?grid-template-columns: minmax\(0, 1fr\) minmax\(0, 50%\) minmax\(0, 1fr\);/);
  assert.match(runtimeCss, /\.openinfra-component-nav\s*\{[\s\S]*?justify-content: flex-end !important;[\s\S]*?margin: 0 0 0 auto !important;/);
  assert.match(runtimeCss, /--openinfra-header-nav-active-bg: linear-gradient\(180deg, rgba\(var\(--openinfra-cyan-rgb\), \.105\), rgba\(var\(--openinfra-action-rgb\), \.045\)\);/);
  assert.match(runtimeCss, /\.openinfra-component-nav \.nav-link\.active,[\s\S]*?background-color: transparent !important;[\s\S]*?background-image: var\(--openinfra-header-nav-active-bg\);[\s\S]*?opacity: \.94;/);
  assert.match(runtimeCss, /\.openinfra-component-nav \.nav-link\.active \.openinfra-top-icon,[\s\S]*?color: var\(--openinfra-header-nav-active-icon\);[\s\S]*?opacity: \.82;/);
  assert.doesNotMatch(runtimeCss, /\.openinfra-component-nav \.nav-link\.active,[^}]*background:\s*linear-gradient\([^}]*#fff/i);
  assert.doesNotMatch(runtimeCss, /\.openinfra-component-nav \.nav-link\.active,[^}]*rgba\(255, 255, 255, \.9[3-9]\)/i);
  assert.match(runtimeCss, /--openinfra-toolbar-action-height: 1\.82rem;/);
  assert.match(runtimeCss, /\.openinfra-language-control \.form-select,[\s\S]*?\.openinfra-api-doc-actions \.btn[\s\S]*?height: var\(--openinfra-toolbar-action-height\);/);
  assert.match(runtimeCss, /@media \(pointer: coarse\)[\s\S]*?--openinfra-toolbar-control-height: 2\.75rem;/);
});

test('active sidebar root keeps its surface and turns only icon and text turquoise on hover', async () => {
  const { runtimeCss } = await sources();

  const match = runtimeCss.match(
    /\.openinfra-sidebar-dashboard\.active:hover,[\s\S]*?\.openinfra-accordion-toggle\.active:focus\s*\{(?<body>[^}]*)\}/,
  );
  assert.ok(match?.groups?.body);
  assert.match(match.groups.body, /color: var\(--openinfra-header-nav-active-icon\);/);
  assert.doesNotMatch(match.groups.body, /background|border|box-shadow/);
  assert.match(runtimeCss, /\.openinfra-accordion-toggle svg,[\s\S]*?fill: currentColor;/);
});
