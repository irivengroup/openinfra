# OpenInfra v0.29.68 — Validation Report

Release: `0.29.68`

## Scope

Hotfix UX web : remplacement du dépliage brutal du menu latéral par un accordéon hiérarchique animé, sans modification de thème visuel ni de contrat API/CLI.

## Changes validated

- Le clic sur un composant sidebar ouvre uniquement le panneau des contextes.
- Le clic sur un contexte ouvre uniquement ce contexte et ferme les autres contextes du même composant.
- Les opérations restent masquées tant que leur contexte n’est pas explicitement ouvert.
- Le menu mobile extra-small reste ouvert pendant les clics composant/contexte et se ferme uniquement après sélection d’une opération.
- Les transitions n’utilisent pas `max-height`; elles reposent sur `grid-template-rows`, plus stable visuellement.
- Le mode `prefers-reduced-motion` désactive les transitions pour les utilisateurs concernés.

## Executed validations

| Validation | Result |
| --- | --- |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| OpenAPI YAML parse | PASS — `0.29.68` |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.68` |
| `PYTHONPATH=src python -m pytest tests/integration/test_openinfra_web.py -q --no-cov` | PASS — 13 tests |
| `python -m compileall -q src tests scripts` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| Integration tests by file groups with `--no-cov` | PASS — 312 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 515 tests collected |

## Not completed in this runtime

- `ruff`, `mypy`, `bandit`, `pip-audit`, `python -m build` : executables non disponibles localement.
- Full `python -m pytest` avec couverture globale : interrompu par timeout sandbox avant génération d’un rapport complet exploitable.
- `quality_gate.py` : non exécuté car il dépend d’un fichier `.coverage` complet.
- Build Vite complet : dépendances frontend non installées dans ce runtime.
- Docker Compose live : non exécuté dans ce runtime.
