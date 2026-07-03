## v0.17.6 — Correctif CI Python 3.13 jetons sûrs

- Exigence : la matrice CI Python 3.13/3.14 ne doit pas échouer aléatoirement lors des smoke tests sécurité.
- Correction : tous les jetons CI générés via `secrets.token_urlsafe(48)` sont préfixés par `ci_`.
- Correction domaine/application : les nouveaux jetons API générés par `TokenGenerator` sont préfixés par `oi_`.
- Contrôle : `scripts/security_gate.py` rejette la génération CI non préfixée `print(secrets.token_urlsafe(48))`.
- Non-régression : tests unitaires et intégration sécurité ajoutés.

## v0.17.5 — Correctif CI Dependency Review séparée

- Exigence : aucun job PR-only ne doit apparaître `Skipped` dans une exécution de push.
- Implémentation : `.github/workflows/dependency-review.yml` séparé, déclenché uniquement par `pull_request`; `.github/workflows/ci.yml` conserve les contrôles bloquants push.
- Garde-fou : `scripts/security_gate.py` refuse `actions/dependency-review-action` et les conditions `if: github.event_name == 'pull_request'` dans le workflow de push.
- Tests : `tests/integration/test_security_gate.py` couvre la séparation push / PR et le rejet d'une régression.

## v0.17.4 — Correctif CI audit vulnérabilités editable

- Exigence qualité : la CI doit auditer les dépendances tierces sans échouer sur le package projet installé en editable.
- Implémentation : `requirements/security-audit.txt`, workflow GitHub Actions mis à jour, garde-fou `security_gate.py`.
- Tests : `tests/integration/test_security_gate.py` vérifie que le workflow utilise l'entrée d'audit dédiée et rejette le retour à l'audit d'environnement editable.

# Traçabilité initiale code ↔ exigences source

| Exigence source | Implémentation livrée | Preuve |
|---|---|---|
| PostgreSQL Cluster socle principal | Migration `migrations/postgresql/0001_bootstrap.sql` partitionnée/indexée | `test_postgresql_migration.py`, `openinfra database render-migration` |
| Pas d'ITSM intégré | Aucun module ITSM ; validation ADR source | `ContractualSpecValidator`, `openinfra spec validate` |
| Plans 2D salle et rack elevation | `RoomPlan2D`, `RackElevation`, `DcimVisualizationService` | `test_dcim_visualization_services.py`, `openinfra dcim room-plan`, `openinfra dcim rack-elevation`, OpenAPI DCIM |
| Énergie et refroidissement DCIM | `PowerDevice`, `PowerCircuit`, `CoolingZone`, `RackPowerReservation`, `DcimEnvironmentService` | `test_dcim_energy_cooling_services.py`, `openinfra dcim energy-cooling-capacity`, OpenAPI DCIM, migration `0014_dcim_energy_cooling_foundation` |
| Câblage DCIM fondation | `PatchPanel`, `DcimPort`, `DcimCable`, `DcimCablingService` | `test_dcim_cabling_services.py`, `openinfra dcim connect-cable`, OpenAPI DCIM, migration `0013_dcim_cabling_foundation` |
| Localisation physique ligne/colonne | `Room`, `Rack`, `EquipmentLocation`, `DcimLocationService` | `test_domain_dcim.py`, `test_services.py`, `openinfra dcim locate` |
| Allocation IP transactionnelle et idempotente | `IpamAllocationService`, `JsonUnitOfWork`, `IpAllocationPolicy` | `test_domain_ipam.py`, `test_services.py`, `openinfra ipam allocate` |
| Audit des opérations critiques | `AuditEvent`, `JsonAuditRepository` | tests d'intégration services et roundtrip audit |
| Architecture hexagonale / POO | packages `domain`, `application`, `infrastructure`, `interfaces` | `test_architecture.py`, `scripts/quality_gate.py` |
| CLI/API/documentation/CI alignées | CLI, API HTTP, OpenAPI, docs, GitHub Actions | `test_cli.py`, `test_http_api.py`, `.github/workflows/ci.yml` |
| Runtime serveur natif production | `deploy/systemd/openinfra-api.service`, `RUNTIME_NATIVE.md`, `native_runtime_smoke.py` | `test_runtime_docker_environment.py`, `scripts/quality_gate.py`, CI native runtime smoke |

## v0.17.3 — Correctif CI audit vulnérabilités et runtime PostgreSQL

- Exigence : la CI sécurité doit auditer les dépendances sans échouer sur le package local non publié `openinfra`.
- Implémentation : `pip-audit` est exécuté avec `requirements/security-audit.txt` dans le job `blocking-security`.
- Garde-fou : `scripts/security_gate.py` rejette un workflow qui conserve `pip_audit` sans l'entrée `requirements/security-audit.txt`.
- Exigence : les erreurs PostgreSQL runtime doivent rester dans le contrat d'erreur OpenInfra.
- Implémentation : `PostgreSQLDriver.connect()` transforme les erreurs de connexion `psycopg` en `OpenInfraError`.
- Roadmap : aucun nouveau jalon métier ; P04 / EPIC-0406 reste inchangé.

## v0.17.2 — Correctif CI sécurité bloquante

- Exigence : la CI doit bloquer les régressions sécurité sur `push` et pull request.
- Implémentation : job `blocking-security`, CodeQL, Dependency Review, Dependabot, `pip-audit`, `bandit` et `scripts/security_gate.py`.
- Compatibilité Python : matrice CI `3.11`, `3.12`, `3.13`, `3.14`.
- Correction RBAC : `security list-tokens` et `security revoke-token` utilisent un jeton `security:admin` dans le smoke CI.
- Roadmap : aucun nouveau jalon métier ; P04 / EPIC-0406 reste inchangé.
