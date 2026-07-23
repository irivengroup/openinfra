import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const webRoot = resolve(import.meta.dirname, '..');
export const runtimeI18nSource = resolve(webRoot, 'src/i18n.js');
export const runtimeI18nTarget = resolve(
  webRoot,
  '../src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js',
);

const GENERATED_HEADER_PREFIX =
  '// Generated from web/src/i18n.js by Rolldown. Source SHA-256: ';

function sha256(content) {
  return createHash('sha256').update(content, 'utf8').digest('hex');
}

function generatedHeader(sourceDigest) {
  return `${GENERATED_HEADER_PREFIX}${sourceDigest}. Do not edit.\n`;
}

async function loadRolldownBuild() {
  try {
    const module = await import('rolldown');
    return module.build;
  } catch (error) {
    if (error?.code === 'ERR_MODULE_NOT_FOUND') {
      return null;
    }
    throw error;
  }
}

async function readVerifiedPackagedRuntime(expectedHeader) {
  const packaged = await readFile(runtimeI18nTarget, 'utf8');
  assert.ok(
    packaged.startsWith(expectedHeader),
    'Rolldown is unavailable and the packaged runtime i18n asset does not match web/src/i18n.js',
  );
  return packaged;
}

export async function buildRuntimeI18n() {
  const source = await readFile(runtimeI18nSource, 'utf8');
  const header = generatedHeader(sha256(source));
  const build = await loadRolldownBuild();
  if (build === null) {
    return readVerifiedPackagedRuntime(header);
  }

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
  return `${header}${chunks[0].code.trimEnd()}\n`;
}
