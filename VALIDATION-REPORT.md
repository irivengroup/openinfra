# OpenInfra v0.29.75 — Validation Report

Release: `0.29.75`

## Objet

La version v0.29.75 ajoute le référentiel ITAM des partenaires d’organisation : constructeurs, éditeurs logiciels et supports tiers. L’objectif est de supprimer l’ambiguïté métier des fournisseurs en texte libre dans les garanties, licences et supports, puis de ne permettre que des partenaires accrédités et actifs au niveau de l’organisation.

La livraison ajoute une migration PostgreSQL unique `0032_itam_partner_registry.sql` pour couvrir le référentiel partenaires et le rattachement des licences logicielles à un éditeur accrédité. Les migrations antérieures restent conservées pour compatibilité ascendante.

## Changements validés

- Ajout domaine `ItamPartner`, `ItamPartnerKind`, `ItamPartnerStatus` et `ItamPartnerCatalog`.
- Ajout CRUD partenaires dans les services ITAM.
- Ajout persistance JSON store et PostgreSQL.
- Ajout migration `0032_itam_partner_registry.sql` avec partitionnement, contraintes, index métier et index d’audit.
- Ajout CLI `openinfra itam partner-*` et API `/api/v1/itam/partner*`.
- Ajout contexte web ITAM `Fournisseurs et Supports`.
- Réalignement des formulaires garanties/licences/supports tiers sur des partenaires actifs et compatibles.
- Validation stricte : organisation active obligatoire, téléphone obligatoire, type partenaire compatible obligatoire.
- CDC et roadmap mis à jour avec `REQ-00816`, `TST-WEB-115` et `TST-P14-ITAM-PARTNER-REGISTRY`.

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
| `PYTHONPATH=src python -m openinfra version` | PASS — 0.29.75 |
| `PYTHONPATH=src python -m openinfra spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 816 exigences, 615 tests |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 85 tests |
| `PYTHONPATH=src python -m pytest --collect-only --no-cov` | PASS — 527 tests collectés |
| `PYTHONPATH=src python -m pytest --no-cov -q tests/unit tests/architecture` | PASS — 203 tests |
| `PYTHONPATH=src python -m pytest --no-cov -q <lots integration>` | PASS — 324 tests |
| `PYTHONPATH=src python -m pytest --cov=openinfra --cov-append <lots unit/architecture/integration>` | PASS |
| `python scripts/quality_gate.py` | PASS — couverture globale 98 % |

## Non exécuté localement

- `ruff format --check src tests scripts docker` : exécutable `ruff` absent du runtime.
- `ruff check src tests scripts docker` : exécutable `ruff` absent du runtime.
- `bandit -q -r src/openinfra` : exécutable `bandit` absent du runtime.
- `mypy src/openinfra` : exécutable `mypy` absent du runtime.
- `python -m build` : module `build` absent du runtime.
- `pip-audit -r requirements/security-audit.txt` : non exécuté dans ce runtime.
- Build Vite complet : dépendances frontend non installées localement.
- Docker Compose live : non exécuté dans ce runtime.

## Artefacts attendus

- Archive source : `openinfra-python-0.29.75.zip`
- CDC mis à jour : `openinfra-cdc-sfg-stg-v4.8.1-updated-0.29.75.zip`
- Roadmap mise à jour : `openinfra-roadmap-developpement-v2-updated-0.29.75.zip`
