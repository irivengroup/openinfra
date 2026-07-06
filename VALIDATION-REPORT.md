# OpenInfra Validation Report — v0.29.19

## Scope

OpenInfra v0.29.19 promotes the former public RI/SOT component naming to `ITRM` (`IT Ressources Management`) across UI, CLI, API, RBAC, audit labels, documentation, CDC and roadmap. Legacy aliases `ri` and `sot` remain available only as deprecated migration aliases and are scheduled for progressive removal.

The dashboard home no longer displays a permanent success alert for backend readiness. Visible success alerts are now reserved for form submissions; errors remain explicit.

## Passed validations

- Python compileall on `src`, `tests`, `scripts`, `docker`
- Frontend static validator
- Runtime asset JavaScript syntax check with `node --check`
- Targeted web/ITRM/API regression tests
- Full test suite by batches with combined coverage data
- Coverage gate `coverage report --fail-under=98`
- Security gate
- Quality gate
- CLI version check
- CDC validation
- Roadmap validation
- Installer validation and dry-run
- Autonomous installer validation
- Enterprise alignment validation
- Native runtime smoke test
- Storage/multisite CDC validation

## Coverage

- Tests collected: 389
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
