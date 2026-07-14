# Runbook de validation

## Validation du socle haute performance — v0.30.0

```bash
PYTHONPATH=src:. python -m pytest -q --no-cov \
  tests/integration/test_asgi_performance_runtime.py \
  tests/performance/test_high_performance_runtime_benchmark.py

mkdir -p build/reports
PYTHONPATH=src:. python scripts/benchmark_high_performance_runtime.py \
  --requests 500 --concurrency 50 --warmups 25 \
  --output build/reports/high-performance-runtime.json --enforce

python -m ruff format --check src tests scripts installers docker
python -m ruff check src tests scripts installers docker
python -m mypy src/openinfra
python -m compileall -q src tests scripts installers docker
python scripts/security_gate.py
python scripts/quality_gate.py
python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/scripts/validate_docs.py
python docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/scripts/validate_roadmap.py
python scripts/validate_enterprise_alignment.py --project-root .
```

Contrôles bloquants : ASGI par défaut en Pro/Entreprise, concurrence et workers bornés, budget global PostgreSQL, restitution des connexions, client HTTP persistant, streaming sans buffering intégral, restauration de l’environnement, rollback legacy explicite et seuils p95/p99 du transport. Le rapport doit contenir `scope=asgi-transport-regression` et `capacity_certification=false`.

La certification de capacité exige séparément le gate P20 avec PostgreSQL/PgBouncer réels, paliers, endurance, spike, saturation, chaos et contrôle des fuites. Le benchmark P19 ne doit jamais être utilisé comme preuve de dimensionnement.

## Validation performance de chargement web — v0.29.105

```bash
PYTHONPATH=src:. python -m pytest -q --no-cov \
  tests/integration/test_openinfra_web.py \
  tests/integration/test_frontend_runtime_startup.py

npm --prefix web test
npm --prefix web run lint
npm --prefix web run a11y
npm --prefix web run a11y:jsx
npm --prefix web run build
PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .
```

Contrôles bloquants : bootstrap local agrégé, sonde backend non bloquante, absence de chargement initial des catalogues métier, déduplication des chargements à la demande, compression gzip, ETag distinct par représentation, réponse `304`, cache immutable des assets versionnés, transfert initial inférieur à 125 Ko gzip et maintien de l’accessibilité WCAG 2.2 AA.

## Validation Discovery régionale Enterprise — v0.29.103

```bash
PYTHONPATH=src:. python -m pytest -q --no-cov \
  tests/unit/test_multisite_domain.py \
  tests/integration/test_enterprise_multisite_discovery_routing.py \
  tests/integration/test_enterprise_multisite_http_api.py \
  tests/integration/test_multisite_cli.py \
  tests/integration/test_multisite_migration.py \
  tests/integration/test_multisite_postgresql_repository.py \
  tests/integration/test_multisite_web_contract.py

PYTHONPATH=src:. python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
```

Contrôles bloquants : disponibilité Enterprise uniquement, site DCIM existant, proxy actif, endpoint HTTPS, portée région/site/VRF exacte, idempotence des jobs, audit, isolation tenant, migration non destructive et absence d’écriture RSOT directe.

## Validation multisite Pro centralisé — v0.29.102

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/unit/test_multisite_domain.py \
  tests/integration/test_multisite_services.py \
  tests/integration/test_multisite_cli.py \
  tests/integration/test_multisite_http_api.py \
  tests/integration/test_multisite_migration.py \
  tests/integration/test_multisite_postgresql_repository.py \
  tests/integration/test_multisite_web_contract.py
python scripts/validate_openapi.py docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
```

Contrôles bloquants : portée locale obligatoire hors `multisite.admin`, rejet atomique des sites non autorisés, disponibilité Pro/Enterprise uniquement, audit des mutations, migration non destructive et absence d’agent régional Pro.

## Validation RAG gouverné — v0.29.101

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_rag_domain.py \
  tests/unit/test_rag_edge_cases.py \
  tests/unit/test_rag_infrastructure.py \
  tests/integration/test_rag_services.py \
  tests/integration/test_rag_edge_coverage.py \
  tests/integration/test_rag_cli.py \
  tests/integration/test_rag_http_api.py \
  tests/integration/test_rag_migration.py \
  tests/integration/test_rag_postgresql_repository.py \
  tests/integration/test_rag_web_contract.py

PYTHONPATH=src:. python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml

cd web && npm test && npm run lint && npm run a11y && npm run a11y:jsx && npm run build
```

Ces contrôles garantissent le filtrage tenant/permissions avant recherche, les citations obligatoires, l'audit sans question en clair, la synchronisation RSOT en lecture seule, les jobs d'import/export relançables, les 13 routes RAG, la migration `0049` et l'absence d'action destructive ou de service de génération externe.

## Validation correctif écran blanc — v0.29.100

```bash
PYTHONPATH=src:. pytest --no-cov -q \
  tests/integration/test_frontend_runtime_startup.py \
  tests/integration/test_sbom_web_contract.py \
  tests/integration/test_openinfra_web.py

python scripts/validate_frontend.py --project-root .
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
cd web && npm test && npm run lint && npm run a11y && npm run a11y:jsx && npm run build
```

Ces contrôles garantissent que toutes les références `FIELD_SETS.*` du portail statique sont déclarées, que le catalogue d’opérations ne contient aucune entrée nulle ou indéfinie, que le Dashboard est rendu avant les appels backend, que les assets non versionnés sont revalidés par le navigateur et qu’une erreur de démarrage est affichée de manière accessible au lieu de laisser un écran blanc.

## Validation SBOM — v0.29.99

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_sbom_domain.py \
  tests/unit/test_sbom_edge_cases.py \
  tests/integration/test_sbom_services.py \
  tests/integration/test_sbom_cli.py \
  tests/integration/test_sbom_http_api.py \
  tests/integration/test_sbom_migration.py \
  tests/integration/test_sbom_postgresql_repository.py \
  tests/integration/test_sbom_web_contract.py

PYTHONPATH=src:. python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml

cd web && npm test && npm run lint && npm run a11y && npm run a11y:jsx && npm run build
```

Ces contrôles garantissent les imports CycloneDX/SPDX, l’idempotence, le versionnement, la corrélation CVE, le risque contextualisé, la comparaison des releases, l’isolation tenant, les 14 routes SBOM et la migration `0048`. Ils vérifient également l’absence de scanner actif et de remédiation automatique.

## Validation GreenOps — v0.29.98

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_greenops_domain.py \
  tests/unit/test_greenops_edge_cases.py \
  tests/integration/test_greenops_services.py \
  tests/integration/test_greenops_cli.py \
  tests/integration/test_greenops_http_api.py \
  tests/integration/test_greenops_migration.py \
  tests/integration/test_greenops_postgresql_repository.py \
  tests/integration/test_greenops_web_contract.py

PYTHONPATH=src:. python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
```

Ces contrôles garantissent la distinction observé/estimé, la provenance du facteur carbone, les calculs PUE/CO₂e reproductibles, l’idempotence tenant-wide, les recommandations soumises à validation humaine, les 16 routes GreenOps et la migration `0047`.

## Validation discovery locale Lite/Pro — v0.29.61

Valider `openinfra discovery local-plan`, `POST /api/v1/discovery/local-plan`, OpenAPI, discovery document, portail web et garde-fous `dry_run`, `agent_required`, `network_scan_executed`, `rsot_write_enabled`.

Valider également que `openinfra-web` publie les groupes contextuels du panneau latéral (`OPENINFRA_SIDEBAR_CONTEXTS`, `sidebarOperationGroups`, `openinfra-sidebar-context`) pour tous les composants, avec les connecteurs Intégrations regroupés par fournisseur et sans opération OpenService côté web.

## Validation guides migration données — v0.29.60

```bash
PYTHONPATH=src python -m pytest -q   tests/unit/test_data_import_domain.py   tests/integration/test_import_services.py   tests/integration/test_cli_import.py   tests/integration/test_http_api.py   tests/integration/test_http_api_error_contracts.py   tests/integration/test_openinfra_web.py   -o addopts=""
PYTHONPATH=src python scripts/validate_frontend.py --project-root .
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0
PYTHONPATH=src python docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/scripts/validate_roadmap.py --root docs/specifications/OpenInfra-Roadmap-Developpement-v2.2
```

Ces contrôles garantissent que les guides Device42, NetBox, Nautobot, GLPI et CSV exposent template, étapes, contrôles, rollback et critères de succès via CLI/API/discovery/OpenAPI/portail web, sans mutation RSOT ni ticketing natif.

## Validation openinfra-web / Compose — v0.29.13

```bash
PYTHONPATH=src:. python -m pytest -q tests/integration/test_openinfra_web.py tests/integration/test_runtime_docker_environment.py --no-cov
python scripts/validate_frontend.py --project-root .
PYTHONPATH=src:. python scripts/quality_gate.py
```

Ces contrôles garantissent que `openinfra-web` sert l'interface, expose `/config.json`, proxyfie `/api/*` vers le backend, refuse les URL backend dangereuses, n'expose pas de DSN PostgreSQL et est réellement déclaré dans `compose.yaml`, `.env.example`, le smoke Docker et l'installateur natif.

## Validation P02 éditions / feature gates — v0.29.0

```bash
PYTHONPATH=src:. pytest tests/integration/test_editions_feature_gates.py
PYTHONPATH=src python -m openinfra.interfaces.cli edition list --data /tmp/openinfra-editions.json
PYTHONPATH=src python -m openinfra.interfaces.cli edition feature-check --tenant default --edition lite --capability distributed_discovery_agents
PYTHONPATH=src python -m openinfra.interfaces.cli edition quota-check --data /tmp/openinfra-editions.json --edition lite --tenant default --resource user --increment 1
```

Ces contrôles garantissent que les éditions Lite/Pro/Enterprise sont appliquées par le backend, que les quotas runtime sont calculés depuis les repositories JSON/PostgreSQL et que les collectors Discovery restent réservés à Enterprise.

## Validation réalignement CDC v4.8.1 / roadmap v2 — v0.28.1

```bash
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0
```

Ces contrôles garantissent que les installateurs Lite/Pro/Enterprise n'exposent aucun secret en clair, respectent les tailles LVM PostgreSQL attendues, utilisent les services systemd canoniques et restent alignés avec les nouveaux référentiels contractuels.

# Runbook de validation


## Validation Discovery collectors v0.28.1

```bash
PYTHONPATH=src python -m pytest -q tests/unit/test_discovery_domain.py tests/integration/test_discovery_collector_services.py tests/integration/test_cli_discovery.py tests/integration/test_http_api.py
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0023_discovery_collector_registry --root installers/migrations/postgresql >/tmp/openinfra-0023.sql
```

Contrôles bloquants spécifiques :

- un collector inconnu doit produire `authorized=false` et ne recevoir aucun job ;
- une empreinte certificat différente doit produire `fingerprint_mismatch` ;
- un collector désactivé doit produire `collector_not_active` ;
- un scope non déclaré doit produire `scope_not_authorized` ;
- aucune valeur secrète collector ne doit être persistée : seules les références `vault://...` sont autorisées.

## Validation locale minimale

```bash
PYTHONPATH=src python -m pytest
PYTHONPATH=src python -m compileall -q src tests scripts docker
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0001_bootstrap --root installers/migrations/postgresql >/tmp/openinfra-0001.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0002_security_rbac --root installers/migrations/postgresql >/tmp/openinfra-0002.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0003_security_token_lifecycle --root installers/migrations/postgresql >/tmp/openinfra-0003.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0004_identity_users_groups --root installers/migrations/postgresql >/tmp/openinfra-0004.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0005_access_policy_abac --root installers/migrations/postgresql >/tmp/openinfra-0005.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0006_audit_trail_integrity --root installers/migrations/postgresql >/tmp/openinfra-0006.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0007_source_of_truth_core --root installers/migrations/postgresql >/tmp/openinfra-0007.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0008_source_governance --root installers/migrations/postgresql >/tmp/openinfra-0008.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0009_dcim_physical_model --root installers/migrations/postgresql >/tmp/openinfra-0009.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0010_dcim_rack_capacity --root installers/migrations/postgresql >/tmp/openinfra-0010.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0011_dcim_field_operations --root installers/migrations/postgresql >/tmp/openinfra-0011.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0012_dcim_visualization_indexes --root installers/migrations/postgresql >/tmp/openinfra-0012.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0013_dcim_cabling_foundation --root installers/migrations/postgresql >/tmp/openinfra-0013.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root installers/migrations/postgresql >/tmp/openinfra-0014.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0015_ipam_enterprise_foundation --root installers/migrations/postgresql >/tmp/openinfra-0015.sql
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate --data /tmp/openinfra-state.json --tenant default --vrf default --prefix 10.99.0.0/30 --hostname validation --idempotency-key validation-1
```

## Validation PostgreSQL avec DSN réel

```bash
export OPENINFRA_DATABASE_DSN='postgresql://openinfra:secret@postgres:5432/openinfra'
PYTHONPATH=src python -m openinfra.interfaces.cli database status --root installers/migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations --root installers/migrations/postgresql --dry-run
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations --root installers/migrations/postgresql
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

## Validation facultative du lab Docker

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```

Cette validation démarre PostgreSQL dans un lab, applique les migrations avec `openinfra database apply-migrations`, lance l’API avec backend PostgreSQL et exécute les smoke tests API/CLI. Elle est facultative : le runtime de production officiel reste le déploiement serveur natif avec virtualenv Python, systemd et PostgreSQL externe/cluster.

## Critères bloquants

- Couverture globale inférieure à 98 %.
- Migration absente ou non partitionnée.
- Historique de migrations PostgreSQL absent dans un environnement runtime.
- Checksum divergent sur une migration déjà appliquée.
- Fichier source contractuel v4 absent.
- Commande CLI documentée mais non testée.
- Fonction publique module-level dans `src/openinfra`, car le code produit doit rester orienté objet.
- Runtime serveur natif incomplet ou incapable de lancer l’API, charger la configuration et exécuter les smoke tests.

## Validations sécurité v0.7.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token \
  --data /tmp/openinfra-security.json \
  --tenant default \
  --subject validation-client \
  --role ipam:operator \
  --token "$(python - <<'PY'
import secrets
print("oi_" + secrets.token_urlsafe(48))
PY
)"
PYTHONPATH=src python -m pytest tests/unit/test_security_domain.py tests/integration/test_http_api.py
```

La CI exécute aussi le smoke runtime natif authentifié, incluant inventaire et révocation de jeton temporaire. Le lab Docker reste facultatif.

## Validation IAM v0.7.0

Les tests automatisés couvrent la création d’utilisateurs, la création de groupes, les appartenances, les rôles directs, les rôles hérités, l’agrégation avec les rôles du jeton, les commandes CLI, les endpoints API et l’adaptateur PostgreSQL simulé.

Commandes dédiées :

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0004_identity_users_groups --root installers/migrations/postgresql
PYTHONPATH=src python3 -m pytest -q tests/unit/test_identity_domain.py tests/integration/test_identity_services.py
```

## Validation ABAC v0.8.0

Commandes minimales :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0005_access_policy_abac --root installers/migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli access create-rule --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --name worker-par1-prod --permission ipam.allocate --effect allow --subject worker-client --site-code PAR1 --environment prod
PYTHONPATH=src python -m openinfra.interfaces.cli access evaluate --data /tmp/openinfra.json --tenant default --token "$WORKER_TOKEN" --permission ipam.allocate --site-code PAR1 --environment prod
PYTHONPATH=src python -m pytest -q tests/unit/test_access_policy_domain.py tests/integration/test_access_policy_services.py
```

La CI exécute également un smoke test JSON ABAC. Les scénarios PostgreSQL/API/CLI sont couverts par le runtime natif et peuvent être rejoués dans le lab Docker facultatif.


## Validation Audit Trail v0.9.0

Commandes minimales :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0006_audit_trail_integrity --root installers/migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli audit list --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --limit 100
PYTHONPATH=src python -m openinfra.interfaces.cli audit export --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --format jsonl --limit 500
PYTHONPATH=src python -m openinfra.interfaces.cli audit verify-integrity --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN"
PYTHONPATH=src python -m pytest -q tests/unit/test_audit_domain.py tests/integration/test_audit_trail_services.py
```

La CI exécute également un smoke test JSON audit et le runtime natif valide les contrats API/CLI. Les endpoints `/api/v1/audit/events`, `/api/v1/audit/export` et `/api/v1/audit/integrity` peuvent être rejoués contre PostgreSQL dans le lab Docker facultatif.

## Contrôles ajoutés en v0.10.0

- Tests unitaires du domaine RSOT (Ressource Source of Truth) : clés sûres, tags, source, relation, snapshots et erreurs contrôlées.
- Tests d'intégration JSON : objet, mise à jour versionnée, relation, liste paginée, restitution de version et erreurs d'autorisation.
- Tests CLI : `openinfra rsot upsert-object`, `list-objects`, `get-object-version`, `create-relation`, `list-relations`.
- Tests API HTTP : `/api/v1/rsot/objects`, `/api/v1/rsot/object-versions`, `/api/v1/rsot/object-as-of`, `/api/v1/rsot/object-audit`, `/api/v1/rsot/relations`.
- Tests adaptateur PostgreSQL simulé : insert/update objet, snapshot, relation et requêtes paginées.

## Contrôles ajoutés en v0.11.0

- Tests unitaires du domaine Source Governance : validation des chemins, wildcard, priorité, fraîcheur et détection de modifications imbriquées.
- Tests d'intégration JSON : création de règle, inventaire, évaluation, désactivation et enforcement dans `SourceOfTruthService`.
- Tests CLI : `openinfra rsot create-governance-rule`, `list-governance-rules`, `evaluate-governance`, `deactivate-governance-rule`.
- Tests API HTTP : `/api/v1/rsot/governance-rules`, `/api/v1/rsot/governance/evaluate`, `/api/v1/rsot/governance/deactivate-rule`.
- Tests adaptateur PostgreSQL simulé : persistance, lecture paginée et évaluation via `PostgreSQLSourceGovernanceRepository`.
- Smoke runtime natif : scénario gouvernance RSOT contre API authentifiée. Le backend PostgreSQL réel peut être testé dans le lab Docker facultatif ou sur un serveur PostgreSQL dédié.


## Contrôles ajoutés en v0.12.0

- Tests unitaires du domaine DCIM physique : région de site, étage, zone et invariants de grille.
- Tests d’intégration JSON : définition idempotente de salle, zone incluse dans grille, localisation avec étage/zone/coordonnées et rejets métier.
- Tests CLI : `openinfra dcim define-room` puis `openinfra dcim locate --floor --zone`.
- Tests API HTTP : `POST /api/v1/dcim/rooms` protégé par `dcim.write` lorsque l’API authentifiée est activée.
- Tests adaptateur PostgreSQL simulé : persistance des nouveaux champs DCIM et rendu de `0009_dcim_physical_model.sql`.
- Smoke runtime natif : création de salle DCIM physique et localisation équipement. PostgreSQL réel est validable sur serveur dédié ou dans le lab Docker facultatif.

## Contrôles ajoutés en v0.13.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0010_dcim_rack_capacity --root installers/migrations/postgresql >/tmp/openinfra-0010.sql
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-rack --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01 --row A --column 01 --units 42 --face front --face rear
PYTHONPATH=src python -m openinfra.interfaces.cli dcim rack-capacity --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01
```

Les tests ajoutés couvrent le domaine rack, le service de capacité, le rejet des chevauchements U, la CLI, l'API HTTP et le smoke runtime natif.

## Contrôles ajoutés en v0.14.0

Le seuil de couverture globale est relevé à `>= 98 %` dans `pyproject.toml` et la CI. La commande de référence devient :

```bash
PYTHONPATH=src python3 -m pytest -q
```

Le périmètre de couverture locale exclut l’adaptateur PostgreSQL bas niveau, qui reste couvert par tests d’intégration simulés et par le runtime Docker/Compose lorsqu’un moteur PostgreSQL réel est disponible. Les validations fonctionnelles locales couvrent les domaines, services applicatifs, CLI/API, magasin JSON, contrats HTTP et scénarios QR terrain.


## Contrôles ajoutés en v0.15.0

La v0.15.0 conserve le seuil bloquant `>= 98 %` et ajoute les contrôles P04 / EPIC-0404 suivants :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0012_dcim_visualization_indexes --root installers/migrations/postgresql >/tmp/openinfra-0012.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0013_dcim_cabling_foundation --root installers/migrations/postgresql >/tmp/openinfra-0013.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root installers/migrations/postgresql >/tmp/openinfra-0014.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0015_ipam_enterprise_foundation --root installers/migrations/postgresql >/tmp/openinfra-0015.sql
PYTHONPATH=src python -m openinfra.interfaces.cli dcim room-plan --tenant default --site PAR1 --building BAT-A --room MMR1 --format json
PYTHONPATH=src python -m openinfra.interfaces.cli dcim room-plan --tenant default --site PAR1 --building BAT-A --room MMR1 --format svg
PYTHONPATH=src python -m openinfra.interfaces.cli dcim rack-elevation --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01 --face front --format json
PYTHONPATH=src python -m openinfra.interfaces.cli dcim rack-elevation --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01 --face front --format html
```

Les tests couvrent le domaine de visualisation, les services applicatifs, les ports JSON/PostgreSQL, la CLI, l’API HTTP et les contrats d’erreur. Les endpoints `GET /api/v1/dcim/room-plan` et `GET /api/v1/dcim/rack-elevation` sont protégés par les mêmes règles d’authentification DCIM que la localisation terrain.


## Contrôles ajoutés en v0.16.0

La v0.16.0 conserve le seuil bloquant `>= 98 %` et ajoute les contrôles P04 / EPIC-0405 suivants :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0013_dcim_cabling_foundation --root installers/migrations/postgresql >/tmp/openinfra-0013.sql
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-patch-panel --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01 --patch-panel PP01 --rack-face front --u-position 2 --port-count 24 --connector rj45 --medium copper
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-port --tenant default --owner-type equipment --owner-code SRV-001 --port-name ETH0 --connector rj45 --medium copper
PYTHONPATH=src python -m openinfra.interfaces.cli dcim connect-cable --tenant default --cable-id CAB-0001 --a-owner-type equipment --a-owner-code SRV-001 --a-port-name ETH0 --b-owner-type patch_panel --b-owner-code PP01 --b-port-name P01 --medium copper --path "Rack R01" --path "Patch panel PP01"
PYTHONPATH=src python -m openinfra.interfaces.cli dcim cable-trace --tenant default --cable-id CAB-0001
PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .
```

Les tests couvrent le domaine de câblage, les services applicatifs, les ports JSON/PostgreSQL, la CLI, l’API HTTP, les contrats d’erreur et les branches de validation connecteur/média. Le quality gate ne dépend plus d’un moteur Docker et contrôle le runtime serveur natif.


## Correctif CI audit vulnérabilités v0.17.4

Le contrôle `pip-audit` bloquant doit auditer le fichier `requirements/security-audit.txt` :

```bash
python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off
```

Il ne doit pas auditer directement l'environnement Python complet lorsque le package projet est installé en editable pour les tests CI. Ce mode provoque un échec non métier `distribution marked as editable` et masque l'objectif réel du contrôle : l'audit des dépendances tierces vulnérables.

## Correctif CI sécurité v0.17.2 et v0.17.3

La v0.17.2 corrige la CI pour intégrer des contrôles sécurité bloquants sur `push` et pull request. La v0.17.4 corrige définitivement l’audit de vulnérabilités en utilisant une entrée dédiée aux dépendances tierces. Le workflow couvre Python `3.11`, `3.12`, `3.13` et `3.14`.

Commandes locales de référence :

```bash
python3 -m ruff format --check src tests scripts docker
python3 -m ruff check src tests scripts docker
python3 -m mypy src/openinfra
python3 -m bandit -q -r src/openinfra
python3 scripts/security_gate.py --project-root .
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 scripts/quality_gate.py
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root installers/migrations/postgresql
python3 scripts/native_runtime_smoke.py --project-root .
```

`pip-audit` est exécuté dans GitHub Actions après installation de `.[postgresql,dev]`. En local, son exécution nécessite que la dépendance `pip-audit` soit disponible dans l'environnement Python courant.

La correction RBAC du smoke sécurité impose un jeton `security:admin` pour `security list-tokens` et `security revoke-token`. Le jeton `ipam:operator` reste limité aux opérations IPAM et lecture de schéma.


## Correctif CI audit vulnérabilités v0.17.3

La commande CI d’audit de vulnérabilités est :

```bash
python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off
```

`requirements/security-audit.txt` est obligatoire parce que la CI installe OpenInfra avec `pip install -e .[postgresql,dev]`. Le package projet n’est pas une dépendance tierce ; l’audit doit donc porter sur une entrée de dépendances explicite et non échouer sur l'installation editable du projet.

Le test local sans accès réseau complet peut valider la collecte avec :

```bash
python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run
```

## Contrôles ajoutés en v0.17.0

La v0.17.0 conserve le seuil bloquant `>= 98 %`, corrige le déclenchement GitHub Actions et ajoute les contrôles P04 / EPIC-0406 suivants :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root installers/migrations/postgresql >/tmp/openinfra-0014.sql
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-power-device --tenant default --code PDU-A --kind pdu --site PAR1 --building BAT-A --room MMR1 --rack R01 --side A --capacity-watts 8000
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-power-circuit --tenant default --circuit-id CIR-A-01 --source-device PDU-A --site PAR1 --building BAT-A --room MMR1 --rack R01 --side A --capacity-watts 4000 --breaker-rating-amps 16
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-cooling-zone --tenant default --site PAR1 --building BAT-A --room MMR1 --zone Z1 --role cold_aisle --cooling-capacity-watts 12000 --supply-temperature-c 18 --return-temperature-c 30
PYTHONPATH=src python -m openinfra.interfaces.cli dcim reserve-power --tenant default --asset-tag SRV-001 --circuit-id CIR-A-01 --expected-watts 1200
PYTHONPATH=src python -m openinfra.interfaces.cli dcim energy-cooling-capacity --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01
```

Les tests couvrent le domaine énergie/refroidissement, les services applicatifs, les ports JSON/PostgreSQL, la CLI, l’API HTTP authentifiée et non authentifiée, les contrats d’erreur, la correction du workflow GitHub Actions et les branches de capacité source/circuit/rack/refroidissement.

## Correctif CI Dependency Review v0.17.6

La v0.17.6 corrige le statut GitHub Actions `Dependency review / PR vulnerability gate (push) Skipped`. Le workflow de push ne contient plus de job PR-only. La revue différentielle des dépendances est déplacée dans `.github/workflows/dependency-review.yml`, déclenché uniquement sur pull request.

Validation attendue :

```bash
python scripts/security_gate.py --project-root .
python -m ruff format --check src tests scripts docker
python -m ruff check src tests scripts docker
python -m mypy src/openinfra
python -m bandit -q -r src/openinfra
PYTHONPATH=src python -m pytest
```


## Correctif CI Python 3.13 jetons v0.17.6

La v0.17.6 corrige les échecs intermittents du smoke sécurité lorsque le jeton généré aléatoirement commence par `-`. Les commandes CI utilisent désormais des jetons préfixés par `ci_`, et le gate sécurité refuse la génération non préfixée.

Contrôle attendu :

```bash
PYTHONPATH=src python3 scripts/security_gate.py --project-root .
```


## Contrôles ajoutés en v0.18.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0015_ipam_enterprise_foundation --root installers/migrations/postgresql >/tmp/openinfra-0015.sql
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vrf --tenant default --name prod --route-distinguisher 65000:1
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-aggregate --tenant default --vrf prod --cidr 10.0.0.0/8
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-prefix --tenant default --vrf prod --cidr 10.10.0.0/24
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-range --tenant default --vrf prod --prefix 10.10.0.0/24 --start 10.10.0.10 --end 10.10.0.200
PYTHONPATH=src python -m openinfra.interfaces.cli ipam register-address --tenant default --vrf prod --prefix 10.10.0.0/24 --address 10.10.0.10 --hostname validation --interface-name eth0
PYTHONPATH=src python -m openinfra.interfaces.cli ipam capacity --tenant default --vrf prod --prefix 10.10.0.0/24
```

Les tests automatisés couvrent le domaine IPAM IPv4/IPv6, les services applicatifs, les adaptateurs JSON/PostgreSQL simulés, les commandes CLI, les endpoints API HTTP et la règle de non-chevauchement par VRF.


## Contrôles ajoutés en v0.19.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0016_ipam_transactional_allocation --root installers/migrations/postgresql >/tmp/openinfra-0016.sql
tmpdir="$(mktemp -d)"
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-range --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24 --start 10.60.0.10 --end 10.60.0.20
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-range --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24 --start 10.60.0.10 --end 10.60.0.12 --purpose exclusion
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24 --hostname validation --idempotency-key validation-1
PYTHONPATH=src python -m openinfra.interfaces.cli ipam capacity --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24
```

Les tests automatisés incluent un scénario de 100 allocations concurrentes sur backend JSON, la vérification des plages d’allocation/exclusion/réservation, la prise en compte des adresses enregistrées et le verrou PostgreSQL simulé `pg_advisory_xact_lock`.


## Contrôles ajoutés en v0.20.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0017_ipam_networking_foundation --root installers/migrations/postgresql >/tmp/openinfra-0017.sql
tmpdir="$(mktemp -d)"
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vrf --data "$tmpdir/state.json" --tenant default --name prod --route-distinguisher 65000:1
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vlan-group --data "$tmpdir/state.json" --tenant default --name fabric --scope dc1
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vxlan-vni --data "$tmpdir/state.json" --tenant default --vni 100100 --name prod-servers --vrf prod --route-target-import 65000:100 --route-target-export 65000:100
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vlan --data "$tmpdir/state.json" --tenant default --group fabric --vlan-id 100 --name servers --vrf prod --vni 100100
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-asn --data "$tmpdir/state.json" --tenant default --asn 65000 --name local-fabric
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-asn --data "$tmpdir/state.json" --tenant default --asn 65100 --name upstream
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-bgp-peer --data "$tmpdir/state.json" --tenant default --vrf prod --local-asn 65000 --remote-asn 65100 --peer-address 192.0.2.1 --route-target-import 65000:100 --route-target-export 65000:100
PYTHONPATH=src python -m openinfra.interfaces.cli ipam network-bindings --data "$tmpdir/state.json" --tenant default --vrf prod
```

Les tests automatisés couvrent la cohérence VRF/VLAN/VNI/ASN, l’unicité VNI par tenant, les route targets, les pairs BGP IPv4/IPv6, les adaptateurs JSON/PostgreSQL, la CLI et les contrats API HTTP.

## Contrôles ajoutés en v0.21.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0018_ipam_conflict_detection --root installers/migrations/postgresql >/tmp/openinfra-0018.sql

tmpdir="$(mktemp -d)"
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-prefix --data "$tmpdir/state.json" --tenant default --vrf prod --cidr 10.251.0.0/24
PYTHONPATH=src python -m openinfra.interfaces.cli ipam register-address --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.251.0.0/24 --address 10.251.0.10 --hostname ci-owner
PYTHONPATH=src python -m openinfra.interfaces.cli ipam observe-dhcp-lease --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.251.0.0/24 --address 10.251.0.10 --mac-address aa:bb:cc:25:10:10 --hostname ci-rogue --source dhcp
PYTHONPATH=src python -m openinfra.interfaces.cli ipam observe-dns --data "$tmpdir/state.json" --tenant default --vrf prod --hostname ci-owner.example.net --address 10.251.0.10 --ptr-hostname old.example.net --source dns
PYTHONPATH=src python -m openinfra.interfaces.cli ipam detect-conflicts --data "$tmpdir/state.json" --tenant default --vrf prod
```

Critères attendus : rapport JSON contenant au minimum `duplicate_address`, `lease_conflict` et `dns_ptr_divergence`; couverture globale maintenue au seuil `>= 98 %`; CI sans étape security smoke dupliquée.


## Contrôles ajoutés en v0.22.0

- Vérifier `openinfra ipam ui-dashboard --tenant default --format json`.
- Vérifier `openinfra ipam ui-dashboard --tenant default --format html`.
- Vérifier `openinfra ipam ui-search --tenant default --query <ip|hostname>`.
- Vérifier `openinfra ipam reservation-wizard` en dry-run puis avec `--apply`.
- Vérifier les endpoints `/api/v1/ipam/ui-dashboard`, `/api/v1/ipam/ui-search`, `/api/v1/ipam/reservation-wizard` et `/ui/ipam`.


## Contrôles ajoutés en v0.22.2

- Vérifier qu’aucune migration PostgreSQL ne référence `audit_events.occurred_at`.
- Vérifier que le `Dockerfile` ne porte pas de `HEALTHCHECK` API global.
- Vérifier que les tags Docker par défaut `.env.example`, `compose.yaml` et `scripts/docker_environment.py` sont alignés avec la version courante.


## Contrôles ajoutés en v0.22.2

- Vérifier que `compose.yaml` contient le service `pgadmin`, le volume `openinfra-pgadmin-data` et le montage `docker/pgadmin/servers.json`.
- Vérifier que `.env.example` contient les variables `OPENINFRA_PGADMIN_EMAIL`, `OPENINFRA_PGADMIN_PASSWORD`, `OPENINFRA_PGADMIN_BIND`, `OPENINFRA_PGADMIN_PORT` et `OPENINFRA_PGADMIN_IMAGE`.
- Vérifier que `scripts/docker_environment.py init` génère un mot de passe pgAdmin4 local et que `up` démarre aussi `pgadmin`.
- Vérifier que `Dockerfile` reste sans `HEALTHCHECK` global et que le runtime production reste natif.

## Contrôles ajoutés en v0.22.3

Le quality gate vérifie que `0015_ipam_enterprise_foundation.sql` ajoute et backfill `prefixes.family` avant la création de l’index IPAM enterprise associé.

## Contrôles ajoutés en v0.23.1

La v0.23.1 conserve le seuil bloquant `>= 98 %` et ajoute les validations P05 / EPIC-0506 suivantes :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli ipam ddi-preview --data .openinfra.json --tenant default --vrf prod --idempotency-key req-0001 --provider all --dns-zone example.net --mac-address aa:bb:cc:00:00:01
PYTHONPATH=src python -m pytest -q --no-cov tests/unit/test_domain_ipam_ddi.py tests/integration/test_ipam_ddi_services.py
```

Le contrôle vérifie la génération des changements BIND/PowerDNS/Kea, les divergences DNS/PTR/DHCP, l’absence de divergence silencieuse et la présence d’un plan de rollback compensatoire.

## Contrôles ajoutés en v0.23.1

La v0.23.1 ajoute les contrôles de non-régression suivants :

- `GET /` retourne `service=openinfra-api`, `status=ok` et les liens `/health`, `/ready`, `/api/v1/version`, `/api/v1/database/schema` ;
- `GET /api/v1` retourne le même contrat d’entrée pour la version courante ;
- le smoke Docker compare `/api/v1/version` avec `openinfra.__version__` au lieu d’une ancienne version codée en dur ;
- l’entrypoint API écrit un événement JSON `openinfra_api_started` visible dans stdout et donc dans `docker logs openinfra-api`.

## Contrôles ajoutés en v0.25.1

La v0.25.1 ajoute les contrôles P06 / EPIC-0602 suivants :

```bash
tmpdir="$(mktemp -d)"
token="$(python - <<'PY'
print("b" * 40)
PY
)"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token --data "$tmpdir/state.json" --tenant default --subject bulk-import-admin --role rsot:operator --token "$token" >/dev/null
printf 'asset_key,kind,name,source,serial\ndevice/bulk-001,device,Bulk 001,csv_import,SN001\ndevice/bulk-002,device,Bulk 002,csv_import,SN002\n' > "$tmpdir/bulk.csv"
PYTHONPATH=src python -m openinfra.interfaces.cli import bulk-dataset --data "$tmpdir/state.json" --tenant default --actor bulk-import-admin --admin-token "$token" --file "$tmpdir/bulk.csv" --format csv --mapping-json '{"key":"asset_key","kind":"kind","display_name":"name","source":"source","attributes.serial":"serial"}' --batch-size 1000 --checkpoint-interval 1000
PYTHONPATH=src python -m pytest -q --no-cov tests/unit/test_data_import_domain.py tests/unit/test_import_parsers.py tests/integration/test_import_services.py tests/integration/test_cli_import.py tests/integration/test_http_api.py tests/integration/test_postgresql_migration.py
```

Les tests vérifient le streaming CSV, les batches bornés, les checkpoints, la reprise, la DLQ, le rapport bulk, la persistance JSON/PostgreSQL et la non-régression de l’import générique atomique livré en v0.24.0.


## Documentation API runtime v0.25.1

Le point d’entrée `GET /` et `GET /api/v1` publie les liens de documentation `Swagger UI` (`/docs` et `/swagger`), `ReDoc` (`/redoc`) et le contrat OpenAPI YAML (`/openapi.yaml` et `/api/v1/openapi.yaml`). Les smoke tests HTTP vérifient ces routes afin d’éviter une régression de découvrabilité API.
## Contrôles ajoutés en v0.25.2

La v0.25.2 ajoute un contrôle de séparation des requirements :

- `requirements/runtime.txt` : dépendances indispensables au runtime OpenInfra cœur ;
- `requirements/postgresql.txt` : dépendances production optionnelles du backend PostgreSQL ;
- `requirements/dev.txt` : outils développement, test, sécurité, packaging et CI uniquement ;
- `requirements/security-audit.txt` : agrégat d'audit `pip-audit` référençant explicitement les trois fichiers précédents.

Le `security_gate.py` bloque tout outil dev/CI placé dans les requirements production et tout fichier d'audit qui ne préserve pas cette séparation.


## Contrôles ajoutés en v0.26.0

La v0.26.0 ajoute les contrôles P06 / EPIC-0603 suivants :

```bash
tmpdir="$(mktemp -d)"
token="$(python -c 'print("x" * 40)')"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token --data "$tmpdir/state.json" --tenant default --subject export-admin --role rsot:operator --role audit:reader --token "$token" >/dev/null
PYTHONPATH=src python -m openinfra.interfaces.cli itrm upsert-object --data "$tmpdir/state.json" --tenant default --admin-token "$token" --key device/export-smoke --kind device --display-name "Export Smoke" --attributes-json '{"serial":"EXPORT-SMOKE"}' --tag prod --source smoke >/dev/null
PYTHONPATH=src python -m openinfra.interfaces.cli export request --data "$tmpdir/state.json" --tenant default --admin-token "$token" --format json --tag prod
PYTHONPATH=src python -m openinfra.interfaces.cli export run --data "$tmpdir/state.json" --tenant default --admin-token "$token"
PYTHONPATH=src python -m pytest -q --no-cov tests/integration/test_export_services.py tests/integration/test_cli_export.py tests/integration/test_http_api.py tests/integration/test_postgresql_migration.py
```

Les tests vérifient la file d’export, l’exécution worker, la pagination bornée, la sérialisation CSV/JSON/XLSX, le digest SHA-256, la signature HMAC-SHA256, le rejet des artefacts altérés, l’audit d’échec et la migration PostgreSQL `0021` partitionnée.


## Contrôles ajoutés en v0.27.0

La v0.27.0 ajoute les contrôles P06 / EPIC-0604 suivants : templates Device42/NetBox/Nautobot/GLPI/CSV, génération de plan de migration dry-run, rapport d’écarts, persistance du rapport, reprise par `job_id`, validation OpenAPI, smoke CLI migration et migration PostgreSQL `0022_legacy_migration_framework.sql`. Les tests de non-régression vérifient notamment qu’un mapping legacy ne produit aucune écriture en simulation et qu’une colonne requise absente devient un gap bloquant.


## Contrôles ajoutés en v0.29.10

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database ha-plan \
  --path installers/setup/enterprise/server/install.ini \
  --edition enterprise \
  --scope server
PYTHONPATH=src:. python -m pytest tests/integration/test_installer_alignment.py tests/unit/test_installer_config.py
```

La validation P06 vérifie le rendu du plan HA/PITR, l'absence de ports et paramètres bas niveau dans `install.ini`, les répertoires internes PITR/backup, le mode quasi temps réel lorsque `identity.peer_nodes` est renseigné, et la migration `0024_postgresql_ha_backup_registry.sql`.

### RSOT Quality & Certification — v0.29.14

Les contrôles de qualité RSOT sont validables via CLI et API :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli RSOT quality-object \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --key device/example

PYTHONPATH=src python -m openinfra.interfaces.cli RSOT quality-summary \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --kind device
```

Critères de validation : score de complétude, fraîcheur, autorité de source, confiance, statut de certification et audit `rsot.quality.*`.

## v0.29.58 — préparation OpenService autonome

La v0.29.58 ajoute les contrôles P25 / EPIC-2506 suivants : fournisseur externe `openservice`, alias contrôlés, validation de profil, plan CMDB, CLI, API, OpenAPI, discovery et contrôle négatif de non-exposition dans `openinfra-web`. Les tests de non-régression vérifient que `native_ticketing_enabled=false`, `openinfra_web_ui_enabled=false`, que les secrets restent des références et qu’aucun formulaire OpenService n’est publié dans le portail web OpenInfra.


## v0.29.59 — validations rollback imports massifs

```bash
python -m compileall -q src tests scripts docker
python scripts/validate_frontend.py --project-root .
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python scripts/security_gate.py
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0
python docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/scripts/validate_roadmap.py
PYTHONPATH=src python -m pytest --collect-only -q -o addopts='' --no-cov
PYTHONPATH=src python -m pytest -q tests/integration/test_import_services.py tests/integration/test_cli_import.py -o addopts=''
PYTHONPATH=src python -m pytest -q tests/integration/test_http_api.py::TestHttpApi::test_bulk_import_rollback_api_endpoint -o addopts=''
```

## Validation volumétrique du graphe RSOT — v0.29.94

Le gate P15/EPIC-1506 doit être exécuté hors mesure de couverture afin de ne pas fausser les latences :

```bash
mkdir -p build/reports
PYTHONPATH=src python -m openinfra.quality.dependency_graph_benchmark \
  --nodes 5000 \
  --spof-hubs 100 \
  --samples 3 \
  --warmups 1 \
  --one-level-threshold-ms 1500 \
  --filtered-threshold-ms 1500 \
  --spof-threshold-ms 5000 \
  --pagination-threshold-ms 15000 \
  --output build/reports/dependency-graph-benchmark.json
```

Contrôles associés :

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/unit/test_dependency_graph_benchmark.py \
  tests/performance/test_dependency_graph_volume.py \
  tests/integration/test_github_workflows.py
```

Un code `1` signale un dépassement de p95. Un code `2` signale une configuration invalide, une pagination non terminante ou une cardinalité incohérente. Le rapport `build/reports/dependency-graph-benchmark.json` doit être conservé avec les preuves de validation de la release.

## Opérations terrain mobiles/offline — v0.29.95

Les contrôles P16/EPIC-1601 couvrent le domaine, l'application, la persistance JSON/PostgreSQL, les interfaces REST/CLI, le parcours web accessible et la migration `0044`.

### Tests ciblés

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/unit/test_field_operations_domain.py \
  tests/unit/test_field_operation_location_and_safety.py \
  tests/integration/test_field_operation_services.py \
  tests/integration/test_field_operation_http_api.py \
  tests/integration/test_field_operation_cli.py \
  tests/integration/test_postgresql_migration.py \
  tests/integration/test_quality_gate_postgresql_schema.py \
  tests/integration/test_github_workflows.py
```

### Contrats OpenAPI, sécurité et qualité

```bash
python scripts/validate_openapi.py docs/api/openapi.yaml
python scripts/validate_openapi.py \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
PYTHONPATH=src python scripts/security_gate.py --project-root .
PYTHONPATH=src python scripts/quality_gate.py --project-root .
```

Le validateur YAML doit refuser toute clé dupliquée. Le gate PostgreSQL doit interdire `occurred_at` dans les instructions SQL visant `audit_events`, sans interdire l'horodatage métier de `field_event_outbox`.

### Frontend et accessibilité

```bash
npm --prefix web run lint
npm --prefix web run a11y
npm --prefix web run a11y:jsx
npm --prefix web test
npm --prefix web run build
npm --prefix web audit --omit=dev --audit-level=high
python scripts/validate_frontend.py --project-root .
```

Le menu attendu est **DCIM → Opérations terrain** dans les deux runtimes. Les formulaires doivent conserver les validations anticipées, les erreurs accessibles et les limites MIME/taille des preuves.

### Migration, installateurs et artefacts

```bash
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate \
  --path installers/setup/lite/server/install.ini
PYTHONPATH=src python -m openinfra.interfaces.cli installer apply \
  --path installers/setup/lite/server/install.ini \
  --dry-run
python -m build
python scripts/verify_artifact.py dist/openinfra-0.29.95-py3-none-any.whl
```

Le wheel doit contenir **44 migrations**, la dernière étant `0044_field_operations_mobile_offline.sql`, les modules Field Operations et les **17 routes** correspondantes.

### Smoke CLI local

```bash
state_file="$(mktemp)"
token="$(python -c 'print("x" * 40)')"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token \
  --data "$state_file" --tenant default --subject field-admin \
  --role dcim:operator --token "$token"
PYTHONPATH=src python -m openinfra.interfaces.cli dcim field-generate \
  --data "$state_file" --tenant default --admin-token "$token" \
  --target-kind equipment --target-key equipment/field-smoke \
  --site-key site/default --title "Field smoke"
```

Le parcours complet de verrouillage, démarrage, checklist, preuve, paquet hors ligne, synchronisation et clôture est validé par les tests d'intégration CLI et HTTP dédiés.

## Simulation de changement et migration — v0.29.96

```bash
PYTHONPATH=src:. pytest -q \
  tests/unit/test_simulation_domain.py \
  tests/integration/test_simulation_services.py \
  tests/integration/test_simulation_cli.py \
  tests/integration/test_simulation_http_api.py \
  tests/integration/test_simulation_migration.py \
  tests/integration/test_simulation_web_contract.py

PYTHONPATH=src python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml

ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
python -m build
python scripts/verify_artifact.py dist/openinfra-0.29.96-py3-none-any.whl
```

Vérifier dans chaque rapport les valeurs `production_mutation=false` et `execution_order=false`. Une analyse `truncated=true` n’est pas exhaustive et doit être relancée avec un périmètre ou une limite adaptés.

## FinOps et rangement de navigation — v0.29.97

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_finops_domain.py \
  tests/unit/test_finops_edge_cases.py \
  tests/integration/test_finops_services.py \
  tests/integration/test_finops_http_api.py \
  tests/integration/test_finops_cli.py \
  tests/integration/test_finops_migration.py \
  tests/integration/test_finops_web_contract.py \
  tests/integration/test_navigation_grouping_contract.py

PYTHONPATH=src:. pytest -q --no-cov \
  tests/integration/test_certificate_pki_web_contract.py \
  tests/integration/test_openinfra_web.py \
  tests/integration/test_web_accessibility_contract.py

PYTHONPATH=src:. python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml

ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
python -m build
python scripts/verify_artifact.py dist/openinfra-0.29.97-py3-none-any.whl
```

Vérifier que les rapports FinOps contiennent `production_billing_mutation=false`, que les périodes clôturées conservent leur digest et que la navigation n’expose plus Flux, Conformité réseau ou Certificats comme composants de premier niveau.

## Reprise d’activité multisite — v0.29.104

Les contrôles P17/EPIC-1703 valident les plans primaire/secours, les objectifs RPO/RTO, les preuves immuables d’exercice et l’absence de bascule automatique.

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/unit/test_multisite_disaster_recovery_domain.py \
  tests/integration/test_multisite_disaster_recovery.py \
  tests/integration/test_multisite_disaster_recovery_cli.py \
  tests/integration/test_multisite_disaster_recovery_http_api.py \
  tests/integration/test_multisite_migration.py \
  tests/integration/test_multisite_postgresql_repository.py \
  tests/integration/test_multisite_web_contract.py

PYTHONPATH=src python -m pytest
ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python scripts/quality_gate.py
```

Contrats, frontend et installateurs :

```bash
python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
npm --prefix web run lint
npm --prefix web run a11y
npm --prefix web run a11y:jsx
npm --prefix web test
npm --prefix web run build
python scripts/validate_frontend.py --project-root .
python scripts/validate_autonomous_installer.py --root installers
python scripts/validate_enterprise_alignment.py --project-root .
```

Packaging :

```bash
python -m build
python scripts/verify_artifact.py dist/openinfra-0.29.104-py3-none-any.whl
target="$(mktemp -d)/site-packages"
python -m pip install --no-deps --target "$target" dist/openinfra-0.29.104-py3-none-any.whl
PYTHONPATH="$target" python scripts/smoke_installed_wheel.py
```

Un exercice n’est réussi que si la confirmation opérateur, la disponibilité du site de secours, la restauration, l’endpoint de service, le RPO, l’ancienneté de sauvegarde et le RTO sont tous conformes. Le module ne doit jamais promouvoir PostgreSQL, exécuter un fencing, restaurer une sauvegarde ou modifier DNS/VIP automatiquement.

