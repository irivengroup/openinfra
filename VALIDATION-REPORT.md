# OpenInfra v0.29.64 — Rapport de validation

## Synthèse

Livraison v0.29.64 validée sur base v0.29.62 PostgreSQL hotfix.

Incrément livré : plan de bootstrap Enterprise `openinfra-agent.service` pour préparer les agents de discovery Enterprise sans installation automatique, sans secret en clair et sans écriture RSOT.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| Ruff format `src tests scripts docker` | PASS — 134 fichiers conformes |
| Ruff check `src tests scripts docker` | PASS |
| `compileall` | PASS |
| `scripts/validate_frontend.py` | PASS |
| `node --check openinfra-web.js` | PASS |
| CLI version | PASS — 0.29.64 |
| OpenAPI YAML | PASS |
| `security_gate.py` | PASS |
| `validate_enterprise_alignment.py` | PASS |
| `validate_autonomous_installer.py` | PASS — 6 profils |
| `native_runtime_smoke.py` | PASS |
| CDC validation | PASS — 807 exigences, 529 entités |
| Roadmap validation | PASS — 19 phases, 114 epics, 8 gates, 79 tests |
| `pytest --collect-only` | PASS — 510 tests collectés |
| Tests ciblés agent bootstrap/API/CLI/web | PASS — 22 tests |
| Tests unitaires + architecture | PASS — 202 tests |
| Tests intégration par lots | PASS — 308 tests |
| Couverture agrégée par lots | PASS — 98 % |
| `quality_gate.py` | PASS |
| `zip -T` | PASS |
| `verify_artifact.py` | PASS |
| Nettoyage archive | PASS |

## Contrôles non exécutés localement

Les contrôles suivants n'ont pas pu être exécutés faute de module ou runtime disponible dans l'environnement local :

- `mypy` — module absent ;
- `bandit` — module absent ;
- `pip-audit` — module absent ;
- `python -m build` — module `build` absent ;
- build Vite complet — binaire `vite` absent ;
- Docker Compose live — binaire `docker` absent.

## Note d'exécution

La tentative monolithique de la suite de tests avec couverture a dépassé la limite locale. La validation complète a donc été rejouée par lots déterministes avec couverture agrégée et seuil 98 % respecté.
