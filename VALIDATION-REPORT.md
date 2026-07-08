# OpenInfra v0.29.69 — Validation Report

Release: `0.29.69`

## Scope

Incrément UX web : sidebar fermée par défaut avec Dashboard actif, activation visuelle composant/contexte, différenciation colorimétrique des contextes et animation d’accordéon plus douce, sans modification de contrat API/CLI.

## Changes validated

- Au chargement initial, Dashboard est actif et tous les composants métier de la sidebar sont fermés.
- Le clic sur un composant active visuellement ce composant et ouvre uniquement la liste de ses contextes.
- Le clic sur un contexte active visuellement le composant parent et ouvre uniquement le contexte concerné.
- Les contextes disposent d’une couleur dédiée, distincte des actions, incluant hover/focus/active.
- Les opérations restent masquées tant que leur contexte n’est pas explicitement ouvert.
- Le menu mobile extra-small reste ouvert pendant les clics composant/contexte et se ferme uniquement après sélection d’une opération.
- Les transitions n’utilisent pas `max-height`; elles reposent sur `grid-template-rows` avec un easing plus doux.
- Le mode `prefers-reduced-motion` désactive les transitions pour les utilisateurs concernés.

## Executed validations

| Validation | Result |
| --- | --- |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| OpenAPI YAML parse | PASS — `0.29.69` |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.69` |
| `PYTHONPATH=src python -m pytest tests/integration/test_openinfra_web.py -q --no-cov` | PASS — 13 tests |
| `python -m compileall -q src tests scripts` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| Integration tests by file groups with `--no-cov` | PASS — 312 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 515 tests collected |
| Coverage par lots avec `--cov-append --cov-fail-under=0` | PASS — 515 tests exécutés |
| `python scripts/quality_gate.py` | PASS — couverture globale 98 % |

## Not completed in this runtime

- `ruff`, `mypy`, `bandit`, `pip-audit`, `python -m build` : executables non disponibles localement.
- Full `python -m pytest` en une seule commande avec couverture : interrompu par timeout sandbox ; remplacement validé par exécution équivalente en lots `--cov-append` puis `quality_gate.py`.
- Build Vite complet : dépendances frontend non installées dans ce runtime.
- Docker Compose live : non exécuté dans ce runtime.
