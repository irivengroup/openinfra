# OpenInfra v0.29.84 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.84`  
Périmètre : `Correctif CI DCIM et compatibilité GitHub Actions Node.js 24`

## Résultat global

La livraison corrige le chaînage des smoke tests DCIM après normalisation du code d’étage et supprime les actions GitHub reposant encore sur le runtime Node.js 20. Aucun contrat métier, schéma PostgreSQL, CDC ou jalon de roadmap n’est modifié.

- Tests Python collectés : **611** dans **83 fichiers**.
- Suite complète : **PASS** par lots, sans échec.
- Régression ciblée CLI/workflows/gate sécurité : **15 tests PASS**.
- Smoke extrait du workflow `DCIM physical model` : **PASS**.
- Smoke extrait du workflow `DCIM cabling and energy foundation` : **PASS**.
- Couverture globale exacte : **98,0041 %** — `20 525 / 20 943` instructions couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **2 PASS**.
- Build frontend Vite : **PASS**.

La suite instrumentée a été exécutée par lots avec accumulation dans un fichier de couverture unique. Un lot de quatorze fichiers a dépassé le timeout du runner ; il a été rejoué en deux sous-lots de sept fichiers, tous validés.

## Correction fonctionnelle CI

- `openinfra dcim define-room` retourne un code d’étage canonique de la forme `<site>_<bâtiment>_ETG<n>` : **contrat confirmé**.
- Le smoke modèle physique extrait désormais le champ JSON `floor` et le réutilise pour `dcim locate` : **PASS**.
- Le smoke câblage/énergie applique la même règle à `dcim define-rack` et `dcim locate` : **PASS**.
- Les anciens usages locaux de `F01` sont conservés uniquement dans les scénarios fondés sur les données de démonstration préchargées où ce code existe réellement.
- Test de non-régression du chaînage `define-room` → `locate` : **PASS**.
- Tests structurels des deux blocs de workflow : **PASS**.

## GitHub Actions

- `actions/checkout@v6` : configuré dans tous les workflows.
- `actions/setup-python@v6` : configuré dans les jobs Python.
- `actions/setup-node@v6` : configuré dans le job frontend.
- `actions/dependency-review-action@v5` : conservé.
- `github/codeql-action@v4` : conservé.
- Le gate de sécurité refuse explicitement `actions/checkout@v4`, `actions/setup-python@v5` et `actions/setup-node@v4` : **PASS**.
- Parsing YAML de tous les workflows : **PASS**.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, aucune erreur sur **56 fichiers source**.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python -m compileall -q src/openinfra scripts tests` : **PASS**.
- Scan des secrets et séparation dépendances runtime/dev : **PASS**.

## CDC, roadmap, installateurs et runtime

- CDC v4.8.1 : **PASS** — **823 exigences**, **622 tests contractuels**.
- Roadmap v2 : **PASS** — **19 phases**, **114 epics**, **8 gates**, **91 tests**.
- Aucun fichier CDC ou roadmap modifié ou réémis.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Alignement Enterprise : **PASS**.
- Validation frontend statique : **PASS**.
- Smoke runtime natif et unités systemd : **PASS**.
- Migration PostgreSQL la plus récente : `0039_discovery_job_resilience.sql`.
- Nombre total de migrations PostgreSQL ordonnées : **39**.
- Aucune nouvelle migration pour cette release.

## Frontend

- Installation npm : **PASS**.
- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web test` : **2 tests PASS**.
- `npm --prefix web run build` : **PASS**, Vite a produit les assets de production.
- `web/node_modules`, `web/dist` et le lockfile généré par le miroir local ne sont pas inclus dans l’archive.

## Packaging

- `uv build` : **PASS**.
- Wheel : `openinfra-0.29.84-py3-none-any.whl`.
- Source distribution : `openinfra-0.29.84.tar.gz`.
- `python scripts/verify_artifact.py dist/openinfra-0.29.84-py3-none-any.whl` : **PASS**.
- Présence des **39 migrations** dans le wheel : **PASS**.
- Présence et rendu de `0039_discovery_job_resilience.sql` depuis le wheel installé : **PASS**.
- Installation isolée du wheel avec la dépendance runtime locale `defusedxml` : **PASS**.
- `openinfra version` depuis le wheel : **PASS**, retourne `0.29.84`.
- `openinfra --help` depuis le wheel : **PASS**.

## Contrôles non exécutables localement

- `pip-audit` a été lancé sur `requirements/security-audit.txt`, mais le runner n’a pas pu résoudre `pypi.org` (`Temporary failure in name resolution`). Le gate reste bloquant dans GitHub Actions.
- Aucun serveur PostgreSQL live n’est disponible dans le runner ; les migrations sont validées par tests structurels et par chargement depuis le wheel.
- La commande Docker n’est pas installée dans le runner ; le smoke Docker Compose live n’est pas exécutable localement.

## Commandes de reproduction

```bash
export PYTHONPATH=src:.
ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
python -m pytest
coverage report --fail-under=98
python scripts/security_gate.py --project-root .
python scripts/quality_gate.py
python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py
python scripts/validate_autonomous_installer.py --root installers
python scripts/validate_enterprise_alignment.py --project-root .
python scripts/validate_frontend.py --project-root .
python scripts/native_runtime_smoke.py --project-root .
npm install --prefix web --ignore-scripts --no-audit --no-fund
npm --prefix web run lint
npm --prefix web test
npm --prefix web run build
uv build
python scripts/verify_artifact.py dist/openinfra-0.29.84-py3-none-any.whl
```
