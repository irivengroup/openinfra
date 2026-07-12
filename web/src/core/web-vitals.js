export const OPENINFRA_WEB_VITAL_BUDGETS = Object.freeze({ LCP: 2500, INP: 200, LONG_TASK: 200 });

function emitMetric(metric, target = globalThis) {
  const history = Array.isArray(target.__OPENINFRA_WEB_VITALS__) ? target.__OPENINFRA_WEB_VITALS__ : [];
  history.push(metric);
  target.__OPENINFRA_WEB_VITALS__ = history.slice(-64);
  if (typeof target.dispatchEvent === "function" && typeof CustomEvent === "function") {
    target.dispatchEvent(new CustomEvent("openinfra:web-vital", { detail: metric }));
  }
}

export function installOpenInfraWebVitals({ target = globalThis, observerFactory = (callback) => new PerformanceObserver(callback) } = {}) {
  if (typeof target.PerformanceObserver !== "function" && typeof PerformanceObserver !== "function") return () => {};
  const observers = [];
  const observe = (type, handler, options = {}) => {
    try {
      const observer = observerFactory((list) => {
        for (const entry of list.getEntries()) handler(entry);
      });
      observer.observe({ type, buffered: true, ...options });
      observers.push(observer);
    } catch (_error) {
      // Unsupported entry types must not break the dashboard.
    }
  };
  observe("largest-contentful-paint", (entry) => emitMetric({ name: "LCP", value: entry.startTime, budget: OPENINFRA_WEB_VITAL_BUDGETS.LCP, withinBudget: entry.startTime <= OPENINFRA_WEB_VITAL_BUDGETS.LCP }, target));
  observe("event", (entry) => {
    if ((entry.duration || 0) > 0) emitMetric({ name: "INP", value: entry.duration, budget: OPENINFRA_WEB_VITAL_BUDGETS.INP, withinBudget: entry.duration <= OPENINFRA_WEB_VITAL_BUDGETS.INP }, target);
  }, { durationThreshold: 40 });
  observe("longtask", (entry) => emitMetric({ name: "LONG_TASK", value: entry.duration, budget: OPENINFRA_WEB_VITAL_BUDGETS.LONG_TASK, withinBudget: entry.duration <= OPENINFRA_WEB_VITAL_BUDGETS.LONG_TASK }, target));
  return () => observers.forEach((observer) => observer.disconnect());
}
