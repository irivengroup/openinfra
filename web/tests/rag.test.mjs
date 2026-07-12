import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { readReactPortalSource, readRuntimePortalSource } from './helpers/frontend-sources.mjs';

const react = await readReactPortalSource();
const packaged = await readRuntimePortalSource();
const service = fs.readFileSync(new URL('../../src/openinfra/application/rag_services.py', import.meta.url), 'utf8');
const generator = fs.readFileSync(new URL('../../src/openinfra/infrastructure/rag_generator.py', import.meta.url), 'utf8');

const operations = [
  'rag-document-upsert', 'rag-documents', 'rag-document-get',
  'rag-document-deactivate', 'rag-rsot-sync', 'rag-query', 'rag-answers',
  'rag-answer-get', 'rag-job-create', 'rag-jobs', 'rag-job-get',
  'rag-job-run', 'rag-job-artifact',
];

const routes = [
  '/v1/rag/documents/upsert', '/v1/rag/documents', '/v1/rag/documents/get',
  '/v1/rag/documents/deactivate', '/v1/rag/index/rsot', '/v1/rag/query',
  '/v1/rag/answers', '/v1/rag/answers/get', '/v1/rag/jobs/create',
  '/v1/rag/jobs', '/v1/rag/jobs/get', '/v1/rag/jobs/run', '/v1/rag/jobs/artifact',
];

test('governed RAG is grouped under RSOT with route parity', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /Assistant gouverné/u);
    assert.match(source, /Index de connaissances/u);
    assert.match(source, /Imports \/ exports RAG/u);
    assert.doesNotMatch(source, /id:\s*['"]rag['"]\s*,\s*label:/u);
    for (const operation of operations) assert.match(source, new RegExp(operation, 'u'));
    for (const route of routes) assert.match(source, new RegExp(route.replaceAll('/', '\\/'), 'u'));
  }
});

test('governed RAG exposes typed permissions, citations and downloadable exports', () => {
  for (const source of [react, packaged]) {
    assert.match(source, /required_permissions/u);
    assert.match(source, /question/u);
    assert.match(source, /rag-job-artifact/u);
    assert.match(source, /["']?download["']?\s*:\s*true/u);
  }
  for (const source of [react, packaged]) {
    assert.match(source, /["']?name["']?\s*:\s*['"]metadata['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]json['"]/u);
    assert.match(source, /["']?name["']?\s*:\s*['"]payload['"][\s\S]{0,240}?["']?type["']?\s*:\s*['"]json['"]/u);
  }
  assert.match(service, /question_hash/u);
  assert.match(generator, /citations/u);
});

test('governed RAG has no execution or remediation capability', () => {
  assert.doesNotMatch(service, /subprocess|os\.system|shell=True|remediat(?:e|ion)/iu);
  assert.doesNotMatch(generator, /requests\.|httpx|urllib\.request|subprocess/iu);
  for (const source of [react, packaged]) {
    assert.doesNotMatch(source, /\/v1\/rag\/(?:execute|remediate)/u);
  }
});
