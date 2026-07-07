# Rapport de validation — OpenInfra v0.29.41

Date : 2026-07-07

## Objet de la livraison

Livraison validée pour l'incrément v0.29.41 : correction UX ciblée de l’icône ITRM. Le pictogramme `reference` reste sémantiquement orienté référentiel/référence, mais il utilise désormais une variante SVG pleine et opaque, homogène avec les autres icônes de composants du header, du menu latéral et des cartes Dashboard.

## Changements validés

- Remplacement du chemin SVG outline de l’icône `reference` par un pictogramme plein/opaque de référentiel.
- Alignement des sources React et des assets runtime servis par `openinfra-web`.
- Ajout d’une validation frontend interdisant le retour de l’ancienne variante outline.
- Extension du test d’intégration web pour vérifier la présence du chemin SVG plein dans React/runtime et l’absence de l’ancien chemin outline.
- Mise à jour README, CHANGELOG, documentation UI, architecture, CDC et roadmap.

## Validations exécutées

| Validation | Résultat |
| --- | --- |
| `python -m compileall -q src scripts tests` | PASS |
| `python scripts/validate_frontend.py` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — 0.29.41 |
| `PYTHONPATH=src python scripts/security_gate.py` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_docs.py docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 783 exigences, 519 entités |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py docs/specifications/OpenInfra-Roadmap-Developpement-v2` | PASS — 19 phases, 114 epics, 8 gates, 56 tests |
| `PYTHONPATH=src:. pytest --collect-only --no-cov -q` | PASS — 440 tests collectés |
| `PYTHONPATH=src:. pytest --no-cov -q tests/unit tests/architecture` | PASS — 174 tests |
| `PYTHONPATH=src:. pytest --no-cov -q tests/integration/...` en lots | PASS — 266 tests |
| `coverage report --fail-under=98` | PASS — 98 % |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |
| `zip -T openinfra-python-0.29.41.zip` | PASS |
| `PYTHONPATH=src:. python scripts/verify_artifact.py /mnt/data/openinfra-python-0.29.41.zip` | PASS |

## Validations non exécutées localement

| Validation | Motif |
| --- | --- |
| `ruff format --check src tests scripts docker` | binaire `ruff` absent de l’environnement |
| `ruff check src tests scripts docker` | binaire `ruff` absent de l’environnement |
| `mypy src/openinfra` | binaire `mypy` absent de l’environnement |
| `bandit -q -r src/openinfra` | binaire `bandit` absent de l’environnement |
| `pip-audit --dry-run` | binaire `pip-audit` absent de l’environnement |
| `python -m build` | module `build` absent de l’environnement |
| `npm run build` | `web/node_modules` / `vite` absents |
| Docker Compose live | commande `docker` absente |

## Notes

La commande complète `pytest --no-cov` en un seul processus a dépassé la limite d’exécution de l’environnement après une partie de la suite. La même suite a été exécutée avec succès en lots déterministes : 174 tests unitaires/architecture et 266 tests d’intégration, soit 440 tests exécutés.
