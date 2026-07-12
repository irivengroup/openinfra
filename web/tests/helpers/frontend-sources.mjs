import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const webRoot = resolve(import.meta.dirname, '..', '..');
const projectRoot = resolve(webRoot, '..');
const runtimeAssets = resolve(
  projectRoot,
  'src/openinfra/interfaces/rendering/static/assets',
);

const reactDomainFiles = [
  'data.js',
  'dcim.js',
  'discovery.js',
  'ipam.js',
  'itam.js',
  'rsot.js',
  'security.js',
];
const runtimeDomainFiles = [
  'data.js',
  'dcim.js',
  'discovery.js',
  'integrations.js',
  'ipam.js',
  'itam.js',
  'rsot.js',
  'security.js',
];

async function joinFiles(paths) {
  return (await Promise.all(paths.map((path) => readFile(path, 'utf8')))).join('\n');
}

export async function readReactPortalSource() {
  return joinFiles([
    resolve(webRoot, 'src/main.jsx'),
    resolve(webRoot, 'src/domain-manifest.js'),
    resolve(webRoot, 'src/search-index.js'),
    ...reactDomainFiles.map((name) => resolve(webRoot, 'src/domains', name)),
  ]);
}

export async function readRuntimePortalSource() {
  return joinFiles([
    resolve(runtimeAssets, 'openinfra-web.js'),
    resolve(runtimeAssets, 'openinfra-domain-manifest.js'),
    resolve(runtimeAssets, 'openinfra-search-index.js'),
    ...runtimeDomainFiles.map((name) => resolve(runtimeAssets, 'domains', name)),
  ]);
}
