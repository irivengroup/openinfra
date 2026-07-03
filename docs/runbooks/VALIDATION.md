# Runbook de validation

## Validation locale minimale

```bash
PYTHONPATH=src python -m pytest
PYTHONPATH=src python -m compileall -q src tests scripts docker
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0001_bootstrap --root migrations/postgresql >/tmp/openinfra-0001.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0002_security_rbac --root migrations/postgresql >/tmp/openinfra-0002.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0003_security_token_lifecycle --root migrations/postgresql >/tmp/openinfra-0003.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0004_identity_users_groups --root migrations/postgresql >/tmp/openinfra-0004.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0005_access_policy_abac --root migrations/postgresql >/tmp/openinfra-0005.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0006_audit_trail_integrity --root migrations/postgresql >/tmp/openinfra-0006.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0007_source_of_truth_core --root migrations/postgresql >/tmp/openinfra-0007.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0008_source_governance --root migrations/postgresql >/tmp/openinfra-0008.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0009_dcim_physical_model --root migrations/postgresql >/tmp/openinfra-0009.sql
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate --data /tmp/openinfra-state.json --tenant default --vrf default --prefix 10.99.0.0/30 --hostname validation --idempotency-key validation-1
```

## Validation PostgreSQL avec DSN réel

```bash
export OPENINFRA_DATABASE_DSN='postgresql://openinfra:secret@postgres:5432/openinfra'
PYTHONPATH=src python -m openinfra.interfaces.cli database status --root migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations --root migrations/postgresql --dry-run
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations --root migrations/postgresql
```

## Validation complète CI

```bash
python -m pip install -e '.[dev]'
ruff format --check src tests scripts docker
ruff check src tests scripts docker
mypy src/openinfra
python -m pytest
PYTHONPATH=src python -m compileall -q src tests scripts docker
bandit -q -r src/openinfra
python -m build
python scripts/verify_artifact.py dist/*.whl
python scripts/quality_gate.py
```

## Validation de l’environnement d’exécution Docker

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```

Cette validation démarre PostgreSQL, applique les migrations avec `openinfra database apply-migrations`, lance l’API avec backend PostgreSQL et exécute les smoke tests API/CLI. Elle nécessite Docker Compose disponible sur le poste ou le runner CI.

## Critères bloquants

- Couverture globale inférieure à 90 %.
- Migration absente ou non partitionnée.
- Historique de migrations PostgreSQL absent dans un environnement runtime.
- Checksum divergent sur une migration déjà appliquée.
- Fichier source contractuel v4 absent.
- Commande CLI documentée mais non testée.
- Fonction publique module-level dans `src/openinfra`, car le code produit doit rester orienté objet.
- Environnement Docker incomplet ou incapable d’orchestrer PostgreSQL, migration, API et smoke tests.

## Validations sécurité v0.7.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token \
  --data /tmp/openinfra-security.json \
  --tenant default \
  --subject validation-client \
  --role ipam:operator \
  --token "$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
PYTHONPATH=src python -m pytest tests/unit/test_security_domain.py tests/integration/test_http_api.py
```

La CI exécute aussi le runtime Docker authentifié via `python scripts/docker_environment.py validate`, incluant inventaire et révocation de jeton temporaire.

## Validation IAM v0.7.0

Les tests automatisés couvrent la création d’utilisateurs, la création de groupes, les appartenances, les rôles directs, les rôles hérités, l’agrégation avec les rôles du jeton, les commandes CLI, les endpoints API et l’adaptateur PostgreSQL simulé.

Commandes dédiées :

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0004_identity_users_groups --root migrations/postgresql
PYTHONPATH=src python3 -m pytest -q tests/unit/test_identity_domain.py tests/integration/test_identity_services.py
```

## Validation ABAC v0.8.0

Commandes minimales :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0005_access_policy_abac --root migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli access create-rule --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --name worker-par1-prod --permission ipam.allocate --effect allow --subject worker-client --site-code PAR1 --environment prod
PYTHONPATH=src python -m openinfra.interfaces.cli access evaluate --data /tmp/openinfra.json --tenant default --token "$WORKER_TOKEN" --permission ipam.allocate --site-code PAR1 --environment prod
PYTHONPATH=src python -m pytest -q tests/unit/test_access_policy_domain.py tests/integration/test_access_policy_services.py
```

La CI exécute également un smoke test JSON ABAC et le runtime Docker couvre le scénario PostgreSQL/API/CLI.


## Validation Audit Trail v0.9.0

Commandes minimales :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0006_audit_trail_integrity --root migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli audit list --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --limit 100
PYTHONPATH=src python -m openinfra.interfaces.cli audit export --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --format jsonl --limit 500
PYTHONPATH=src python -m openinfra.interfaces.cli audit verify-integrity --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN"
PYTHONPATH=src python -m pytest -q tests/unit/test_audit_domain.py tests/integration/test_audit_trail_services.py
```

La CI exécute également un smoke test JSON audit et le runtime Docker valide `/api/v1/audit/events`, `/api/v1/audit/export` et `/api/v1/audit/integrity` en backend PostgreSQL.

## Contrôles ajoutés en v0.10.0

- Tests unitaires du domaine Source of Truth : clés sûres, tags, source, relation, snapshots et erreurs contrôlées.
- Tests d'intégration JSON : objet, mise à jour versionnée, relation, liste paginée, restitution de version et erreurs d'autorisation.
- Tests CLI : `openinfra sot upsert-object`, `list-objects`, `get-object-version`, `create-relation`, `list-relations`.
- Tests API HTTP : `/api/v1/sot/objects`, `/api/v1/sot/object-versions`, `/api/v1/sot/relations`.
- Tests adaptateur PostgreSQL simulé : insert/update objet, snapshot, relation et requêtes paginées.

## Contrôles ajoutés en v0.11.0

- Tests unitaires du domaine Source Governance : validation des chemins, wildcard, priorité, fraîcheur et détection de modifications imbriquées.
- Tests d'intégration JSON : création de règle, inventaire, évaluation, désactivation et enforcement dans `SourceOfTruthService`.
- Tests CLI : `openinfra sot create-governance-rule`, `list-governance-rules`, `evaluate-governance`, `deactivate-governance-rule`.
- Tests API HTTP : `/api/v1/sot/governance-rules`, `/api/v1/sot/governance/evaluate`, `/api/v1/sot/governance/deactivate-rule`.
- Tests adaptateur PostgreSQL simulé : persistance, lecture paginée et évaluation via `PostgreSQLSourceGovernanceRepository`.
- Smoke runtime Docker : scénario gouvernance SOT contre API authentifiée et backend PostgreSQL.


## Contrôles ajoutés en v0.12.0

- Tests unitaires du domaine DCIM physique : région de site, étage, zone et invariants de grille.
- Tests d’intégration JSON : définition idempotente de salle, zone incluse dans grille, localisation avec étage/zone/coordonnées et rejets métier.
- Tests CLI : `openinfra dcim define-room` puis `openinfra dcim locate --floor --zone`.
- Tests API HTTP : `POST /api/v1/dcim/rooms` protégé par `dcim.write` lorsque l’API authentifiée est activée.
- Tests adaptateur PostgreSQL simulé : persistance des nouveaux champs DCIM et rendu de `0009_dcim_physical_model.sql`.
- Smoke runtime Docker : création de salle DCIM physique et localisation équipement contre PostgreSQL.
