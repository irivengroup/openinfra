import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const reactMain = readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8');
const reactCss = readFileSync(new URL('../src/openinfra-theme.css', import.meta.url), 'utf8');
const runtimeMain = readFileSync(
  new URL('../../src/openinfra/interfaces/rendering/static/assets/openinfra-web.js', import.meta.url),
  'utf8',
);
const runtimeCss = readFileSync(
  new URL('../../src/openinfra/interfaces/rendering/static/assets/openinfra-web.css', import.meta.url),
  'utf8',
);

for (const [name, source] of [['React portal', reactMain], ['runtime portal', runtimeMain]]) {
  test(`${name} renders one statistics card and pie chart per business component`, () => {
    assert.match(source, /openinfra-component-card/);
    assert.match(source, /openinfra-pie-chart/);
    assert.match(source, /readOperations/);
    assert.match(source, /writeOperations/);
    assert.match(source, /distributionChart/);
  });
}

test('both portal styles keep responsive accessible pie charts', () => {
  for (const source of [reactCss, runtimeCss]) {
    assert.match(source, /--openinfra-pie-size:\s*clamp\(8rem, 14vw, 10\.5rem\)/);
    assert.match(source, /conic-gradient/);
    assert.match(source, /\.openinfra-component-card/);
  }
});
