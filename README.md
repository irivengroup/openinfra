# OpenInfra Python Foundation

OpenInfra est un socle Python orienté objet pour construire une solution open source de Source of Truth, DCIM, ITAM, Discovery, Dependency Mapping et IPAM Enterprise++ sans fonction ITSM intégrée.

Cette livraison correspond au socle exécutable de démarrage aligné avec la roadmap P01/P02 puis REL-01/P03 : architecture hexagonale, modèle domaine, CLI, API HTTP standard library, migrations PostgreSQL applicatives, adaptateur PostgreSQL runtime, sécurité API par jetons hachés avec expiration, révocation et rotation, IAM utilisateurs/groupes avec rôles effectifs, ABAC contextuel site/environnement, audit trail consultable/exportable avec intégrité chaînée, Source of Truth P03 objets/relations/historique, gouvernance minimale des sources autoritatives, DCIM P04 modèle physique pays/région/ville/site/bâtiment/étage/salle/zone/grille, environnement d’exécution Docker, tests, documentation et CI.

## Garanties de cette itération

- Code produit en Python POO : les comportements sont portés par des classes de domaine, services applicatifs, ports et adaptateurs.
- Séparation stricte `domain / application / infrastructure / interfaces`.
- Localisation DCIM univoque : pays, région, ville, site, bâtiment, étage, salle, zone, ligne, colonne, coordonnées X/Y/Z facultatives, rack et unité U.
- IPAM IPv4/IPv6 : VRF, préfixe, allocation transactionnelle côté service applicatif, idempotence par clé métier, détection de conflit.
- Persistance locale JSON atomique pour développement et tests reproductibles.
- Persistance PostgreSQL runtime optionnelle via `psycopg`, DSN explicite et transactions courtes.
- Migration PostgreSQL initiale avec tables partitionnées, index, contraintes et audit append-only.
- Moteur de migrations PostgreSQL applicatif : statut, dry-run, application idempotente, historique `openinfra_schema_migrations` et checksum SHA-256.
- CLI exploitable : `openinfra version`, `openinfra spec validate`, `openinfra dcim define-room`, `openinfra dcim locate`, `openinfra ipam allocate`, `openinfra security bootstrap-token`, `openinfra security whoami`, `openinfra security list-tokens`, `openinfra security revoke-token`, `openinfra security rotate-token`, `openinfra identity create-user`, `openinfra identity create-group`, `openinfra identity add-user-to-group`, `openinfra identity grant-user-role`, `openinfra identity grant-group-role`, `openinfra identity effective`, `openinfra access create-rule`, `openinfra access list-rules`, `openinfra access evaluate`, `openinfra access deactivate-rule`, `openinfra audit list`, `openinfra audit export`, `openinfra audit verify-integrity`, `openinfra sot upsert-object`, `openinfra sot get-object`, `openinfra sot list-objects`, `openinfra sot get-object-version`, `openinfra sot create-relation`, `openinfra sot list-relations`, `openinfra sot create-governance-rule`, `openinfra sot list-governance-rules`, `openinfra sot evaluate-governance`, `openinfra sot deactivate-governance-rule`, `openinfra database render-migration`, `openinfra database status`, `openinfra database apply-migrations`.
- API HTTP légère : `/health`, `/ready`, `/api/v1/version`, `/api/v1/database/schema`, `/api/v1/security/whoami`, `/api/v1/security/tokens`, `/api/v1/security/revoke-token`, `/api/v1/security/rotate-token`, `/api/v1/identity/users`, `/api/v1/identity/groups`, `/api/v1/identity/group-memberships`, `/api/v1/identity/user-roles`, `/api/v1/identity/group-roles`, `/api/v1/identity/effective`, `/api/v1/access/rules`, `/api/v1/access/evaluate`, `/api/v1/access/deactivate-rule`, `/api/v1/audit/events`, `/api/v1/audit/export`, `/api/v1/audit/integrity`, `/api/v1/sot/objects`, `/api/v1/sot/object-versions`, `/api/v1/sot/relations`, `/api/v1/sot/governance-rules`, `/api/v1/sot/governance/evaluate`, `/api/v1/sot/governance/deactivate-rule`, `/api/v1/ipam/allocate`, `/api/v1/dcim/rooms`.
- GitHub Actions complète : format, lint, types, tests, couverture, sécurité, build, smoke tests CLI/API et runtime Docker authentifié.

## Installation développeur

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
# Avec backend PostgreSQL runtime :
python -m pip install -e '.[dev,postgresql]'
```

## Commandes de validation

```bash
python scripts/quality_gate.py
python -m pytest
python -m openinfra.interfaces.cli version
python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
python -m compileall -q src tests scripts
```

Lorsque les outils de qualité sont installés :

```bash
ruff format --check src tests scripts
ruff check src tests scripts
mypy src/openinfra
bandit -q -r src/openinfra
python -m build
python scripts/verify_artifact.py dist/*.whl
```

## Exécution CLI sans installation

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration --name 0001_bootstrap
```

## API locale

```bash
PYTHONPATH=src python -m openinfra.interfaces.http_api --host 127.0.0.1 --port 8080 --data .openinfra.json
```

## Exemple IPAM

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate \
  --data .openinfra.json \
  --tenant default \
  --vrf default \
  --prefix 10.10.0.0/24 \
  --hostname srv-app-01 \
  --idempotency-key req-0001
```

## Exemple DCIM

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-room \
  --data .openinfra.json \
  --tenant default \
  --site-code PAR1 \
  --site-name "Paris Datacenter 1" \
  --country FR \
  --region IDF \
  --city Paris \
  --building-code BAT-A \
  --building-name "Bâtiment A" \
  --floor-code F01 \
  --floor-name "Niveau 1" \
  --floor-index 1 \
  --room-code MMR1 \
  --room-name "Salle MMR" \
  --row A \
  --row B \
  --column 01 \
  --column 02 \
  --zone-code Z1 \
  --zone-name "Zone critique" \
  --zone-row A \
  --zone-column 01
PYTHONPATH=src python -m openinfra.interfaces.cli dcim locate \
  --asset-tag SRV-0001 \
  --site PAR1 \
  --building BAT-A \
  --floor F01 \
  --room MMR1 \
  --zone Z1 \
  --row A \
  --column 12 \
  --rack R42 \
  --u-position 18
```


## Sécurité API, RBAC et cycle de vie des jetons

La v0.8.0 étend le socle RBAC exploitable pour les accès API : les jetons sont hachés en SHA-256 avant persistance, les rôles intégrés sont validés côté domaine et chaque création, inventaire, révocation et rotation de jeton produit un événement d’audit. L’authentification API est désactivée par défaut pour préserver la compatibilité ascendante des exemples existants. Elle s’active avec `--auth-required` ou `OPENINFRA_AUTH_REQUIRED=true`.

Rôles intégrés :

- `admin` : toutes les permissions initiales ;
- `ipam:operator` : allocation IPAM et lecture de statut de schéma ;
- `dcim:operator` : localisation DCIM et lecture de statut de schéma ;
- `viewer` : lecture de statut de schéma ;
- `security:admin` : administration sécurité initiale et lecture de statut de schéma.
- `access:admin` : administration des politiques ABAC et lecture de statut de schéma.

Exemple JSON local avec expiration explicite :

```bash
TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token \
  --data .openinfra.json \
  --tenant default \
  --subject api-client-01 \
  --role ipam:operator \
  --token "$TOKEN" \
  --ttl-seconds 86400
PYTHONPATH=src python -m openinfra.interfaces.cli security whoami \
  --data .openinfra.json \
  --tenant default \
  --token "$TOKEN"
PYTHONPATH=src python -m openinfra.interfaces.cli security list-tokens \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$TOKEN"
```

Les commandes `revoke-token` et `rotate-token` permettent de retirer un jeton compromis ou de remplacer un jeton administrateur sans exposer de hash ni secret en sortie. En backend PostgreSQL, les commandes acceptent `--backend postgresql` et `--postgres-dsn`, ou utilisent `OPENINFRA_DATABASE_DSN`. Le runtime Docker applique les migrations, crée un jeton d’amorçage depuis le `.env` local généré et lance l’API avec authentification obligatoire.


## IAM utilisateurs, groupes et rôles effectifs

La v0.8.0 ajoute un socle IAM persistant : utilisateurs, groupes, appartenance utilisateur/groupe, rôles directs et rôles hérités des groupes. L’authentification par jeton conserve les rôles embarqués dans le jeton et agrège, lorsque le sujet du jeton correspond à un utilisateur IAM actif, les rôles directs et les rôles des groupes actifs. Cette compatibilité évite de casser les jetons existants tout en permettant une administration plus proche des standards entreprise.

Exemple local avec un jeton administrateur existant :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token \
  --data .openinfra.json \
  --tenant default \
  --subject identity-admin \
  --role admin \
  --token "$ADMIN_TOKEN"
PYTHONPATH=src python -m openinfra.interfaces.cli identity create-user \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --username alice \
  --display-name "Alice Infra" \
  --email alice@example.com \
  --role viewer
PYTHONPATH=src python -m openinfra.interfaces.cli identity create-group \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --name ipam-ops \
  --display-name "IPAM Operators" \
  --role ipam:operator
PYTHONPATH=src python -m openinfra.interfaces.cli identity add-user-to-group \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --username alice \
  --group ipam-ops
PYTHONPATH=src python -m openinfra.interfaces.cli identity effective \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --subject alice
```

La migration PostgreSQL `0004_identity_users_groups.sql` crée des tables partitionnées par `tenant_id`, des index sur rôles et appartenance, ainsi qu’un index d’audit dédié aux actions `identity.%`.

## ABAC contextuel tenant/site/environnement

La v0.8.0 ajoute un premier socle ABAC, c’est-à-dire un contrôle d’accès par attributs venant compléter RBAC. RBAC décide si un principal possède la permission fonctionnelle, par exemple `ipam.allocate`. ABAC restreint ensuite le contexte autorisé, par exemple uniquement le site `PAR1` en environnement `prod`. En absence de règle applicable, le comportement reste compatible avec les versions précédentes. Dès qu’une règle s’applique à un sujet ou à un rôle pour une permission donnée, toute requête hors contexte autorisé est refusée. Les règles `deny` priment sur les règles `allow`.

Exemple local :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli access create-rule \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --name worker-par1-prod \
  --permission ipam.allocate \
  --effect allow \
  --subject worker-client \
  --site-code PAR1 \
  --environment prod
PYTHONPATH=src python -m openinfra.interfaces.cli access evaluate \
  --data .openinfra.json \
  --tenant default \
  --token "$WORKER_TOKEN" \
  --permission ipam.allocate \
  --site-code PAR1 \
  --environment prod
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate \
  --data .openinfra.json \
  --tenant default \
  --auth-token "$WORKER_TOKEN" \
  --site-code PAR1 \
  --environment prod \
  --vrf default \
  --prefix 10.20.0.0/30 \
  --hostname srv-abac-01 \
  --idempotency-key req-abac-0001
```

La migration PostgreSQL `0005_access_policy_abac.sql` crée la table partitionnée `access_policy_rules`, des index GIN sur sujets/rôles/sites/environnements et un index d’audit dédié aux actions `access.policy.%`.

## Audit trail, export et intégrité chaînée

La v0.9.0 rend l’audit exploitable par les équipes exploitation, sécurité et conformité. Chaque événement est stocké avec `previous_hash` et `record_hash`, calculés en SHA-256 sur une représentation canonique de l’événement. Le chaînage permet de détecter une altération locale du journal. Les sorties API/CLI exposent uniquement les métadonnées d’audit nécessaires et ne publient aucun secret ni hash de jeton API.

Rôle dédié :

- `audit:reader` : lecture, export et vérification d’intégrité de l’audit ;
- `security:admin` : inclut aussi `audit.read` ;
- `admin` : conserve toutes les permissions.

Exemple local :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli audit list \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --limit 100
PYTHONPATH=src python -m openinfra.interfaces.cli audit export \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --format jsonl \
  --limit 500
PYTHONPATH=src python -m openinfra.interfaces.cli audit verify-integrity \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN"
```

La migration PostgreSQL `0006_audit_trail_integrity.sql` ajoute les colonnes d’intégrité à `audit_events`, les contraintes de format SHA-256 et les index nécessaires aux recherches par acteur, action, sévérité et chaîne d’intégrité.


## Environnement d’exécution Docker

Le dépôt contient un lab Docker destiné à exécuter la solution développée et à vérifier son bon fonctionnement avec PostgreSQL réel, migration, API et CLI.

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py up
python scripts/docker_environment.py validate
python scripts/docker_environment.py down
```

Le script `init` génère un `.env` local non versionné avec un mot de passe aléatoire et des permissions restrictives. Le scénario `validate` démarre le profil de validation Compose, applique les migrations via `openinfra database apply-migrations`, puis exécute des smoke tests fonctionnels contre l’API et la CLI en backend PostgreSQL. Le runbook complet est disponible dans `docs/runbooks/RUNTIME_DOCKER.md`.


## Migrations PostgreSQL

```bash
export OPENINFRA_DATABASE_DSN='postgresql://openinfra@postgres/openinfra'
PYTHONPATH=src python -m openinfra.interfaces.cli database status --root migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations --root migrations/postgresql --dry-run
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations --root migrations/postgresql
```

Le moteur applique uniquement les migrations absentes, maintient l'historique `openinfra_schema_migrations` et refuse toute divergence de checksum sur une migration déjà appliquée. `/ready` et `/api/v1/database/schema` utilisent cet état pour exposer un statut opérationnel fiable.

## Backend PostgreSQL runtime

La CLI et l’API acceptent `--backend postgresql`. Le DSN est fourni par `--postgres-dsn` ou `OPENINFRA_DATABASE_DSN`. Aucun secret n’est stocké dans le code ni dans la configuration versionnée.

```bash
export OPENINFRA_DATABASE_DSN='postgresql://openinfra@postgres/openinfra'
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate \
  --backend postgresql \
  --tenant default \
  --vrf default \
  --prefix 10.10.0.0/24 \
  --hostname srv-app-01 \
  --idempotency-key req-0001
```

L’adaptateur PostgreSQL couvre les référentiels DCIM, IPAM et audit alignés avec la migration `0001_bootstrap.sql`. Les opérations IPAM exécutent création de préfixe, contrôle d’idempotence, allocation, réservation et audit dans une seule unité de travail transactionnelle.

## Limites explicites de cette itération

Cette archive ne prétend pas livrer toute la cible Device42-like/OpenInfra GA. Elle livre un socle industriel complet et validable pour démarrer le développement, avec les premières capacités DCIM/IPAM intégrées, testées et documentées. Les modules Discovery distribuée, graphes de dépendances avancés, UI web complète, RBAC avancé, imports massifs et jobs distribués seront développés par releases successives sur ce socle.


## Source of Truth P03 : objets, relations et historique

La v0.10.0 réaligne le développement sur la roadmap REL-01/P03. Elle ajoute le référentiel Source of Truth initial : objets typés (`generic`, `device`, `interface`, `service`, `application`), attributs JSON contrôlés, tags, source d’autorité déclarée, relations typées et snapshots de versions. Chaque création ou mise à jour produit une version historisée permettant une restitution time-travel initiale.

Rôles dédiés :

- `sot:reader` : lecture des objets, relations et versions SOT ;
- `sot:operator` : lecture et écriture SOT ;
- `sot:governance-admin` : administration des règles de source autoritative ;
- `admin` : toutes les permissions.

Exemple local :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token \
  --data .openinfra.json \
  --tenant default \
  --subject sot-admin \
  --role sot:operator \
  --token "$ADMIN_TOKEN"
PYTHONPATH=src python -m openinfra.interfaces.cli sot upsert-object \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --key device/srv-001 \
  --kind device \
  --display-name "Server 001" \
  --attributes-json '{"serial":"ABC","site":"PAR1"}' \
  --tag prod \
  --tag linux \
  --source manual
PYTHONPATH=src python -m openinfra.interfaces.cli sot get-object-version \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --key device/srv-001 \
  --version 1
```

La migration PostgreSQL `0007_source_of_truth_core.sql` crée des tables partitionnées pour `source_objects`, `source_object_snapshots` et `source_relations`, avec index par type, tags, attributs JSONB, lookup historique et relations entrantes/sortantes.


## Gouvernance minimale des sources SOT

La v0.11.0 poursuit le jalon roadmap REL-01/P03 avec EPIC-0306. Le module de gouvernance empêche une source non autoritative d’écraser silencieusement des attributs certifiés du Source of Truth. Une règle définit le type d’objet concerné, le chemin d’attribut gouverné, la source autoritative, la priorité, la fraîcheur optionnelle et la stratégie de conflit.

Deux stratégies sont disponibles :

- `reject` : refuse la modification non autoritative ;
- `accept_with_audit` : accepte la modification mais retourne un conflit auditables dans l’évaluation.

Exemple local :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token \
  --data .openinfra.json \
  --tenant default \
  --subject sot-governance-admin \
  --role sot:governance-admin \
  --token "$ADMIN_TOKEN"
PYTHONPATH=src python -m openinfra.interfaces.cli sot create-governance-rule \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --name serial-from-discovery \
  --object-kind device \
  --attribute-path serial \
  --authoritative-source discovery \
  --priority 500 \
  --conflict-strategy reject
PYTHONPATH=src python -m openinfra.interfaces.cli sot evaluate-governance \
  --data .openinfra.json \
  --tenant default \
  --admin-token "$ADMIN_TOKEN" \
  --object-kind device \
  --incoming-source manual \
  --existing-attributes-json '{"serial":"ABC"}' \
  --incoming-attributes-json '{"serial":"XYZ"}'
```

La migration PostgreSQL `0008_source_governance.sql` crée la table partitionnée `source_governance_rules`, ses contraintes métier et ses index de recherche par type d’objet, chemin d’attribut, source autoritative et audit `sot.governance.%`. Les adaptateurs JSON et PostgreSQL implémentent le même port `SourceGovernanceRepository`.


## DCIM P04 : modèle physique et localisation univoque

La v0.12.0 démarre le jalon roadmap P04 avec EPIC-0401. Elle ajoute le modèle physique pays, région, ville, site, bâtiment, étage, salle et zone. Une salle déclare une grille stricte de lignes et colonnes ; une zone de salle ne peut référencer que des lignes et colonnes existantes. La localisation d’un équipement vérifie la salle, l’étage, la zone, la cellule ligne/colonne, les coordonnées X/Y/Z et les conflits de position rack/U lorsque ces informations sont fournies.

Rôle dédié :

- `dcim:operator` : création du modèle physique DCIM et localisation d’équipements ;
- `admin` : toutes les permissions.

Commandes principales :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli dcim define-room --data .openinfra.json --tenant default --site-code PAR1 --site-name "Paris Datacenter 1" --country FR --region IDF --city Paris --building-code BAT-A --building-name "Bâtiment A" --floor-code F01 --floor-name "Niveau 1" --floor-index 1 --room-code MMR1 --room-name "Salle MMR" --row A --column 01 --zone-code Z1 --zone-name "Zone critique" --zone-row A --zone-column 01
PYTHONPATH=src python -m openinfra.interfaces.cli dcim locate --data .openinfra.json --tenant default --asset-tag SRV-0001 --equipment-name "Server 0001" --site PAR1 --building BAT-A --floor F01 --room MMR1 --zone Z1 --row A --column 01 --x 1 --y 2 --z 0
```

La migration PostgreSQL `0009_dcim_physical_model.sql` étend le schéma DCIM avec `floors`, `room_zones`, `sites.region`, `rooms.floor_code`, `rooms.zone_codes`, coordonnées X/Y/Z, `racks.floor_code`, `racks.zone_code`, `equipment.floor_code` et `equipment.zone_code`. Les adaptateurs JSON et PostgreSQL implémentent le même port `DcimRepository`.
