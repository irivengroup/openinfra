import assert from 'node:assert/strict';
import { resolve } from 'node:path';

import { build } from 'rolldown';

const webRoot = resolve(import.meta.dirname, '..');
export const runtimeI18nSource = resolve(webRoot, 'src/i18n.js');
export const runtimeI18nTarget = resolve(
  webRoot,
  '../src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js',
);

const GENERATED_HEADER = '// Generated from web/src/i18n.js by Rolldown. Do not edit.\n';

export async function buildRuntimeI18n() {
  const result = await build({
    input: runtimeI18nSource,
    platform: 'browser',
    write: false,
    output: {
      format: 'esm',
      minify: true,
      sourcemap: false,
    },
  });
  const chunks = result.output.filter((item) => item.type === 'chunk');
  assert.equal(chunks.length, 1, 'runtime i18n build must emit exactly one JavaScript chunk');
  return `${GENERATED_HEADER}${chunks[0].code.trimEnd()}\n`;
}
