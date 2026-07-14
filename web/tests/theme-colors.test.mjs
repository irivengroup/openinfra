import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');

function parseHexVariable(css, name) {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6});`));
  assert.ok(match, `CSS variable --${name} must be defined with a six-digit hexadecimal color`);
  return match[1];
}

function relativeLuminance(hexColor) {
  const channels = hexColor.slice(1).match(/.{2}/g).map((value) => Number.parseInt(value, 16) / 255);
  const linear = channels.map((channel) => (
    channel <= 0.04045
      ? channel / 12.92
      : ((channel + 0.055) / 1.055) ** 2.4
  ));
  return (0.2126 * linear[0]) + (0.7152 * linear[1]) + (0.0722 * linear[2]);
}

function contrastRatio(first, second) {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  const lighter = Math.max(firstLuminance, secondLuminance);
  const darker = Math.min(firstLuminance, secondLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}

async function themes() {
  const [reactTheme, runtimeTheme] = await Promise.all([
    readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-web.css'), 'utf8'),
  ]);
  return { reactTheme, runtimeTheme };
}

test('React and packaged runtime share exactly the same semantic color theme', async () => {
  const { reactTheme, runtimeTheme } = await themes();
  assert.equal(runtimeTheme, reactTheme);
});

test('secondary text remains visibly blue and WCAG AA on OpenInfra light surfaces', async () => {
  const { reactTheme } = await themes();
  const pageBackground = parseHexVariable(reactTheme, 'openinfra-page-bg');
  const colors = [
    parseHexVariable(reactTheme, 'openinfra-text-primary'),
    parseHexVariable(reactTheme, 'openinfra-text-secondary'),
    parseHexVariable(reactTheme, 'openinfra-text-muted'),
    parseHexVariable(reactTheme, 'openinfra-text-subtle'),
  ];

  for (const color of colors) {
    assert.ok(contrastRatio(color, '#ffffff') >= 4.5, `${color} must pass WCAG AA on white`);
    assert.ok(contrastRatio(color, pageBackground) >= 4.5, `${color} must pass WCAG AA on the page background`);
    const [, red, green, blue] = color.match(/^#(..)(..)(..)$/).map((value, index) => (
      index === 0 ? value : Number.parseInt(value, 16)
    ));
    assert.ok(blue > red, `${color} must preserve an explicit blue hue`);
  }
});

test('Bootstrap text helpers use OpenInfra semantic navy tokens instead of gray defaults', async () => {
  const { reactTheme } = await themes();
  assert.match(reactTheme, /\.text-muted,\s*\n\.text-body-secondary\s*\{\s*\n\s*color: var\(--openinfra-text-muted\) !important;/);
  assert.match(reactTheme, /\.text-secondary\s*\{\s*\n\s*color: var\(--openinfra-text-secondary\) !important;/);
  assert.match(reactTheme, /--bs-secondary-color: var\(--openinfra-text-secondary\);/);
  assert.match(reactTheme, /--bs-tertiary-color: var\(--openinfra-text-muted\);/);
  assert.doesNotMatch(reactTheme, /color:\s*rgba\(var\(--openinfra-ink-rgb\),\s*\.[0-9]+\)/);
  assert.doesNotMatch(reactTheme, /var\(--openinfra-muted\)/);
});

test('visual excellence layer preserves premium surfaces and restrained interaction depth', async () => {
  const { reactTheme } = await themes();
  for (const token of [
    '--openinfra-surface: #ffffff;',
    '--openinfra-surface-soft: #f7faff;',
    '--openinfra-radius-xl: 1.55rem;',
    '--openinfra-elevation-1:',
    '--openinfra-elevation-2:',
    '--openinfra-transition:',
  ]) {
    assert.ok(reactTheme.includes(token), `missing visual-system token ${token}`);
  }
  assert.match(reactTheme, /\.openinfra-titlebar::before\s*\{/);
  assert.match(reactTheme, /\.table thead th\s*\{/);
  assert.match(reactTheme, /@supports not \(\(-webkit-backdrop-filter:/);
  assert.match(reactTheme, /@media \(prefers-contrast: more\)/);
  assert.match(reactTheme, /@media \(prefers-reduced-motion: reduce\)/);
  assert.doesNotMatch(reactTheme, /^\s*filter:\s*blur\(/m);
});

test('approved OpenInfra palette remains unchanged in the transparent depth release', async () => {
  const { reactTheme } = await themes();
  const expectedPalette = new Map([
    ['openinfra-ink', '#001b41'],
    ['openinfra-navy', '#001b41'],
    ['openinfra-navy-2', '#052f6f'],
    ['openinfra-blue', '#003d8f'],
    ['openinfra-action', '#0066ff'],
    ['openinfra-cyan', '#00c2ff'],
    ['openinfra-green', '#15a362'],
    ['openinfra-fuchsia', '#ff00ff'],
    ['openinfra-page-bg', '#f4f8ff'],
  ]);

  for (const [name, expected] of expectedPalette) {
    assert.equal(parseHexVariable(reactTheme, name).toLowerCase(), expected, `--${name} must remain unchanged`);
  }
});

test('sidebar root menu and contextual page titles use the darkest approved midnight blue', async () => {
  const { reactTheme } = await themes();
  assert.match(
    reactTheme,
    /\/\* v0\.32\.7:[\s\S]*?\.openinfra-sidebar-dashboard,\s*\n\.openinfra-accordion-toggle\s*\{\s*\n\s*color: var\(--openinfra-ink\);/,
  );
  assert.match(
    reactTheme,
    /\.openinfra-titlebar h1,\s*\n\.openinfra-operation-card h2\s*\{\s*\n\s*color: var\(--openinfra-ink\);/,
  );
  assert.match(reactTheme, /\.openinfra-sidebar-context-title\s*\{[\s\S]*?color: var\(--openinfra-ink\);/);
});

test('transparent depth is applied to surfaces without fading readable content', async () => {
  const { reactTheme } = await themes();
  const releaseLayer = reactTheme.slice(reactTheme.indexOf('/* v0.32.7:'));
  assert.ok(releaseLayer.length > 0, 'v0.32.7 transparency layer must exist');
  for (const selector of [
    '.openinfra-sidebar',
    '.openinfra-titlebar',
    '.openinfra-global-toolbar',
    '.openinfra-global-search-results',
    '.openinfra-mega-menu-group',
  ]) {
    assert.ok(releaseLayer.includes(selector), `${selector} must participate in the depth layer`);
  }
  assert.match(releaseLayer, /background:\s*rgba\(255, 255, 255, \.9\);/);
  assert.match(releaseLayer, /backdrop-filter: blur\(18px\) saturate\(125%\);/);
  assert.match(releaseLayer, /@media \(prefers-contrast: more\)/);
  assert.doesNotMatch(releaseLayer, /^\s*opacity:\s*\.[0-9]+;/m, 'surface transparency must not fade child content');
});
