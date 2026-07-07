# Rapport de validation OpenInfra v0.29.36

## Objet de livraison

Correction UX ciblée `openinfra-web` : suppression des alertes informatives affichées par défaut sur les pages composant. Le contenu d’aide formulaire reste disponible comme texte indicatif neutre ; les alertes visibles restent réservées aux erreurs/warnings caractérisés et au succès après soumission effective.

## Changements validés

- Version projet : `0.29.36`.
- Runtime statique `openinfra-web.js` : remplacement du bloc `<div class="alert alert-info" role="note">...` par un paragraphe indicatif `text-muted`.
- Source React `web/src/main.jsx` : alignement du texte indicatif sans alerte par défaut.
- Succès de formulaire conservé et conditionné à `result && activeModuleId !== "overview"` côté runtime et `submissionCompleted && activeModuleId !== 'overview'` côté React.
- Validateur frontend renforcé : interdiction de `alert alert-info`, `role="note"` et `className="alert alert-info"` dans les surfaces UI runtime contrôlées.
- Tests d’intégration web renforcés pour verrouiller l’absence d’alerte informative par défaut et la conservation du succès post-soumission.
- CDC : ajout `REQ-00776` et `TST-WEB-079`.
- Roadmap : ajout `TST-P08-WEB-CONTEXTUAL-ALERTS` et alignement `REQ-00776`.

## Validations exécutées dans cet environnement

| Validation | Résultat |
|---|---:|
| `python -m compileall -q src tests scripts docker` | PASS |
| `PYTHONPATH=src python scripts/validate_frontend.py --project-root .` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — `0.29.36` |
| `PYTHONPATH=src python scripts/security_gate.py` | PASS |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --json` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers --json` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py` | PASS |
| Validation CDC via `ContractualSpecValidator` | PASS — 776 exigences, 581 tests |
| `PYTHONPATH=src:. pytest --collect-only -q --no-cov` | PASS — 436 tests collectés |
| `PYTHONPATH=src:. pytest -q --no-cov tests/integration/test_openinfra_web.py` | PASS — 12 tests |
| `PYTHONPATH=src:. pytest -q --no-cov tests/integration/test_runtime_docker_environment.py` | PASS — 5 tests |
| Tests version/discovery/API/proxy ciblés | PASS — 62 tests |
| Suite complète en lots `pytest -q --no-cov` | PASS — 436 tests exécutés en lots |

## Validations non exécutées jusqu’au bout dans cet environnement

| Validation | Statut |
|---|---|
| `ruff format --check src tests scripts docker` | Non exécutable : binaire/module `ruff` absent. |
| `ruff check src tests scripts docker` | Non exécutable : binaire/module `ruff` absent. |
| `mypy src/openinfra` | Non exécutable : module `mypy` absent. |
| `bandit -q -r src/openinfra` | Non exécutable : module `bandit` absent. |
| `pip-audit --dry-run` | Non exécutable : module `pip_audit` absent. |
| `python -m build` | Non exécutable : module `build` absent. |
| `npm run build` | Échec environnement : `vite` absent car `web/node_modules` non installé. |
| Docker Compose live | Non exécutable : commande `docker` absente. |
| Couverture `--fail-under=98` | Non finalisée : les tentatives de couverture complète ont dépassé le temps d’exécution disponible ; la suite fonctionnelle complète a toutefois passé en lots sans couverture. |

## Risques résiduels

- Le build Vite et les gates Python outillés doivent être relancés dans la CI ou un poste disposant des dépendances de développement (`ruff`, `mypy`, `bandit`, `pip-audit`, `build`, `vite`).
- La couverture globale 98 % doit être confirmée par CI ; la modification fonctionnelle est couverte par les tests web ciblés et par le validateur frontend.
