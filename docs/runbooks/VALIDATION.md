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
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0010_dcim_rack_capacity --root migrations/postgresql >/tmp/openinfra-0010.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0011_dcim_field_operations --root migrations/postgresql >/tmp/openinfra-0011.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0012_dcim_visualization_indexes --root migrations/postgresql >/tmp/openinfra-0012.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0013_dcim_cabling_foundation --root migrations/postgresql >/tmp/openinfra-0013.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql >/tmp/openinfra-0014.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0015_ipam_enterprise_foundation --root migrations/postgresql >/tmp/openinfra-0015.sql
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

La CI exécute également un smoke test JSON ABAC. Les scénarios PostgreSQL/API/CLI sont couverts par le runtime natif et peuvent être rejoués dans le lab Docker facultatif.


## Validation Audit Trail v0.9.0

Commandes minimales :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0006_audit_trail_integrity --root migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli audit list --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --limit 100
PYTHONPATH=src python -m openinfra.interfaces.cli audit export --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN" --format jsonl --limit 500
PYTHONPATH=src python -m openinfra.interfaces.cli audit verify-integrity --data /tmp/openinfra.json --tenant default --admin-token "$ADMIN_TOKEN"
PYTHONPATH=src python -m pytest -q tests/unit/test_audit_domain.py tests/integration/test_audit_trail_services.py
```

La CI exécute également un smoke test JSON audit et le runtime natif valide les contrats API/CLI. Les endpoints `/api/v1/audit/events`, `/api/v1/audit/export` et `/api/v1/audit/integrity` peuvent être rejoués contre PostgreSQL dans le lab Docker facultatif.

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
- Smoke runtime natif : scénario gouvernance SOT contre API authentifiée. Le backend PostgreSQL réel peut être testé dans le lab Docker facultatif ou sur un serveur PostgreSQL dédié.


## Contrôles ajoutés en v0.12.0

- Tests unitaires du domaine DCIM physique : région de site, étage, zone et invariants de grille.
- Tests d’intégration JSON : définition idempotente de salle, zone incluse dans grille, localisation avec étage/zone/coordonnées et rejets métier.
- Tests CLI : `openinfra dcim define-room` puis `openinfra dcim locate --floor --zone`.
- Tests API HTTP : `POST /api/v1/dcim/rooms` protégé par `dcim.write` lorsque l’API authentifiée est activée.
- Tests adaptateur PostgreSQL simulé : persistance des nouveaux champs DCIM et rendu de `0009_dcim_physical_model.sql`.
- Smoke runtime natif : création de salle DCIM physique et localisation équipement. PostgreSQL réel est validable sur serveur dédié ou dans le lab Docker facultatif.

## Contrôles ajoutés en v0.13.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0010_dcim_rack_capacity --root migrations/postgresql >/tmp/openinfra-0010.sql
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
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0012_dcim_visualization_indexes --root migrations/postgresql >/tmp/openinfra-0012.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0013_dcim_cabling_foundation --root migrations/postgresql >/tmp/openinfra-0013.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql >/tmp/openinfra-0014.sql
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0015_ipam_enterprise_foundation --root migrations/postgresql >/tmp/openinfra-0015.sql
PYTHONPATH=src python -m openinfra.interfaces.cli dcim room-plan --tenant default --site PAR1 --building BAT-A --room MMR1 --format json
PYTHONPATH=src python -m openinfra.interfaces.cli dcim room-plan --tenant default --site PAR1 --building BAT-A --room MMR1 --format svg
PYTHONPATH=src python -m openinfra.interfaces.cli dcim rack-elevation --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01 --face front --format json
PYTHONPATH=src python -m openinfra.interfaces.cli dcim rack-elevation --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01 --face front --format html
```

Les tests couvrent le domaine de visualisation, les services applicatifs, les ports JSON/PostgreSQL, la CLI, l’API HTTP et les contrats d’erreur. Les endpoints `GET /api/v1/dcim/room-plan` et `GET /api/v1/dcim/rack-elevation` sont protégés par les mêmes règles d’authentification DCIM que la localisation terrain.


## Contrôles ajoutés en v0.16.0

La v0.16.0 conserve le seuil bloquant `>= 98 %` et ajoute les contrôles P04 / EPIC-0405 suivants :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0013_dcim_cabling_foundation --root migrations/postgresql >/tmp/openinfra-0013.sql
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
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql
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
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0014_dcim_energy_cooling_foundation --root migrations/postgresql >/tmp/openinfra-0014.sql
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
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0015_ipam_enterprise_foundation --root migrations/postgresql >/tmp/openinfra-0015.sql
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
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0016_ipam_transactional_allocation --root migrations/postgresql >/tmp/openinfra-0016.sql
tmpdir="$(mktemp -d)"
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-range --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24 --start 10.60.0.10 --end 10.60.0.20
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-range --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24 --start 10.60.0.10 --end 10.60.0.12 --purpose exclusion
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24 --hostname validation --idempotency-key validation-1
PYTHONPATH=src python -m openinfra.interfaces.cli ipam capacity --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.60.0.0/24
```

Les tests automatisés incluent un scénario de 100 allocations concurrentes sur backend JSON, la vérification des plages d’allocation/exclusion/réservation, la prise en compte des adresses enregistrées et le verrou PostgreSQL simulé `pg_advisory_xact_lock`.


## Contrôles ajoutés en v0.20.0

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0017_ipam_networking_foundation --root migrations/postgresql >/tmp/openinfra-0017.sql
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
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0018_ipam_conflict_detection --root migrations/postgresql >/tmp/openinfra-0018.sql

tmpdir="$(mktemp -d)"
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-prefix --data "$tmpdir/state.json" --tenant default --vrf prod --cidr 10.251.0.0/24
PYTHONPATH=src python -m openinfra.interfaces.cli ipam register-address --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.251.0.0/24 --address 10.251.0.10 --hostname ci-owner
PYTHONPATH=src python -m openinfra.interfaces.cli ipam observe-dhcp-lease --data "$tmpdir/state.json" --tenant default --vrf prod --prefix 10.251.0.0/24 --address 10.251.0.10 --mac-address aa:bb:cc:25:10:10 --hostname ci-rogue --source dhcp
PYTHONPATH=src python -m openinfra.interfaces.cli ipam observe-dns --data "$tmpdir/state.json" --tenant default --vrf prod --hostname ci-owner.example.net --address 10.251.0.10 --ptr-hostname old.example.net --source dns
PYTHONPATH=src python -m openinfra.interfaces.cli ipam detect-conflicts --data "$tmpdir/state.json" --tenant default --vrf prod
```

Critères attendus : rapport JSON contenant au minimum `duplicate_address`, `lease_conflict` et `dns_ptr_divergence`; couverture globale maintenue au seuil `>= 98 %`; CI sans étape security smoke dupliquée.
