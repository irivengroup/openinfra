# OpenInfra v0.29.31 — Validation Report

## Scope

Release: `0.29.31`
Increment: P11/IPAM Enterprise++ dashboard parity and API discovery.
Date: 2026-07-07

## Implemented changes

- Added dashboard operations for Enterprise++ IPAM workflows: VRF, aggregates, prefixes, ranges, address records, allocation, reservation wizard, capacity, network bindings, VLAN groups, VXLAN VNIs, VLANs, ASNs, BGP peers, DNS observations, DHCP leases, conflicts and DDI preview.
- Added `ipam` to the HTTP API root discovery document, exposing all related `/api/v1/ipam/*` contracts to automation.
- Updated runtime web assets, React source catalog, frontend validator, OpenAPI, README, UI documentation, architecture documentation, CHANGELOG, CDC and roadmap.
- Preserved backend invariants: browser forms submit normalized payloads through the existing API contracts and do not duplicate domain validation logic.

## Validation results

| Command | Result |
|---|---:|
| `ruff format --check src tests scripts docker` | PASS |
| `ruff check src tests scripts docker` | PASS |
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.31 |
| `PYTHONPATH=src mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `pip-audit --dry-run` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py` | PASS — 769 requirements, 519 entities |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS — 769 requirements |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 42 tests |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profiles |
| `python scripts/native_runtime_smoke.py` | PASS |
| `openinfra installer validate` over all 6 profiles | PASS |
| `openinfra installer dry-run` over all 6 profiles | PASS |
| `PYTHONPATH=src:. pytest --collect-only --no-cov` | PASS — 409 tests collected |
| `pytest` by batches with `--no-cov` | PASS — 409 tests executed |
| `pytest` by batches with `pytest-cov --cov-append` | PASS — combined coverage produced |
| `coverage report --fail-under=98` | PASS — 98% |
| `python scripts/quality_gate.py` | PASS |
| `python -m build` | PASS — wheel and sdist built |
| `python scripts/verify_artifact.py dist/openinfra-0.29.31-py3-none-any.whl` | PASS |

## Timeout handling

A monolithic `pytest` execution exceeded the interactive environment timeout. The complete suite was therefore executed by deterministic batches, first without coverage and then with cumulative coverage append. No test subset was skipped.

## Not executed locally

- `npm run build`: `web/node_modules` is not present in the execution environment.
- Docker Compose live runtime: the `docker` command is not available in the execution environment.

## Residual risks

- Browser production bundle validation is limited to static/runtime JavaScript syntax and catalog validation because Node dependencies are absent.
- Live Docker orchestration remains to be validated in a host with Docker Engine/Compose available.
