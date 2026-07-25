import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

const projectRoot = resolve(import.meta.dirname, '../..');

async function source(relativePath) {
  return readFile(resolve(projectRoot, relativePath), 'utf8');
}

test('global search clients enforce the backend maximum limit', async () => {
  const [react, runtime, backend] = await Promise.all([
    source('web/src/main.jsx'),
    source('src/openinfra/interfaces/rendering/static/assets/openinfra-web.js'),
    source('src/openinfra/application/search_services.py'),
  ]);

  assert.match(react, /GLOBAL_SEARCH_BACKEND_LIMIT = 25/);
  assert.match(react, /Math\.min\(GLOBAL_SEARCH_BACKEND_LIMIT, Math\.max\(1, parsed\)\)/);
  assert.match(react, /query, GLOBAL_SEARCH_BACKEND_LIMIT/);
  assert.match(runtime, /this\.globalSearchUrl\(query, 25\)/);
  assert.match(runtime, /Math\.min\(25, Math\.max\(1, parsedLimit\)\)/);
  assert.match(backend, /global search limit must be between 1 and 25/);
  assert.doesNotMatch(react, /query, 80/);
  assert.doesNotMatch(runtime, /globalSearchUrl\(query, 80\)/);
});
