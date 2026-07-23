import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const runtime = await readRuntimePortalSource();
const domain = fs.readFileSync(
  new URL('../../src/openinfra/domain/rag.py', import.meta.url),
  'utf8',
);
const service = fs.readFileSync(
  new URL('../../src/openinfra/application/rag_services.py', import.meta.url),
  'utf8',
);

test('governed RAG report exposes cited RSOT objects in both portals', () => {
  for (const source of [react, runtime]) {
    assert.match(source, /rag-query/u);
    assert.match(source, /openinfra-rag-governance-report/u);
    assert.match(source, /openinfra-rag-source-objects/u);
    assert.match(source, /openinfra-rag-citations/u);
    assert.match(source, /source_objects/u);
    assert.match(source, /source_data_mutation_performed/u);
    assert.match(source, /change_validation_required/u);
  }
});

test('RAG answer contract is read-only and requires validation before changes', () => {
  assert.match(domain, /"mode": "read-only"/u);
  assert.match(domain, /"source_data_mutation_performed": False/u);
  assert.match(domain, /"change_validation_required": True/u);
  assert.match(domain, /"execution_capabilities": \[\]/u);
  assert.match(domain, /RagSourceType\.RSOT/u);
  assert.match(service, /source_object_count/u);
  assert.match(service, /source_data_mutation_performed/u);
  assert.match(service, /change_validation_required/u);
});

test('governed RAG still exposes no execution or remediation endpoint', () => {
  for (const source of [react, runtime]) {
    assert.doesNotMatch(source, /\/v1\/rag\/(?:execute|remediate|apply|mutate)/u);
  }
  assert.doesNotMatch(service, /subprocess|os\.system|shell=True/iu);
});
