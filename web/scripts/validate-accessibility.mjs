import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');
const files = {
  react: await readFile(resolve(webRoot, 'src/main.jsx'), 'utf8'),
  runtime: await readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-web.js'), 'utf8'),
  css: await readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8'),
  index: await readFile(resolve(webRoot, 'index.html'), 'utf8'),
  runtimeIndex: await readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/index.html'), 'utf8'),
};

for (const [name, source] of Object.entries({ react: files.react, runtime: files.runtime })) {
  for (const token of ['openinfra-skip-links', 'openinfra-live-region', 'openinfra-component-navigation', 'aria-live', 'aria-atomic', 'ArrowRight', 'ArrowLeft', 'ArrowDown', 'requiredFieldsNotice', 'opensNewWindow', 'openinfra-graph-canvas', 'openinfra-spof-ranking']) {
    assert.match(source, new RegExp(token), `${name} portal misses ${token}`);
  }
  assert.match(source, name === 'react' ? /tabIndex=\{0\}/ : /tabindex=\"0\"/, `${name} graph must be keyboard reachable`);
  assert.match(source, /role=\"img\"/, `${name} graph must expose an image role`);
  assert.doesNotMatch(source, /<(audio|video)\b/i, `${name} must not introduce media without an explicit caption/transcript contract`);
}
for (const token of ['prefers-reduced-motion', 'prefers-contrast', 'forced-colors', 'focus-visible', 'openinfra-component-bounce-fade', 'openinfra-graph-node', 'openinfra-spof-ratio']) {
  assert.match(files.css, new RegExp(token), `theme misses ${token}`);
}
assert.doesNotMatch(files.index, /<main id="openinfra-root"/);
assert.doesNotMatch(files.runtimeIndex, /<main id="openinfra-root"/);
console.log('OpenInfra WCAG 2.2 AA accessibility contract valid');
