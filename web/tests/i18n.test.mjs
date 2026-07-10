import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

import {
  DEFAULT_LANGUAGE,
  OpenInfraI18n,
  detectBrowserLanguage,
  localizeOpenInfraCatalog,
} from '../src/i18n.js';

const webRoot = resolve(import.meta.dirname, '..');
const projectRoot = resolve(webRoot, '..');

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
  };
}

test('browser language detection supports only French and English with English fallback', () => {
  assert.equal(detectBrowserLanguage({ languages: ['fr-FR', 'en-US'] }), 'fr');
  assert.equal(detectBrowserLanguage({ languages: ['en-GB'] }), 'en');
  assert.equal(detectBrowserLanguage({ languages: ['de-DE', 'es-ES'], language: 'it-IT' }), DEFAULT_LANGUAGE);
  assert.equal(detectBrowserLanguage({}), 'en');
});

test('a persisted explicit choice overrides browser detection and remains switchable', () => {
  const storage = memoryStorage({ 'openinfra.language': 'fr' });
  const i18n = new OpenInfraI18n({ navigatorObject: { languages: ['en-US'] }, storage });
  assert.equal(i18n.language, 'fr');
  assert.equal(i18n.t('execute'), 'Exécuter');
  assert.equal(i18n.label('Pays'), 'Pays');

  assert.equal(i18n.setLanguage('en'), 'en');
  assert.equal(i18n.t('execute'), 'Execute');
  assert.equal(i18n.label('Pays'), 'Country');
  assert.equal(storage.getItem('openinfra.language'), 'en');

  assert.equal(i18n.setLanguage('pt-BR'), 'en');
});

test('catalog localization covers modules, operations, fields, contexts and resource taxonomy', () => {
  const modules = [{
    id: 'dcim',
    label: 'DCIM',
    description: 'Sites, bâtiments et salles.',
    operations: [{
      id: 'dcim-building-create',
      label: 'Créer un bâtiment',
      body: [{ name: 'building_name', label: 'Nom bâtiment' }],
    }],
  }];
  const contexts = { dcim: [{ label: 'Sites & dépendances', operationIds: ['dcim-building-create'] }] };
  const taxonomy = { server: [{ value: 'rack-server', label: 'Rack server' }] };
  const categories = [{ value: 'server', label: 'Server' }];

  localizeOpenInfraCatalog({ modules, contexts, resourceTaxonomy: taxonomy, resourceCategories: categories }, 'fr');
  assert.equal(modules[0].operations[0].label, 'Créer un bâtiment');
  assert.equal(taxonomy.server[0].label, 'Serveur rack');
  assert.equal(categories[0].label, 'Serveurs');

  localizeOpenInfraCatalog({ modules, contexts, resourceTaxonomy: taxonomy, resourceCategories: categories }, 'en');
  assert.equal(modules[0].operations[0].label, 'Create building');
  assert.equal(modules[0].operations[0].body[0].label, 'Building name');
  assert.equal(contexts.dcim[0].label, 'Sites & dependencies');
  assert.equal(taxonomy.server[0].label, 'Rack server');
  assert.equal(categories[0].label, 'Server');

  localizeOpenInfraCatalog({ modules, contexts, resourceTaxonomy: taxonomy, resourceCategories: categories }, 'fr');
  assert.equal(modules[0].operations[0].body[0].label, 'Nom bâtiment');
  assert.equal(contexts.dcim[0].label, 'Sites & dépendances');
});

test('country names are rendered from ISO alpha-2 values in the active language', () => {
  const i18n = new OpenInfraI18n({ navigatorObject: { languages: ['en'] }, storage: memoryStorage() });
  assert.match(i18n.countryName('FR', 'France'), /France/i);
  i18n.setLanguage('fr', { persist: false });
  assert.match(i18n.countryName('GB', 'Royaume-Uni'), /Royaume-Uni/i);
  assert.equal(i18n.countryName('invalid', 'Fallback'), 'Fallback');
});

test('runtime values, counts, continents and floor display names remain localized without changing identifiers', () => {
  const i18n = new OpenInfraI18n({ navigatorObject: { languages: ['en'] }, storage: memoryStorage() });
  assert.equal(i18n.optionLabel('dead-letter'), 'Dead-letter queue');
  assert.equal(i18n.optionLabel('software_publisher'), 'Software publisher');
  assert.equal(i18n.count(1, 'result', 'results'), '1 result');
  assert.equal(i18n.count(3, 'result', 'results'), '3 results');
  assert.equal(i18n.continentName('North America'), 'North America');
  assert.equal(i18n.floorName(-1, 'Basement 1'), 'Basement 1');
  assert.equal(i18n.floorName(0, 'Ground floor'), 'Ground floor');
  assert.equal(i18n.floorName(2, 'Executive'), 'Level 2 — Executive');

  i18n.setLanguage('fr', { persist: false });
  assert.equal(i18n.optionLabel('dead-letter'), 'File de quarantaine');
  assert.equal(i18n.optionLabel('software_publisher'), 'Éditeur logiciel');
  assert.equal(i18n.count(1, 'result', 'results'), '1 résultat');
  assert.equal(i18n.count(3, 'result', 'results'), '3 résultats');
  assert.equal(i18n.continentName('North America'), 'Amérique du Nord');
  assert.equal(i18n.floorName(-1, 'Basement 1'), 'Sous-sol 1');
  assert.equal(i18n.floorName(0, 'Ground floor'), 'Rez-de-chaussée');
  assert.equal(i18n.floorName(2, 'Executive'), 'Étage 2 — Executive');
});

test('React and packaged runtime use the same internationalization implementation', async () => {
  const [sourceI18n, runtimeI18n, reactSource, runtimeSource, sourceHtml, runtimeHtml] = await Promise.all([
    readFile(resolve(webRoot, 'src/i18n.js'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js'), 'utf8'),
    readFile(resolve(webRoot, 'src/main.jsx'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/assets/openinfra-web.js'), 'utf8'),
    readFile(resolve(webRoot, 'index.html'), 'utf8'),
    readFile(resolve(projectRoot, 'src/openinfra/interfaces/rendering/static/index.html'), 'utf8'),
  ]);
  assert.equal(runtimeI18n, sourceI18n);
  assert.match(reactSource, /OpenInfraI18n/);
  assert.match(runtimeSource, /openinfra-i18n\.js/);
  assert.match(reactSource, /id="openinfra-language"/);
  assert.match(runtimeSource, /id="openinfra-language"/);
  assert.match(sourceHtml, /<html lang="en">/);
  assert.match(runtimeHtml, /<html lang="en">/);
});
