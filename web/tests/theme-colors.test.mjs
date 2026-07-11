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
