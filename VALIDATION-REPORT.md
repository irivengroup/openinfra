# OpenInfra v0.29.65 — Validation Report

## Scope

Release: `0.29.65`

Implemented scope:

- DCIM site lifecycle CRUD.
- DCIM topology catalog for site/building/floor/room/zone/rack selectors.
- Non-destructive retirement cascade for site dependencies.
- Web forms: no free-text fields for DCIM references (`site`, `site_code`, `building`, `building_code`, `floor`, `floor_code`, `room`, `room_code`, `zone`, `zone_code`, `rack`, `row`, `column`).
- Responsive sidebar and mobile/tablet display optimization.

## Validation results

| Validation | Result |
|---|---:|
| Ruff format check on `src tests scripts docker` | PASS |
| Ruff check on `src tests scripts docker` | PASS |
| `compileall` on `src tests scripts` | PASS |
| `node --check openinfra-web.js` | PASS |
| Frontend validator | PASS |
| CLI version | PASS — `0.29.65` |
| OpenAPI YAML parse | PASS |
| Security gate | PASS |
| Enterprise alignment | PASS |
| Autonomous installer validation | PASS — 6 profiles |
| Native runtime smoke | PASS |
| CDC validation | PASS — 811 requirements, 610 tests |
| Roadmap validation | PASS — 19 phases, 114 epics, 8 gates, 80 tests |
| `pytest --collect-only` | PASS — 515 tests collected |
| Unit + architecture tests | PASS — 203 tests |
| Integration tests by deterministic lots | PASS — 312 tests |
| Coverage gate | PASS — 98% |
| Quality gate | PASS |

## Integration test lots

| Lot | Result |
|---|---:|
| CLI / access / audit / autonomous installers / import-export / discovery CLI | PASS — 50 tests |
| DCIM / discovery | PASS — 48 tests |
| editions / export / external auth / ITSM / search / HTTP / identity / import | PASS — 86 tests |
| installer / IPAM | PASS — 32 tests |
| ITAM / ITRM | PASS — 19 tests |
| JSON store / web / PostgreSQL / runtime / security / services / source governance / source of truth | PASS — 85 tests |

## Non executed locally

The following validations were not executed in the current runtime because the tools or live environment were unavailable:

- `mypy`
- `bandit`
- `pip-audit`
- `python -m build`
- full Vite production build
- Docker Compose live runtime

## Packaging

Archives were cleaned before packaging. Runtime caches and temporary validation artifacts are excluded from the release package.
