# OpenInfra v0.29.76 — Validation Report

Release: `0.29.76`

## Objet

La version v0.29.76 réaligne le DCIM sur la gestion complète des sites et dépendances : sites, bâtiments, étages conditionnels, salles avec plages bornées de lignes/colonnes et racks/châssis avec cycle de vie CRUD non destructif. Elle applique aussi les ajustements ITAM demandés : libellé web `Partenaires`, présentation `Filiale/Subdivision` sous `Organisations`, et champs pays rendus en select ISO groupé par continent.

La livraison ajoute une migration PostgreSQL additive `0033_dcim_site_dependencies_rack_lifecycle.sql`. Les migrations antérieures, dont `0032_itam_partner_registry.sql`, restent conservées pour compatibilité ascendante.

## Changements validés

- Règle métier d’étage conditionnel : une salle peut être créée sans étage uniquement si le bâtiment ne possède aucun étage actif ; si le bâtiment possède au moins un étage actif, l’étage devient obligatoire et doit appartenir au bâtiment.
- Extension des salles DCIM avec expansion déterministe des plages de lignes/colonnes (`0-12`, `A-F`) en listes incrémentales bornées et uniques.
- Ajout du cycle de vie rack/châssis : création, consultation, liste, mise à jour et retrait logique.
- Validation stricte du rattachement rack : site, bâtiment, salle et, lorsque applicable, étage cohérents.
- Cascade non destructive des retraits : site → bâtiment → salle → rack.
- Ajout endpoints API DCIM racks et endpoint de référence pays `/api/v1/reference/countries`.
- Ajout commandes CLI `openinfra dcim racks`, `rack`, `rack-update`, `rack-delete` et enrichissement `room-create`/`define-room` avec plages.
- UI web : menu DCIM `Sites & dépendances` enrichi, menu ITAM `Partenaires`, `Filiale/Subdivision` déplacé sous `Organisations`, select pays ISO groupé par continent.
- CDC et roadmap mis à jour avec `REQ-00817`, `TST-WEB-116` et `TST-P14-DCIM-SITE-DEPENDENCIES-RACKS-COUNTRIES`.

## Validations exécutées

| Commande | Statut |
|---|---|
| `python -m compileall -q src tests scripts docker` | PASS |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |
| `python scripts/validate_frontend.py --project-root .` | PASS |
| `python scripts/security_gate.py --project-root .` | PASS |
| `python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `python scripts/native_runtime_smoke.py` | PASS |
| `PYTHONPATH=src python -m openinfra version` | PASS — 0.29.76 |
| `PYTHONPATH=src python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 817 exigences, 616 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 85 tests |
| `PYTHONPATH=src python -m pytest --collect-only -q --no-cov` | PASS — 532 tests collectés |
| `PYTHONPATH=src python -m pytest -q -o addopts='' --cov=src/openinfra --cov-report= --cov-fail-under=0 tests/unit tests/architecture` | PASS — 203 tests |
| `PYTHONPATH=src python -m pytest -q -o addopts='' --cov=src/openinfra --cov-append --cov-report= --cov-fail-under=0 <lots integration>` | PASS — 329 tests |
| `python scripts/quality_gate.py` | PASS — couverture globale 98 % |

## Non exécuté localement

- `ruff format --check src tests scripts docker` : exécutable `ruff` absent du runtime.
- `ruff check src tests scripts docker` : exécutable `ruff` absent du runtime.
- `bandit -q -r src/openinfra` : exécutable `bandit` absent du runtime.
- `mypy src/openinfra` : exécutable `mypy` absent du runtime.
- `python -m build` : module `build` absent du runtime.
- `pip-audit -r requirements/security-audit.txt` : exécutable/module `pip-audit` absent du runtime.
- Build Vite complet : dépendances frontend non installées localement.
- Docker Compose live : non exécuté dans ce runtime.

## Artefacts attendus

- Archive source : `openinfra-python-0.29.76.zip`
- CDC mis à jour : `openinfra-cdc-sfg-stg-v4.8.1-updated-0.29.76.zip`
- Roadmap mise à jour : `openinfra-roadmap-developpement-v2-updated-0.29.76.zip`
