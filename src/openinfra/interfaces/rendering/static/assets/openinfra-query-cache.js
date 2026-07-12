export class OpenInfraQueryCache {
  constructor({ defaultTtlMs = 30_000, maxEntries = 128, clock = () => Date.now() } = {}) {
    this.defaultTtlMs = defaultTtlMs;
    this.maxEntries = maxEntries;
    this.clock = clock;
    this.entries = new Map();
    this.inflight = new Map();
    this.controllers = new Map();
    this.generations = new Map();
  }

  get(key) {
    const entry = this.entries.get(key);
    if (!entry) return undefined;
    if (entry.expiresAt <= this.clock()) {
      this.entries.delete(key);
      return undefined;
    }
    this.entries.delete(key);
    this.entries.set(key, entry);
    return entry.value;
  }

  set(key, value, ttlMs = this.defaultTtlMs) {
    this.entries.delete(key);
    this.entries.set(key, { value, expiresAt: this.clock() + Math.max(0, ttlMs) });
    while (this.entries.size > this.maxEntries) {
      const oldest = this.entries.keys().next().value;
      this.entries.delete(oldest);
      if (!this.inflight.has(oldest)) this.generations.delete(oldest);
    }
    return value;
  }

  nextGeneration(key) {
    const generation = (this.generations.get(key) || 0) + 1;
    this.generations.set(key, generation);
    return generation;
  }

  invalidate(prefix = '') {
    const matches = (key) => !prefix || key.startsWith(prefix);
    for (const key of Array.from(this.entries.keys())) {
      if (matches(key)) this.entries.delete(key);
    }
    for (const key of Array.from(this.inflight.keys())) {
      if (matches(key)) this.nextGeneration(key);
    }
  }

  abort(scope) {
    const active = this.controllers.get(scope);
    if (active) {
      this.nextGeneration(active.key);
      active.controller.abort();
    }
    this.controllers.delete(scope);
  }

  async run(key, loader, { ttlMs = this.defaultTtlMs, force = false, scope = null } = {}) {
    if (!force) {
      const cached = this.get(key);
      if (cached !== undefined) return cached;
      const pending = this.inflight.get(key);
      if (pending) return pending;
    }

    let controller = null;
    if (scope) {
      this.abort(scope);
      controller = new AbortController();
    }
    const generation = this.nextGeneration(key);
    if (scope) this.controllers.set(scope, { controller, key, generation });

    let promise;
    promise = Promise.resolve()
      .then(() => loader(controller?.signal))
      .then((value) => {
        if (this.generations.get(key) !== generation) return value;
        return this.set(key, value, ttlMs);
      })
      .finally(() => {
        if (this.inflight.get(key) === promise) this.inflight.delete(key);
        const active = scope ? this.controllers.get(scope) : null;
        if (active?.controller === controller) this.controllers.delete(scope);
        if (!this.inflight.has(key) && !this.entries.has(key) && this.generations.get(key) === generation) {
          this.generations.delete(key);
        }
      });
    this.inflight.set(key, promise);
    return promise;
  }
}
