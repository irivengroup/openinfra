import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

import { MODULES, loadDomain } from '../src/domain-manifest.js';
import { OpenInfraQueryCache } from '../src/core/query-cache.js';
import { virtualWindow } from '../src/core/virtual-window.js';
import {
  OPENINFRA_WEB_VITAL_BUDGETS,
  installOpenInfraWebVitals,
} from '../src/core/web-vitals.js';

const projectRoot = resolve(import.meta.dirname, '..', '..');
const runtimeAssetRoot = resolve(
  projectRoot,
  'src/openinfra/interfaces/rendering/static/assets',
);
const packageMetadata = JSON.parse(
  await readFile(resolve(projectRoot, 'web/package.json'), 'utf8'),
);

function deferred() {
  let resolvePromise;
  let rejectPromise;
  const promise = new Promise((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return { promise, resolve: resolvePromise, reject: rejectPromise };
}

test('query cache deduplicates inflight reads and expires values deterministically', async () => {
  let now = 1_000;
  let calls = 0;
  const cache = new OpenInfraQueryCache({ defaultTtlMs: 100, clock: () => now });
  const loader = async () => {
    calls += 1;
    return { revision: calls };
  };

  const [first, duplicate] = await Promise.all([
    cache.run('catalog:sites', loader),
    cache.run('catalog:sites', loader),
  ]);
  assert.deepEqual(first, { revision: 1 });
  assert.strictEqual(duplicate, first);
  assert.equal(calls, 1);
  assert.strictEqual(await cache.run('catalog:sites', loader), first);

  now += 101;
  assert.deepEqual(await cache.run('catalog:sites', loader), { revision: 2 });
  assert.equal(calls, 2);
});

test('query cache cancellation and generations prevent stale response replacement', async () => {
  const cache = new OpenInfraQueryCache();
  const oldResult = deferred();
  const freshResult = deferred();
  const stale = cache.run('global-search:default:router', () => oldResult.promise, {
    force: true,
    scope: 'global-search',
  });
  const fresh = cache.run('global-search:default:router', () => freshResult.promise, {
    force: true,
    scope: 'global-search',
  });

  freshResult.resolve('fresh');
  assert.equal(await fresh, 'fresh');
  oldResult.resolve('stale');
  assert.equal(await stale, 'stale');
  assert.equal(cache.get('global-search:default:router'), 'fresh');
});

test('targeted invalidation prevents an older inflight catalog from repopulating cache', async () => {
  const cache = new OpenInfraQueryCache();
  const pending = deferred();
  const request = cache.run('catalog:sites:default', () => pending.promise);
  cache.invalidate('catalog:');
  pending.resolve(['old-site']);
  assert.deepEqual(await request, ['old-site']);
  assert.equal(cache.get('catalog:sites:default'), undefined);
  assert.deepEqual(await cache.run('catalog:sites:default', async () => ['new-site']), ['new-site']);
});

test('virtual window bounds rendering and preserves full scroll geometry', () => {
  assert.deepEqual(
    virtualWindow({ itemCount: 1_000, scrollTop: 4_400, viewportHeight: 440, rowHeight: 44, overscan: 4 }),
    { start: 96, end: 114, offsetTop: 4_224, totalHeight: 44_000 },
  );
  assert.deepEqual(
    virtualWindow({ itemCount: 3, scrollTop: -20, viewportHeight: 0, rowHeight: 0, overscan: 4 }),
    { start: 0, end: 3, offsetTop: 0, totalHeight: 132 },
  );
});

test('Web Vitals observers retain bounded in-memory metrics and budget decisions', () => {
  const callbacks = new Map();
  const observers = [];
  const events = [];
  const target = {
    PerformanceObserver: function PerformanceObserver() {},
    dispatchEvent(event) { events.push(event); },
  };
  const cleanup = installOpenInfraWebVitals({
    target,
    observerFactory: (callback) => {
      const observer = {
        observe(options) { callbacks.set(options.type, callback); },
        disconnect() { observer.disconnected = true; },
        disconnected: false,
      };
      observers.push(observer);
      return observer;
    },
  });

  callbacks.get('largest-contentful-paint')({ getEntries: () => [{ startTime: 2_100 }] });
  callbacks.get('event')({ getEntries: () => [{ duration: 240 }] });
  callbacks.get('longtask')({ getEntries: () => [{ duration: 205 }] });

  assert.deepEqual(OPENINFRA_WEB_VITAL_BUDGETS, { LCP: 2500, INP: 200, LONG_TASK: 200 });
  assert.deepEqual(
    target.__OPENINFRA_WEB_VITALS__.map(({ name, withinBudget }) => ({ name, withinBudget })),
    [
      { name: 'LCP', withinBudget: true },
      { name: 'INP', withinBudget: false },
      { name: 'LONG_TASK', withinBudget: false },
    ],
  );
  assert.equal(events.length, 3);
  cleanup();
  assert.ok(observers.every((observer) => observer.disconnected));
});

test('domain manifest starts metadata-only and coalesces lazy domain loading', async () => {
  const rsot = MODULES.find((module) => module.id === 'rsot');
  const dcim = MODULES.find((module) => module.id === 'dcim');
  assert.equal(rsot.loaded, false);
  assert.deepEqual(rsot.operations, []);
  assert.equal(dcim.loaded, false);
  assert.ok(dcim.stats.operations > 0);

  const [first, second] = await Promise.all([loadDomain('rsot'), loadDomain('rsot')]);
  assert.strictEqual(first, second);
  assert.equal(first.loaded, true);
  assert.ok(first.operations.length > 0);
  assert.equal(MODULES.find((module) => module.id === 'dcim').loaded, false);
});

test('runtime and React cache implementations remain identical and memory-only', async () => {
  const [reactCache, runtimeCache, runtimeManifest, runtimeIndex] = await Promise.all([
    readFile(resolve(projectRoot, 'web/src/core/query-cache.js'), 'utf8'),
    readFile(resolve(runtimeAssetRoot, 'openinfra-query-cache.js'), 'utf8'),
    readFile(resolve(runtimeAssetRoot, 'openinfra-domain-manifest.js'), 'utf8'),
    readFile(resolve(runtimeAssetRoot, 'openinfra-search-index.js'), 'utf8'),
  ]);
  assert.equal(runtimeCache, reactCache);
  assert.doesNotMatch(reactCache, /localStorage|sessionStorage|indexedDB/u);
  assert.match(runtimeManifest, /OPENINFRA_DOMAIN_LOADERS/u);
  const escapedVersion = packageMetadata.version.replaceAll('.', '\\.');
  assert.match(
    runtimeManifest,
    new RegExp(`import\\("\\./domains/dcim\\.js\\?v=${escapedVersion}"\\)`, 'u'),
  );
  assert.match(runtimeIndex, /field-sheet-list/u);
  assert.doesNotMatch(runtimeManifest, /"path": "\/v1\/field/u);
});
