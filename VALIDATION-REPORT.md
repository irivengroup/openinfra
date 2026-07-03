# OpenInfra Python POO v0.19.0 — Rapport de validation

Date : 2026-07-03

## Synthèse

- Version livrée : OpenInfra Python POO v0.19.0
- Roadmap : P05 / EPIC-0502 — Allocation IP transactionnelle
- Seuil couverture global obligatoire : >= 98 %
- Runtime production : serveur natif Linux + Python virtualenv + systemd + PostgreSQL, sans dépendance Docker
- Docker : lab/smoke facultatif uniquement

## Périmètre livré

La version v0.19.0 durcit l’allocation IP transactionnelle introduite dans le socle IPAM. L’allocation `next available` tient compte du tenant, du VRF, du préfixe, des plages d’allocation, des plages de réservation/exclusion et des adresses déjà enregistrées. Elle reste idempotente par clé métier et produit un événement d’audit structuré lors d’une création effective.

## Changements techniques

- Domaine IPAM : enrichissement de `IpRange` avec bornes entières et test d’appartenance ; sélection déterministe dans `IpAllocationPolicy`.
- Application : `IpamAllocationService` acquiert un verrou logique, charge réservations/adresses/ranges et évite les collisions.
- Port : ajout de `IpamRepository.acquire_allocation_lock`.
- Backend JSON : verrou transactionnel existant conservé et validé par 100 allocations concurrentes.
- Backend PostgreSQL : `pg_advisory_xact_lock` par `tenant/VRF/prefixe`, contraintes uniques conservées.
- Migration PostgreSQL : `0016_ipam_transactional_allocation.sql`.
- CLI/API : `openinfra ipam allocate` et `POST /api/v1/ipam/allocate` restent compatibles, mais avec comportement transactionnel durci.
- CI : rendu migration `0016` et smoke IPAM transactionnel.

## Validations

| Contrôle | Résultat |
| --- | --- |
| `python3 -m ruff format --check src tests scripts docker` | Réussi |
| `python3 -m ruff check src tests scripts docker` | Réussi |
| `python3 -m mypy src/openinfra` | Réussi |
| `python3 -m bandit -q -r src/openinfra` | Réussi |
| `PYTHONPATH=src python3 scripts/security_gate.py --project-root .` | Réussi |
| `PYTHONPATH=src python3 -m pytest -q` | Réussi |
| Couverture globale | 98.09 % |
| Seuil obligatoire | >= 98 % |
| `PYTHONPATH=src python3 scripts/quality_gate.py` | Réussi |
| `PYTHONPATH=src python3 -m compileall -q src tests scripts docker` | Réussi |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli version` | 0.19.0 |
| Validation CDC/SFG/STG | Réussi |
| Rendu migrations PostgreSQL 0001 à 0016 | Réussi |
| Rendu migration `0016_ipam_transactional_allocation` | Réussi |
| Smoke CLI IPAM transactionnel JSON | Réussi |
| Smoke runtime natif | Réussi |
| Build wheel et vérification artefact | Réussi |
| Archive nettoyée | Réussi |

## Tests métier ajoutés

- Allocation respectant plages `allocation`, `exclusion` et adresses déjà enregistrées.
- Plages `reservation` considérées comme capacité bloquée par le moteur d’allocation.
- 100 allocations concurrentes sans collision sur backend JSON.
- Verrou PostgreSQL simulé via `pg_advisory_xact_lock` dans le flux d’allocation.
- Non-régression idempotence existante.

## Non exécuté localement

- Matrice GitHub complète Python `3.11`, `3.12`, `3.13`, `3.14` : seul Python `3.13.5` était disponible localement.
- CodeQL et Dependency Review : exécutables uniquement côté GitHub Actions.
- Audit `pip-audit` réseau complet : dépend de l’accès à PyPI côté CI.
- Docker Compose réel : non exécuté, Docker n’est pas requis en production.
- PostgreSQL réel : non exécuté, aucun serveur PostgreSQL local disponible.
