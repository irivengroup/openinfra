# OpenInfra Python v0.11.0 - Rapport de validation

## Périmètre

Version livrée : 0.11.0

Jalon roadmap : REL-01 / P03 Source of Truth - EPIC-0306 Gouvernance minimale des sources.

Objectif : empêcher les sources non autoritatives d'écraser silencieusement les attributs certifiés du Source of Truth, tout en conservant la compatibilité des objets, relations, versions, audit, IAM, RBAC, ABAC, IPAM et runtime Docker existants.

## Changements validés

- Domaine `SourceGovernanceRule`, `SourceGovernanceEvaluation` et `SourceGovernanceEvaluator`.
- Service applicatif `SourceGovernanceService`.
- Enforcement de gouvernance dans `SourceOfTruthService` avant versionnement.
- Rôle `sot:governance-admin` et permissions `sot.governance.read` / `sot.governance.write`.
- Référentiels `JsonSourceGovernanceRepository` et `PostgreSQLSourceGovernanceRepository`.
- Migration PostgreSQL additive `0008_source_governance.sql`.
- CLI `openinfra sot create-governance-rule`, `list-governance-rules`, `evaluate-governance`, `deactivate-governance-rule`.
- API `/api/v1/sot/governance-rules`, `/api/v1/sot/governance/evaluate`, `/api/v1/sot/governance/deactivate-rule`.
- Runtime Docker smoke étendu au scénario gouvernance SOT.
- Documentation, OpenAPI, CI et runbooks mis à jour.

## Validations exécutées localement

```text
PYTHONPATH=src python3 -m pytest -q
Résultat : 112 tests passants
Couverture totale : 90.02 %
Seuil configuré : 90 %
```

```text
PYTHONPATH=src python3 scripts/quality_gate.py
Résultat : PASS
```

```text
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
Résultat : PASS
```

```text
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
Résultat : 0.11.0
```

```text
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
Résultat : status=valid, version=4.0.0, requirements=488, tests=310
```

```text
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0001_bootstrap --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0002_security_rbac --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0003_security_token_lifecycle --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0004_identity_users_groups --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0005_access_policy_abac --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0006_audit_trail_integrity --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0007_source_of_truth_core --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0008_source_governance --root migrations/postgresql
Résultat : PASS
```

```text
Smoke CLI gouvernance : bootstrap-token, create-governance-rule, list-governance-rules, evaluate-governance, deactivate-governance-rule
Résultat : PASS
```

```text
Validation YAML : compose.yaml, .github/workflows/ci.yml, docs/api/openapi.yaml
Résultat : PASS
```

```text
python3 scripts/docker_environment.py init
Résultat : PASS, .env généré avec permissions restrictives puis supprimé avant archive
```

## Validations non exécutées localement

Ces contrôles sont configurés dans la CI GitHub Actions, mais les outils ou services ne sont pas disponibles dans l'environnement courant :

- `ruff format --check src tests scripts docker`
- `ruff check src tests scripts docker`
- `mypy src/openinfra`
- `bandit -q -r src/openinfra`
- `python -m build`
- `python scripts/verify_artifact.py dist/*.whl`
- Runtime Docker Compose réel avec PostgreSQL réel
- Validation PostgreSQL hors Docker contre un cluster externe

## Nettoyage avant archive

- Suppression de `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`, `build`, `dist`, `*.egg-info`.
- Suppression de `.coverage`.
- Suppression du `.env` local généré.
- Vérification de l'archive ZIP après création.
