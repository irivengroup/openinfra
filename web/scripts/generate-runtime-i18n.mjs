import { chmod, mkdir, rename, rm, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';

import { buildRuntimeI18n, runtimeI18nTarget } from './runtime-i18n-build.mjs';

const generated = await buildRuntimeI18n();
const temporary = `${runtimeI18nTarget}.${process.pid}.tmp`;
await mkdir(dirname(runtimeI18nTarget), { recursive: true, mode: 0o755 });
try {
  await writeFile(temporary, generated, { encoding: 'utf8', mode: 0o644 });
  await chmod(temporary, 0o644);
  await rename(temporary, runtimeI18nTarget);
} finally {
  await rm(temporary, { force: true });
}
console.log(`Generated ${runtimeI18nTarget} (${Buffer.byteLength(generated)} bytes)`);
