# OpenInfra Validation Report — v0.29.20

## Scope

OpenInfra v0.29.20 fixes the operational web dashboard after the ITRM transition:

- all dashboard forms now target the real backend contracts exposed under `/api/v1/*` through the same-origin web proxy;
- form payloads have been aligned with backend-required fields such as `vrf`, `hostname`, `idempotency_key`, `endpoint_url`, `version`, `requested_scope` and `target`;
- the web proxy preserves the `/api/v1/*` upstream prefix instead of stripping `/api`, preventing runtime 404 mismatches;
- `openinfra-web` supports optional server-side backend bearer injection through `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` or `OPENINFRA_BOOTSTRAP_TOKEN`, without exposing credentials to the browser;
- dashboard component pie charts are doubled and responsive through CSS `clamp()` sizing, while remaining mobile-safe;
- the permanent dashboard readiness success alert remains removed; visible success alerts are reserved for form submissions and errors stay explicit.

## Passed validations

- Python compileall on `src`, `tests`, `scripts`
- Frontend static validator
- Runtime asset JavaScript syntax check with `node --check`
- Targeted web/runtime regression tests
- Full test suite by batches with combined coverage data
- Coverage gate `coverage report --fail-under=98`
- Security gate
- Quality gate
- CLI version check
- CDC validation
- Roadmap/CDC enterprise alignment validation
- Installer validation and dry-run
- Autonomous installer validation
- Native runtime smoke test
- Storage/multisite CDC validation

## Coverage

- Tests collected: 391
- Final coverage: 98%
- Required coverage: 98%

## Not executed locally

- `ruff format --check` / `ruff check`: tool unavailable
- `mypy`: tool unavailable
- `bandit`: tool unavailable
- `pip-audit`: tool unavailable
- `python -m build`: `build` module unavailable
- `npm run build`: `web/node_modules` unavailable
- Docker Compose live smoke: Docker unavailable
