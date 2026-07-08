# OpenInfra v0.29.71 — Validation Report

Release: `0.29.71`

## Scope

Hotfix CI/CLI après v0.29.70 : la commande `openinfra edition feature-check` accepte désormais les options backend homogènes (`--backend`, `--data`, `--postgres-dsn`) utilisées par le workflow GitHub Actions, sans modifier le contrat métier `--edition` ni les décisions Lite/Pro/Enterprise.

## Changes validated

- CLI `edition feature-check --data <state.json>` accepté.
- Parité restaurée avec `edition list --data` et `edition quota-check --data`.
- Régression d'intégration ajoutée dans `tests/integration/test_editions_feature_gates.py`.
- CDC mis à jour : `REQ-00812` et `TST-CLI-111`.
- Roadmap mise à jour : `TST-P08-CLI-EDITION-DATA-COMPAT`.

## Executed validations

| Command | Result |
| --- | --- |
| `ruff format --check src tests scripts docker` | PASS — 135 files formatted |
| `ruff check src tests scripts docker` | PASS |
| `bandit -q -r src/openinfra` | PASS |
| `mypy src/openinfra` | PASS — 54 source files |
| `python -m compileall -q src tests scripts docker` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 installers |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.71` |
| `PYTHONPATH=src python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 812 requirements, 611 tests |
| `PYTHONPATH=src python -m pytest tests/integration/test_editions_feature_gates.py -q --no-cov` | PASS — 9 tests |
| `PYTHONPATH=src python -m pytest tests/integration/test_cli.py -q --no-cov` | PASS — 20 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 516 tests collected |
| Integration tests by files / batches | PASS — 313 tests |
| `python scripts/quality_gate.py` | PASS — global coverage 98% |
| `python -m build` | PASS — sdist and wheel built locally, excluded from source archive |

## CI smoke reproduced

```bash
TMPDIR="$(mktemp -d)"
PYTHONPATH=src python -m openinfra edition list --data "$TMPDIR/state.json" > "$TMPDIR/editions.json"
PYTHONPATH=src python -m openinfra edition feature-check --data "$TMPDIR/state.json" --tenant default --edition enterprise --capability distributed_discovery_agents > "$TMPDIR/feature.json"
PYTHONPATH=src python -m openinfra edition quota-check --data "$TMPDIR/state.json" --tenant default --edition lite --resource user --increment 1 > "$TMPDIR/quota.json"
```

Result: PASS.

## Not executed locally

- `pip-audit -r requirements/security-audit.txt` could not complete because DNS resolution to `pypi.org` failed in the runtime.
- Full Vite production build was not executed because frontend dependencies are not installed in this runtime.
- Docker Compose live execution was not run in this runtime.
