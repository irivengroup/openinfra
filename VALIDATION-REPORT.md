# OpenInfra v0.29.32 — Validation Report

## Scope

Release: `0.29.32`
Increment: P11/IPAM operational topology graph.
Date: 2026-07-07

## Implemented changes

- Added the operational IPAM topology graph through `GET /api/v1/ipam/topology`.
- Added CLI command `openinfra ipam topology`.
- Added dashboard operation **Topologie opérationnelle IPAM**.
- Consolidated VRF, aggregates, prefixes, ranges, address records, reservations, VLAN groups, VLANs, VXLAN VNIs, ASNs, BGP peers, DNS observations and DHCP leases into normalized graph `nodes` and `edges`.
- Added graph summary and integrity metadata including orphan-edge detection.
- Reused existing IPAM repositories and services without adding parallel storage.
- Added API discovery and OpenAPI documentation for the topology contract.
- Updated runtime web assets, React source catalog, frontend validator, README, UI documentation, architecture documentation, CHANGELOG, CDC and roadmap.
- Removed duplicated topology helper code from the UI service so the topology implementation remains centralized in `IpamModelService`.

## Validation results

| Command | Result |
|---|---:|
| `ruff format --check src tests scripts docker` | PASS |
| `ruff check src tests scripts docker` | PASS |
| `python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.32 |
| `PYTHONPATH=src mypy src/openinfra` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `pip-audit --dry-run` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 770 requirements, 519 entities |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 770 requirements |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py docs/specifications/OpenInfra-Roadmap-Developpement-v2` | PASS — 19 phases, 114 epics, 8 gates, 43 tests |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profiles |
| `python scripts/native_runtime_smoke.py` | PASS |
| `openinfra installer validate` over all 6 profiles | PASS |
| `openinfra installer dry-run` over all 6 profiles | PASS |
| `PYTHONPATH=src:. pytest --collect-only -q -o addopts=''` | PASS — 410 tests collected |
| `pytest` by deterministic batches without coverage | PASS — 410 tests executed |
| `coverage run --parallel-mode -m pytest ...` by deterministic batches | PASS — combined coverage produced |
| `coverage report --fail-under=98` | PASS — 98.00745303825386% |
| `python scripts/quality_gate.py` | PASS |
| `python -m build` | PASS — wheel and sdist built |
| `python scripts/verify_artifact.py dist/openinfra-0.29.32-py3-none-any.whl` | PASS |

## Timeout handling

A monolithic `pytest` execution exceeded the interactive environment timeout. The complete suite was executed by deterministic batches, first without coverage and then with cumulative `coverage run --parallel-mode` data. No test subset was skipped.

## Not executed locally

- `npm run build`: `web/node_modules` is not present in the execution environment.
- Docker Compose live runtime: the `docker` command is not available in the execution environment.

## Residual risks

- Browser production bundle validation is limited to static/runtime JavaScript syntax and catalog validation because Node dependencies are absent.
- Live Docker orchestration remains to be validated in a host with Docker Engine/Compose available.
