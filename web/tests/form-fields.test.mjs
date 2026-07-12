import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

import {
  inferValidationKind,
  inputTypeForField,
  isValidCidr,
  isValidIpAddress,
  normalizeFieldValue,
  validateFieldValue,
} from '../src/form-fields.js';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');
const react = await readReactPortalSource();
const runtime = await readRuntimePortalSource();
const sourceHelper = await readFile(resolve(webRoot, 'src/form-fields.js'), 'utf8');
const runtimeHelper = await readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-form-fields.js'), 'utf8');
const theme = await readFile(resolve(webRoot, 'src/openinfra-theme.css'), 'utf8');


test('date and datetime fields use native calendar controls and normalized values', () => {
  const date = { name: 'as_of', label: 'Date de référence', placeholder: '2026-07-10' };
  const datetime = { name: 'observed_at', label: 'Observé le', placeholder: '2026-07-10T12:30:00Z' };
  assert.equal(inferValidationKind(date), 'date');
  assert.equal(inputTypeForField(date), 'date');
  assert.equal(inferValidationKind(datetime), 'datetime');
  assert.equal(inputTypeForField(datetime), 'datetime-local');
  assert.equal(normalizeFieldValue(date, '2026-07-10'), '2026-07-10');
  assert.equal(normalizeFieldValue(datetime, '2026-07-10T12:30'), '2026-07-10T12:30:00.000Z');
  assert.equal(validateFieldValue(date, '2026-02-30').valid, false);
});


test('free-form network and contact values are validated before submission', () => {
  assert.equal(isValidIpAddress('192.0.2.10'), true);
  assert.equal(isValidIpAddress('2001:db8::10'), true);
  assert.equal(isValidIpAddress('999.0.0.1'), false);
  assert.equal(isValidCidr('192.0.2.0/24'), true);
  assert.equal(isValidCidr('2001:db8::/64'), true);
  assert.equal(isValidCidr('192.0.2.0/64'), false);
  assert.equal(validateFieldValue({ name: 'email' }, 'ops@example.org').valid, true);
  assert.equal(validateFieldValue({ name: 'email' }, 'ops@invalid').valid, false);
  assert.equal(validateFieldValue({ name: 'telephone' }, '+33 1 44 55 66 77').valid, true);
  assert.equal(validateFieldValue({ name: 'postal_code' }, '75008', { countryCode: 'FR' }).valid, true);
  assert.equal(validateFieldValue({ name: 'postal_code' }, '75A08', { countryCode: 'FR' }).valid, false);
  assert.equal(validateFieldValue({ name: 'management_ip' }, '10.10.10.256').valid, false);
  assert.equal(validateFieldValue({ name: 'mac_address' }, '00:11:22:33:44:55').valid, true);
  assert.equal(validateFieldValue({ name: 'endpoint_url' }, 'javascript:alert(1)').valid, false);
  assert.equal(validateFieldValue({ name: 'payload', type: 'json' }, '{"safe":true}').valid, true);
  assert.equal(validateFieldValue({ name: 'payload', type: 'json' }, '{broken}').valid, false);
});


test('React and packaged runtime share the exact validation implementation', () => {
  assert.equal(runtimeHelper, sourceHelper);
  for (const source of [react, runtime]) {
    assert.match(source, /normalizeFieldDefinition/);
    assert.match(source, /validateControl/);
    assert.match(source, /formCountryCode/);
  }
});


test('graph operations are grouped under RSOT and no standalone graph component remains', () => {
  for (const source of [react, runtime]) {
    assert.doesNotMatch(source, /\{ id: ['"]graph['"], label:/);
    assert.match(source, /["']?label["']?\s*:\s*["']Exploration["']/);
    assert.match(source, /["']?label["']?\s*:\s*["']Analyse d’impact["']/);
    assert.match(source, /["']?label["']?\s*:\s*["']Exports["']/);
  }
});


test('form focus changes border color without enlarging the contour', () => {
  assert.match(theme, /:where\(\.form-control, \.form-select\):focus-visible/);
  assert.match(theme, /box-shadow: none !important/);
  assert.match(theme, /transform: none/);
  assert.match(theme, /input\.form-control\[type="date"\]/);
  assert.match(theme, /input\.form-control\[type="datetime-local"\]/);
});
