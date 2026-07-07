# OpenInfra v0.29.43 — rapport de validation

## Périmètre livré

- Profil de support ITAM par actif physique.
- Garantie/support constructeur conservés comme référence canonique séparée.
- Contrats de support tiers ajoutés sans écraser les informations constructeur.
- API HTTP, CLI, RBAC, audit, persistance JSON/PostgreSQL et migration PostgreSQL alignés.
- Documentation, OpenAPI, CDC et roadmap mis à jour.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `PYTHONPATH=src python -m compileall -q src tests scripts docker` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.43 |
| `python scripts/security_gate.py` | PASS |
| `python scripts/validate_enterprise_alignment.py` | PASS |
| `python scripts/validate_autonomous_installer.py` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 784 exigences, 589 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 57 tests |
| `PYTHONPATH=src:. pytest --collect-only --no-cov -q` | PASS — 446 tests collectés |
| Tests ciblés ITAM domaine/service/API/CLI | PASS — 7 tests |
| Tests unitaires + architecture | PASS |
| Tests d’intégration par lots | PASS — 270 tests |
| `coverage report --fail-under=98` | PASS — 98 % |
| `python scripts/quality_gate.py` | PASS |
| `zip -T openinfra-python-0.29.43.zip` | PASS |
| `python scripts/verify_artifact.py /mnt/data/openinfra-python-0.29.43.zip` | PASS |

## Tests ciblés ITAM exécutés

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_domain_itam_support.py \
  tests/integration/test_itam_support_services.py \
  tests/integration/test_itam_support_http_api.py \
  tests/integration/test_cli.py::test_itam_support_profile_cli_commands \
  tests/integration/test_http_api.py::TestHttpApi::test_health_and_ipam_allocation
```

Résultat : 7 passed.

## Validations non exécutées localement

- `ruff format --check src tests scripts docker` : binaire `ruff` absent.
- `ruff check src tests scripts docker` : binaire `ruff` absent.
- `mypy src/openinfra` : binaire `mypy` absent.
- `bandit -q -r src/openinfra` : binaire `bandit` absent.
- `pip-audit --dry-run` : binaire `pip-audit` absent.
- `python -m build` : module Python `build` absent.
- `npm run build` depuis `web/` : `vite` absent car `web/node_modules` n’est pas installé.
- Docker Compose live : commande `docker` absente.

## Nettoyage artefact

- Caches Python supprimés.
- Caches pytest/mypy/ruff supprimés.
- Fichiers `.coverage*` supprimés après validation couverture.
- `node_modules`, `build`, `dist`, `*.egg-info` exclus/supprimés avant packaging.
