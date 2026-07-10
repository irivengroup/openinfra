import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');

async function sources() {
  const [reactSource, runtimeSource, css, reactHtml, runtimeHtml, i18n] = await Promise.all([
    readFile(resolve(webRoot, 'src/main.jsx'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-web.js'), 'utf8'),
    readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8'),
    readFile(resolve(webRoot, 'index.html'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/index.html'), 'utf8'),
    readFile(resolve(webRoot, 'src/i18n.js'), 'utf8'),
  ]);
  return { reactSource, runtimeSource, css, reactHtml, runtimeHtml, i18n };
}

test('both portals expose semantic landmarks, skip links and screen reader status regions', async () => {
  const { reactSource, runtimeSource, reactHtml, runtimeHtml } = await sources();
  for (const source of [reactSource, runtimeSource]) {
    for (const token of [
      'openinfra-main-content',
      'openinfra-component-navigation',
      'openinfra-global-search',
      'openinfra-live-region',
      'skipToContent',
      'skipToNavigation',
      'skipToSearch',
      'aria-live',
      'aria-atomic',
      'role="status"',
      'role="banner"',
    ]) assert.match(source, new RegExp(token));
  }
  assert.doesNotMatch(reactHtml, /<main id="openinfra-root"/);
  assert.doesNotMatch(runtimeHtml, /<main id="openinfra-root"/);
});

test('component navigation supports keyboard traversal and focus restoration', async () => {
  const { reactSource, runtimeSource } = await sources();
  for (const source of [reactSource, runtimeSource]) {
    for (const key of ['ArrowRight', 'ArrowLeft', 'ArrowDown', 'Home', 'End', 'Escape']) {
      assert.match(source, new RegExp(key));
    }
    assert.match(source, /componentNavigationInstructions/);
    assert.match(source, /openinfra-component-navigation-instructions/);
  }
  assert.match(reactSource, /lastComponentTriggerRef/);
  assert.match(runtimeSource, /lastNavigationModuleId/);
});

test('forms, results and external documentation links expose accessible semantics', async () => {
  const { reactSource, runtimeSource } = await sources();
  assert.match(reactSource, /<form aria-describedby="openinfra-required-fields-notice"/);
  assert.match(reactSource, /role="status" aria-live="polite" aria-atomic="true"/);
  assert.match(runtimeSource, /id="openinfra-operation-form"/);
  assert.match(runtimeSource, /aria-invalid/);
  assert.match(runtimeSource, /requiredIndicator/);
  assert.match(runtimeSource, /reportValidity/);
  for (const source of [reactSource, runtimeSource]) {
    assert.match(source, /opensNewWindow/);
    assert.match(source, /rel="noopener noreferrer"/);
  }
});

test('visual accessibility supports high contrast, reduced motion, clear focus and non-color-only status', async () => {
  const { css } = await sources();
  for (const token of [
    '@media (prefers-reduced-motion: reduce)',
    '@media (prefers-contrast: more)',
    '@media (forced-colors: active)',
    ':focus-visible',
    'scroll-padding-top',
    'openinfra-required-marker',
    'openinfra-error-summary',
    'openinfra-component-bounce-fade',
    'openinfra-megamenu-bounce-fade',
  ]) assert.match(css, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
});

test('the web contract has no sound-only or uncaptioned media surface', async () => {
  const { reactSource, runtimeSource, reactHtml, runtimeHtml } = await sources();
  const combined = `${reactSource}\n${runtimeSource}\n${reactHtml}\n${runtimeHtml}`;
  assert.doesNotMatch(combined, /<(audio|video)\b/i);
  assert.doesNotMatch(combined, /new Audio\s*\(/);
});

test('accessibility labels exist in English and French', async () => {
  const { i18n } = await sources();
  for (const key of [
    'skipToNavigation',
    'skipToSearch',
    'componentNavigationInstructions',
    'navigationOpened',
    'navigationClosed',
    'requiredFieldsNotice',
    'requiredIndicator',
    'opensNewWindow',
  ]) {
    assert.equal((i18n.match(new RegExp(`${key}:`, 'g')) || []).length, 2, `${key} must exist in EN and FR`);
  }
});
