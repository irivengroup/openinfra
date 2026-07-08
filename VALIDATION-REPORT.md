# OpenInfra v0.29.66 — Validation Report

## Scope

Release: `0.29.66`

Implemented scope:

- Hotfix for the v0.29.65 responsive sidebar regression.
- Removal of the global `.openinfra-sidebar { width: 100%; }` override that made the sidebar consume the whole desktop viewport width.
- Extra-small mobile navigation with an SVG menu icon button.
- Mobile menu panel hidden by default, opened by the menu button, closable through backdrop, and closed automatically after a sidebar entry is selected.
- Runtime static assets and React source kept synchronized.
- Frontend validation and web integration tests extended to prevent regression.

## Validation results

| Validation | Result |
|---|---:|
| `python -m compileall -q src tests scripts` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| OpenAPI YAML parse | PASS — `0.29.66` |
| CLI version | PASS — `0.29.66` |
| `pytest tests/integration/test_openinfra_web.py -q --no-cov` | PASS — 13 tests |
| Impact regression set: runtime Docker, discovery CLI, HTTP API, discovery domain, web | PASS — 66 tests |
| `pytest tests/unit tests/architecture -q --no-cov` | PASS — 203 tests |
| Integration tests by chunks | PASS — 312 tests |
| `pytest --collect-only -q --no-cov` | PASS — 515 tests collected |
| `python scripts/quality_gate.py` | NOT PASS locally — coverage report used incomplete `.coverage` data after the full coverage run timed out |
| Full `python -m pytest` with project coverage gate | NOT COMPLETED locally — timed out in this sandbox before completion |
| Ruff format/check | NOT EXECUTED locally — `ruff` not installed |
| mypy | NOT EXECUTED locally — `mypy` not installed |
| bandit | NOT EXECUTED locally — `bandit` not installed |
| pip-audit | NOT EXECUTED locally — `pip-audit` not installed |
| `python -m build` | NOT EXECUTED locally — `build` module not installed |
| Vite production build | NOT EXECUTED locally — frontend dependencies are not installed in this sandbox |
| Docker Compose live smoke | NOT EXECUTED locally — Docker runtime unavailable in this sandbox |

## Commands executed

```bash
python -m compileall -q src tests scripts
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
python scripts/validate_frontend.py --project-root .
python scripts/security_gate.py --project-root .
python scripts/validate_autonomous_installer.py --root installers
python scripts/validate_enterprise_alignment.py --project-root .
python scripts/native_runtime_smoke.py
python - <<'PY'
from pathlib import Path
import yaml
for path in ['docs/api/openapi.yaml', 'docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/09-API/OpenAPI/openapi.yaml']:
    data = yaml.safe_load(Path(path).read_text())
    print(path, data['info']['version'])
PY
PYTHONPATH=src python -m openinfra version
PYTHONPATH=src python -m pytest tests/integration/test_openinfra_web.py -q --no-cov
PYTHONPATH=src python -m pytest --no-cov -q \
  tests/integration/test_runtime_docker_environment.py \
  tests/integration/test_cli_discovery.py \
  tests/integration/test_http_api.py \
  tests/unit/test_discovery_domain.py \
  tests/integration/test_openinfra_web.py
PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture
PYTHONPATH=src python -m pytest --collect-only -q --no-cov
```

Integration tests were executed by chunks to avoid sandbox command timeouts.

## Residual risks

- Browser-level visual validation was not executed because no browser automation stack is available in this sandbox.
- Full coverage gate remains to be rerun in CI or a local development environment with enough runtime budget and the project QA tools installed.
- The change is intentionally limited to UI layout/runtime assets; no backend API, CLI, database or domain behavior was modified.
