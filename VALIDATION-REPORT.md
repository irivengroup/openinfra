# OpenInfra v0.29.83 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.83`  
Périmètre : `P14 / EPIC-1406 — Résilience des workers et agents Discovery`

## Résultat global

La livraison est validée sur le code source, le domaine, les contrats applicatifs, la concurrence, les migrations, les interfaces opérateur et le packaging Python. La suite monolithique instrumentée dépasse la durée maximale du runner ; les 82 fichiers de tests ont donc été exécutés par lots avec accumulation dans un fichier de couverture unique. Aucun test n’a échoué dans ce découpage.

- Tests Python collectés : **608** dans **82 fichiers**.
- Suite complète : **PASS** par fichiers et lots.
- Régression ciblée EPIC-1406 : **129 tests PASS**.
- Tests architecture : **3 PASS**.
- Couverture globale exacte : **98,0041 %** — `20 525 / 20 943` instructions couvertes.
- Seuil bloquant exact : **98 % PASS**, sans dépendre de l’arrondi d’affichage.
- Tests frontend Node.js : **2 PASS**.

## Contrats CDC et roadmap

- CDC v4.8.1 : **PASS** — **823 exigences**, **622 tests contractuels**.
- Roadmap v2 : **PASS** — **19 phases**, **114 epics**, **8 gates**, **91 tests**.
- Alignement CDC/roadmap/installation Enterprise : **PASS**.
- Les 234 fichiers de `docs/specifications` sont **strictement identiques** à ceux de la v0.29.82.
- Empreinte agrégée SHA-256 inchangée : `0544f06e9d5015f4a61acb2bacdb0dc70ff5e99d0e0f2cf671a950394f7fce3e`.
- Aucun CDC ni roadmap séparé n’est réémis : EPIC-1406 était déjà défini et aucune nouvelle recommandation n’impacte l’existant.
- Migration PostgreSQL la plus récente : `0039_discovery_job_resilience.sql`.
- Nombre total de migrations PostgreSQL ordonnées : **39**.

## Fonctionnalité et non-régression

- Soumission transactionnelle et idempotente par tenant et clé métier : **PASS**.
- Réservation concurrente sans doublon ni perte : **PASS**.
- Baux expirants et reprise après crash : **PASS**.
- Fencing token monotone et rejet des workers obsolètes : **PASS**.
- Renouvellement, completion idempotente et hash SHA-256 : **PASS**.
- Retries bornés, DLQ, rejeu administré et audit : **PASS**.
- Mise en DLQ automatique lors de l’expiration du dernier bail autorisé : **PASS**.
- Contrôle optimiste PostgreSQL et réservation `FOR UPDATE SKIP LOCKED` : **PASS** par tests structurels.
- Compatibilité de la réconciliation multisource v0.29.82 et des corrections DCIM/ITAM : **PASS**.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, aucune erreur sur **56 fichiers source**.
- `bandit -q -r src/openinfra` : **PASS** ; seuls les avertissements informatifs relatifs aux annotations SQL `nosec` existantes sont affichés.
- `python scripts/security_gate.py` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python -m compileall -q src/openinfra` : **PASS**.
- Scan des secrets, durcissement CI et séparation dépendances runtime/dev : **PASS**.

## Interfaces et exécution

- CLI Discovery jobs : **PASS**.
- API HTTP et OpenAPI Discovery jobs : **PASS**.
- Portail statique et source React : **PASS**.
- Alignement `VERSION`, package Python, module Python et `web/package.json` : **PASS** (`0.29.83`).
- Contrat frontend Node.js (`npm --prefix web run lint`) : **PASS**.
- Tests frontend Node.js (`npm --prefix web test`) : **PASS**.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Smoke runtime natif et unités systemd rendues : **PASS**.

## Packaging

- `python -m build` : **PASS**.
- Wheel : `openinfra-0.29.83-py3-none-any.whl`.
- Source distribution : `openinfra-0.29.83.tar.gz`.
- `python scripts/verify_artifact.py dist/openinfra-0.29.83-py3-none-any.whl` : **PASS**.
- Présence des 39 migrations dans le wheel, dont `0039_discovery_job_resilience.sql` : **PASS**.
- Résolution automatique des migrations depuis une installation wheel et un répertoire de travail vide : **PASS**.
- Installation isolée du wheel avec la dépendance runtime locale `defusedxml` : **PASS**.
- `openinfra version` depuis le wheel : **PASS**, retourne `0.29.83`.
- `openinfra --help` depuis le wheel : **PASS**.
- L’archive de livraison exclut les caches, données runtime, rapports temporaires, `build/`, `dist/` et métadonnées `*.egg-info`.

## Contrôles non exécutables localement

- `npm --prefix web run build` a été lancé et s’arrête avec `vite: not found`, car `web/node_modules` n’est pas fourni et le runner ne dispose pas d’accès réseau npm. Le job GitHub Actions Node.js 22 installe les dépendances, exécute le lint, les tests frontend et le build de production.
- Aucun serveur PostgreSQL live n’est disponible dans le runner ; les migrations et opérations concurrentes sont validées par tests de structure, ordre, contraintes, index, partitionnement, SQL atomique et politique de transition.
- La commande `docker` est absente du runner ; le smoke Docker Compose live n’est pas exécutable localement.
- `pip-audit` a été lancé sur `requirements/security-audit.txt`, mais n’a pas pu résoudre `pypi.org` (`Temporary failure in name resolution`). Le gate reste présent en CI.

## Commandes de reproduction

```bash
export PYTHONPATH=src:.
ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
python -m pytest
coverage report --fail-under=98
python scripts/security_gate.py
python scripts/quality_gate.py
openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py
python scripts/validate_autonomous_installer.py --root installers
python scripts/validate_enterprise_alignment.py --project-root .
python scripts/validate_frontend.py --project-root .
python scripts/native_runtime_smoke.py --project-root .
npm --prefix web run lint
npm --prefix web test
npm --prefix web run build
python -m build
python scripts/verify_artifact.py dist/*.whl
```
