const LOADERS = Object.freeze({
  dcim: () => import('../../../src/openinfra/interfaces/rendering/static/assets/domains/dcim.js'),
  itam: () => import('../../../src/openinfra/interfaces/rendering/static/assets/domains/itam.js'),
});

const MODULE_CACHE = new Map();

export async function loadManagementOperationSchema(moduleId, operationId) {
  const loader = LOADERS[moduleId];
  if (!loader) return null;
  if (!MODULE_CACHE.has(moduleId)) {
    MODULE_CACHE.set(moduleId, loader().then((loaded) => loaded.default || loaded.moduleDefinition));
  }
  const moduleDefinition = await MODULE_CACHE.get(moduleId);
  return moduleDefinition?.operations?.find((operation) => operation.id === operationId) || null;
}
