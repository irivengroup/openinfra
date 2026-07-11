import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const react = fs.readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8');
const packaged = fs.readFileSync(new URL('../../src/openinfra/interfaces/rendering/static/assets/openinfra-web.js', import.meta.url), 'utf8');
const sharedFields = fs.readFileSync(new URL('../src/form-fields.js', import.meta.url), 'utf8');

const expectedOperations = [
  'field-sheet-list', 'field-sheet-get', 'field-sheet-generate', 'field-lock-acquire',
  'field-operation-start', 'field-checklist-record', 'field-evidence-attach',
  'field-evidence-list', 'field-evidence-validate', 'field-operation-complete',
  'field-operation-cancel', 'field-qr-verify', 'field-lock-release',
  'field-offline-create', 'field-offline-list', 'field-offline-get', 'field-offline-sync',
];

test('field operations are grouped under DCIM in both portals', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /Opérations terrain/u);
    for (const operation of expectedOperations) assert.match(source, new RegExp(operation, 'u'));
    assert.doesNotMatch(source, /id:\s*['"]field-operations['"]\s*,\s*label:/u);
  }
});

test('field evidence uses camera-aware bounded file controls and API payload expansion', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /image\/jpeg,image\/png,image\/webp,application\/pdf/u);
    assert.match(source, /capture:\s*['"]environment['"]/u);
    assert.match(source, /2 \* 1024 \* 1024/u);
    assert.match(source, /content_base64/u);
    assert.match(source, /media_type/u);
    assert.match(source, /filename/u);
  }
  assert.match(sharedFields, /type \|\| ''\)\.toLowerCase\(\) === 'file'/u);
  assert.match(sharedFields, /attributes\.accept/u);
});
