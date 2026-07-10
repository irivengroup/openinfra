# OpenInfra v0.29.82 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.82`  
Périmètre : `P14 / EPIC-1405 — Réconciliation Discovery multisource gouvernée`

## Résultat global

La livraison est validée sur le code source, les contrats applicatifs, les migrations, la documentation contractuelle, le packaging Python et les surfaces opérateur. La suite monolithique avec couverture dépasse la durée maximale du runner ; elle a donc été exécutée par fichiers et lots avec accumulation dans un fichier de couverture unique. Aucun test n’a échoué dans ce découpage.

- Tests Python collectés : **574** dans **79 fichiers**.
- Tests existants : **PASS** par fichiers/lots.
- Tests modifiés ou ajoutés v0.29.82 : **PASS** après consolidation.
- Régression ciblée Discovery/CLI/API/Web/migrations/installateur : **73 tests PASS**.
- Couverture globale exacte : **98,03 %** — `19 805 / 20 203` instructions couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **2 PASS**.

## Contrats CDC et roadmap

- CDC v4.8.1 : **PASS** — **823 exigences**, **622 tests contractuels**.
- Roadmap v2 : **PASS** — **19 phases**, **114 epics**, **8 gates**, **91 tests**.
- Alignement CDC/roadmap/installation Enterprise : **PASS**.
- Migration PostgreSQL la plus récente : `0038_discovery_multisource_reconciliation.sql`.
- Nombre total de migrations PostgreSQL ordonnées : **38**.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, aucune erreur sur 55 fichiers source.
- `bandit -q -r src/openinfra` : **PASS** ; seuls les avertissements informatifs relatifs aux annotations `nosec` SQL existantes sont affichés.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- Scan des secrets, durcissement CI et séparation dépendances runtime/dev : **PASS**.

## Interfaces et exécution

- CLI Discovery : **PASS**.
- API HTTP et OpenAPI Discovery : **PASS**.
- Portail statique et source React : **PASS**.
- Alignement `web/package.json` / version backend : **PASS** (`0.29.82`).
- Contrat frontend Node.js (`npm --prefix web run lint`) : **PASS**.
- Tests frontend Node.js (`npm --prefix web test`) : **PASS**.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Smoke runtime natif et unités systemd rendues : **PASS**.

## Packaging

- `python -m build` : **PASS**.
- Wheel : `openinfra-0.29.82-py3-none-any.whl`.
- Source distribution : `openinfra-0.29.82.tar.gz`.
- `python scripts/verify_artifact.py dist/openinfra-0.29.82-py3-none-any.whl` : **PASS**.
- Installation isolée du wheel avec la dépendance runtime locale `defusedxml` : **PASS**.
- `openinfra version` depuis le wheel : **PASS**, retourne `0.29.82`.
- `openinfra --help` depuis le wheel : **PASS**.

## Contrôles non concluants ou non exécutables localement

- `pip-audit` a été lancé sur la dépendance runtime, mais n’a pas pu interroger PyPI à cause de l’absence de résolution DNS sortante dans le runner. Le gate reste présent en CI.
- Le build Vite local n’a pas été exécuté, car `web/node_modules` n’est pas fourni et le runner ne peut pas télécharger les dépendances npm. Un job GitHub Actions Node.js 22 installe les dépendances, exécute le lint, les tests frontend et le build de production.
- Aucun serveur PostgreSQL live n’est disponible dans le runner ; les migrations sont validées par tests de structure, ordre, contraintes, index, partitionnement et politique SQL.
- Aucun daemon Docker n’est disponible ; le smoke Docker Compose live n’est pas exécuté localement.

## Commandes de reproduction

```bash
ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
python -m pytest
python scripts/security_gate.py --project-root .
python scripts/quality_gate.py
openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py
python scripts/validate_autonomous_installer.py --root installers
python scripts/validate_enterprise_alignment.py --project-root .
python scripts/validate_frontend.py --project-root .
npm --prefix web run lint
npm --prefix web test
npm --prefix web run build
python -m build
python scripts/verify_artifact.py dist/*.whl
```
