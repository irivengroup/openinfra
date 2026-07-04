# OpenInfra Python Foundation

**Version courante : 0.28.0 — Registry collectors et identité forte P07 / EPIC-0701.**


## Registry collectors et identité forte P07 / EPIC-0701

La version `0.28.0` démarre le chantier Discovery P07 avec un registre de collectors exploitable en production. Chaque collector dispose d'une identité forte représentée par l'empreinte SHA-256 de son certificat mTLS, d'un type technique, d'une version déclarée, de scopes autorisés et d'une référence Vault pour ses secrets. OpenInfra ne stocke pas de secret en clair : seul le pointeur `vault://...` est persistant.

Contrats exposés :

- CLI : `openinfra discovery collector-register`, `collector-heartbeat`, `job-authorize`, `collector-disable`, `collector-list` ;
- API : `POST /api/v1/discovery/collectors`, `GET /api/v1/discovery/collectors`, `POST /api/v1/discovery/collectors/heartbeat`, `POST /api/v1/discovery/jobs/authorize`, `POST /api/v1/discovery/collectors/disable` ;
- sécurité : l'enregistrement, la désactivation et la consultation nécessitent `security.admin` ; l'autorisation de job s'appuie sur l'identité collector et ne délivre aucun travail si le collector est inconnu, désactivé, hors scope ou présenté avec une empreinte différente ;
- observabilité : les événements `discovery.collector.registered`, `discovery.collector.heartbeat`, `discovery.job.authorized`, `discovery.job.rejected` et `discovery.collector.disabled` sont audités.

Exemple CLI minimal :

```bash
tmpdir="$(mktemp -d)"
token="$(python -c 'print("d" * 40)')"
fingerprint="$(python -c 'print("a" * 64)')"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token --data "$tmpdir/state.json" --tenant default --subject discovery-admin --role security:admin --token "$token" >/dev/null
PYTHONPATH=src python -m openinfra.interfaces.cli discovery collector-register --data "$tmpdir/state.json" --tenant default --actor discovery-admin --admin-token "$token" --name par1-snmp-collector --kind snmp --certificate-fingerprint "$fingerprint" --scope site/par1 --version 1.0.0 --vault-secret-ref vault://openinfra/discovery/snmp/par1
PYTHONPATH=src python -m openinfra.interfaces.cli discovery collector-heartbeat --data "$tmpdir/state.json" --tenant default --collector-id "<collector_id>" --certificate-fingerprint "$fingerprint" --version 1.0.1 --status healthy
PYTHONPATH=src python -m openinfra.interfaces.cli discovery job-authorize --data "$tmpdir/state.json" --tenant default --collector-id "<collector_id>" --certificate-fingerprint "$fingerprint" --requested-scope site/par1 --job-type snmp-scan --target 10.0.0.10
```



## Migration depuis référentiels existants P06 / EPIC-0604

La version `0.27.1` corrigeait le faux positif de sécurité CI Bandit sur l’état JSON des exports signés, sans changer le périmètre fonctionnel livré en `0.27.0`. La version `0.27.0` ajoute une couche de migration contrôlée depuis les référentiels existants. Elle ne charge pas directement les données legacy en production : elle produit d’abord un plan de migration en dry-run, avec mapping effectif, rapport d’impact, lignes invalides, gaps bloquants ou non bloquants et stratégie de reprise. Les sources initiales couvertes sont Device42, NetBox, Nautobot, GLPI et CSV générique.

Contrats exposés :

- CLI : `openinfra import migration-template`, `openinfra import migration-plan`, `openinfra import migration-report` ;
- API : `GET /api/v1/imports/migration-template`, `POST /api/v1/imports/migration-plans`, `GET /api/v1/imports/migration-report` ;
- formats : CSV, JSON et XLSX via le parseur d’import existant ;
- cible initiale : Source of Truth `source_objects` ;
- sécurité : contrôle `sot.write`, aucun secret en clair, aucun effet de bord en simulation.

Exemple CLI minimal :

```bash
tmpdir="$(mktemp -d)"
token="$(python -c 'print("m" * 40)')"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token --data "$tmpdir/state.json" --tenant default --subject migration-admin --role sot:operator --token "$token" >/dev/null
printf 'name,serial,status,site,rack\nnetbox-device-001,SN-NB-001,active,dc-paris,rack-a01\n' > "$tmpdir/netbox.csv"
PYTHONPATH=src python -m openinfra.interfaces.cli import migration-template --data "$tmpdir/state.json" --source netbox
PYTHONPATH=src python -m openinfra.interfaces.cli import migration-plan --data "$tmpdir/state.json" --tenant default --admin-token "$token" --source netbox --file "$tmpdir/netbox.csv" --format csv
PYTHONPATH=src python -m openinfra.interfaces.cli import migration-report --data "$tmpdir/state.json" --tenant default --job-id "<job_id>"
```

## Exports asynchrones et signés P06 / EPIC-0603

La version `0.26.0` a ajouté un cycle d’export exploitable en production : la demande d’export est non bloquante, l’exécution est portée par une action worker explicite, l’artefact est persisté, son digest SHA-256 est enregistré et son contenu est signé en HMAC-SHA256 par une clé managée par le backend. Le téléchargement vérifie systématiquement le digest et la signature avant de restituer le fichier.

Contrats exposés :

- CLI : `openinfra export request`, `openinfra export run`, `openinfra export report`, `openinfra export artifact` ;
- API : `POST /api/v1/exports/jobs`, `GET /api/v1/exports/jobs`, `POST /api/v1/exports/run`, `GET /api/v1/exports/artifact` ;
- formats : CSV, JSON et XLSX ;
- ressource initiale : `source_objects` avec filtres `kind`, `tag` et `limit`.

Exemple CLI minimal :

```bash
tmpdir="$(mktemp -d)"
token="$(python -c 'print("x" * 40)')"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token --data "$tmpdir/state.json" --tenant default --subject export-admin --role sot:operator --role audit:reader --token "$token" >/dev/null
PYTHONPATH=src python -m openinfra.interfaces.cli sot upsert-object --data "$tmpdir/state.json" --tenant default --admin-token "$token" --key device/export-001 --kind device --display-name "Export 001" --attributes-json '{"serial":"EXPORT-001"}' --tag prod --source export-smoke >/dev/null
PYTHONPATH=src python -m openinfra.interfaces.cli export request --data "$tmpdir/state.json" --tenant default --admin-token "$token" --format json --tag prod
PYTHONPATH=src python -m openinfra.interfaces.cli export run --data "$tmpdir/state.json" --tenant default --admin-token "$token"
PYTHONPATH=src python -m openinfra.interfaces.cli export report --data "$tmpdir/state.json" --tenant default --admin-token "$token" --job-id "<job_id>"
PYTHONPATH=src python -m openinfra.interfaces.cli export artifact --data "$tmpdir/state.json" --tenant default --admin-token "$token" --job-id "<job_id>" --output "$tmpdir/export.json"
```

## Correctif v0.25.1

La version `0.25.1` est une livraison corrective CI/DevSecOps du jalon `0.25.0`. Elle conserve l'import massif scalable et corrige les échecs Ruff/Bandit/MyPy signalés par la CI Python 3.12 : formatage, parsing XML XLSX sécurisé via `defusedxml`, typage des rapports bulk et garde-fous associés. Aucun endpoint, commande CLI ou comportement métier du jalon `0.25.0` n'est supprimé.

OpenInfra est un socle Python orienté objet pour construire une solution open source de Source of Truth, DCIM, ITAM, Discovery, Dependency Mapping et IPAM Enterprise++ sans fonction ITSM intégrée.

Cette livraison correspond au socle exécutable aligné avec la roadmap P01/P02 puis REL-01/P03/P04/P05/P06 : architecture hexagonale, modèle domaine, CLI, API HTTP standard library, migrations PostgreSQL applicatives, adaptateur PostgreSQL runtime, sécurité API par jetons hachés avec expiration, révocation et rotation, IAM utilisateurs/groupes avec rôles effectifs, ABAC contextuel site/environnement, audit trail consultable/exportable avec intégrité chaînée, Source of Truth P03 objets/relations/historique, gouvernance minimale des sources autoritatives, DCIM P04 modèle physique pays/région/ville/site/bâtiment/étage/salle/zone/grille, racks, QR terrain, plans 2D et rack elevation, IPAM P05 modèle IPv4/IPv6/VRF, allocation transactionnelle, fondation réseau VLAN/VXLAN/ASN/BGP et intégration DDI baseline, puis P06 import générique CSV/JSON/XLSX avec mapping, dry-run, rapport d’impact, DLQ et import massif scalable par streaming CSV, batches bornés, checkpoints et reprise, puis exports asynchrones signés avec artefacts vérifiés avant téléchargement, et migration depuis référentiels legacy avec templates Device42/NetBox/Nautobot/GLPI/CSV, dry-run et rapport d’écarts persisté, puis registre de collectors Discovery avec identité forte, scopes, heartbeat et autorisation de jobs. Le runtime production reste natif serveur Linux + virtualenv + systemd + PostgreSQL ; Docker reste uniquement un lab/smoke/test facultatif.

## Garanties de cette itération

- Code produit en Python POO : les comportements sont portés par des classes de domaine, services applicatifs, ports et adaptateurs.
- Séparation stricte `domain / application / infrastructure / interfaces`.
- Localisation DCIM univoque : pays, région, ville, site, bâtiment, étage, salle, zone, ligne, colonne, coordonnées X/Y/Z facultatives, rack, face, unité U, plan 2D salle et rack elevation.
- IPAM IPv4/IPv6 : VRF, agrégats, préfixes, plages, adresses suivies, capacité de préfixe, allocation transactionnelle next-available, idempotence par clé métier, plages d’allocation/exclusion/réservation, verrouillage fin PostgreSQL, détection de chevauchement par VRF, UI IPAM opérationnelle, recherche IP/hostname, assistant de réservation, prévisualisation DDI DNS/DHCP avec divergences et rollback compensatoire, VLAN groups, VLAN, VNI/VXLAN, ASN, pairs BGP et route targets.
- Persistance locale JSON atomique pour développement et tests reproductibles.
- Persistance PostgreSQL runtime optionnelle via `psycopg`, DSN explicite et transactions courtes.
- Migration PostgreSQL initiale avec tables partitionnées, index, contraintes et audit append-only.
- Moteur de migrations PostgreSQL applicatif : statut, dry-run, application idempotente, historique `openinfra_schema_migrations` et checksum SHA-256.
- CLI exploitable : `openinfra version`, `openinfra spec validate`, `openinfra dcim define-room`, `openinfra dcim locate`, `openinfra dcim define-rack`, `openinfra dcim rack-capacity`, `openinfra dcim locator-sheet`, `openinfra dcim verify-scan`, `openinfra dcim room-plan`, `openinfra dcim rack-elevation`, `openinfra ipam define-vrf`, `openinfra ipam define-aggregate`, `openinfra ipam define-prefix`, `openinfra ipam define-range`, `openinfra ipam register-address`, `openinfra ipam list-prefixes`, `openinfra ipam capacity`, `openinfra ipam allocate`, `openinfra ipam define-vlan-group`, `openinfra ipam define-vxlan-vni`, `openinfra ipam define-vlan`, `openinfra ipam define-asn`, `openinfra ipam define-bgp-peer`, `openinfra ipam network-bindings`, `openinfra ipam observe-dns`, `openinfra ipam observe-dhcp-lease`, `openinfra ipam detect-conflicts`, `openinfra ipam ui-dashboard`, `openinfra ipam ui-search`, `openinfra ipam reservation-wizard`, `openinfra ipam ddi-preview`, `openinfra security bootstrap-token`, `openinfra security whoami`, `openinfra security list-tokens`, `openinfra security revoke-token`, `openinfra security rotate-token`, `openinfra identity create-user`, `openinfra identity create-group`, `openinfra identity add-user-to-group`, `openinfra identity grant-user-role`, `openinfra identity grant-group-role`, `openinfra identity effective`, `openinfra access create-rule`, `openinfra access list-rules`, `openinfra access evaluate`, `openinfra access deactivate-rule`, `openinfra audit list`, `openinfra audit export`, `openinfra audit verify-integrity`, `openinfra sot upsert-object`, `openinfra sot get-object`, `openinfra sot list-objects`, `openinfra sot get-object-version`, `openinfra sot create-relation`, `openinfra sot list-relations`, `openinfra sot create-governance-rule`, `openinfra sot list-governance-rules`, `openinfra sot evaluate-governance`, `openinfra sot deactivate-governance-rule`, `openinfra database render-migration`, `openinfra database status`, `openinfra database apply-migrations`, `openinfra import dataset`, `openinfra import report`, `openinfra import bulk-dataset`, `openinfra import bulk-report`, `openinfra import bulk-checkpoint`, `openinfra import migration-template`, `openinfra import migration-plan`, `openinfra import migration-report`, `openinfra export request`, `openinfra export run`, `openinfra export report`, `openinfra export artifact`, `openinfra discovery collector-register`, `openinfra discovery collector-heartbeat`, `openinfra discovery job-authorize`, `openinfra discovery collector-disable`, `openinfra discovery collector-list`.
- API HTTP légère : `/`, `/api/v1`, `/health`, `/ready`, `/api/v1/version`, `/api/v1/database/schema`, `/api/v1/security/whoami`, `/api/v1/security/tokens`, `/api/v1/security/revoke-token`, `/api/v1/security/rotate-token`, `/api/v1/identity/users`, `/api/v1/identity/groups`, `/api/v1/identity/group-memberships`, `/api/v1/identity/user-roles`, `/api/v1/identity/group-roles`, `/api/v1/identity/effective`, `/api/v1/access/rules`, `/api/v1/access/evaluate`, `/api/v1/access/deactivate-rule`, `/api/v1/audit/events`, `/api/v1/audit/export`, `/api/v1/audit/integrity`, `/api/v1/sot/objects`, `/api/v1/sot/object-versions`, `/api/v1/sot/relations`, `/api/v1/sot/governance-rules`, `/api/v1/sot/governance/evaluate`, `/api/v1/sot/governance/deactivate-rule`, `/api/v1/ipam/vrfs`, `/api/v1/ipam/aggregates`, `/api/v1/ipam/prefixes`, `/api/v1/ipam/ranges`, `/api/v1/ipam/addresses`, `/api/v1/ipam/capacity`, `/api/v1/ipam/allocate`, `/api/v1/ipam/vlan-groups`, `/api/v1/ipam/vxlan-vnis`, `/api/v1/ipam/vlans`, `/api/v1/ipam/asns`, `/api/v1/ipam/bgp-peers`, `/api/v1/ipam/network-bindings`, `/api/v1/ipam/conflicts`, `/api/v1/ipam/ui-dashboard`, `/api/v1/ipam/ui-search`, `/api/v1/ipam/reservation-wizard`, `/api/v1/ipam/ddi-preview`, `/api/v1/imports/datasets`, `/api/v1/imports/report`, `/api/v1/imports/bulk-datasets`, `/api/v1/imports/bulk-report`, `/api/v1/imports/bulk-checkpoint`, `/api/v1/imports/migration-template`, `/api/v1/imports/migration-plans`, `/api/v1/imports/migration-report`, `/api/v1/exports/jobs`, `/api/v1/exports/run`, `/api/v1/exports/artifact`, `/docs`, `/swagger`, `/redoc`, `/openapi.yaml`, `/api/v1/openapi.yaml`, `/ui/ipam`, `/api/v1/dcim/rooms`, `/api/v1/dcim/racks`, `/api/v1/dcim/rack-capacity`, `/api/v1/dcim/locator-sheet`, `/api/v1/dcim/verify-scan`, `/api/v1/dcim/room-plan`, `/api/v1/dcim/rack-elevation`.
- GitHub Actions complète : format, lint, types, tests, couverture, sécurité, build, smoke tests CLI/API et runtime serveur natif et lab Docker authentifié facultatif.



## Import massif scalable P06 / EPIC-0602

La version `0.25.0` a introduit un mode d’import massif distinct de l’import générique atomique livré en `0.24.0`. Ce mode est conçu pour les gros fichiers opérationnels : lecture CSV en streaming, traitement par batches bornés, checkpoint persistant, reprise par `job_id`, métriques d’exécution, échantillons d’impact et DLQ limitée afin de ne pas charger l’intégralité du dataset en mémoire.

Le contrat est volontairement explicite :

- le mode bulk lit le flux ligne par ligne ;
- `--batch-size` borne la taille des écritures ;
- `--checkpoint-interval` force la persistance périodique de l’avancement ;
- `--resume-job-id` reprend après le dernier checkpoint connu ;
- les lignes invalides sont reportées en DLQ avec numéro de ligne et cause ;
- le backend JSON expose une stratégie `json-streaming-batch-checkpoint` ;
- le backend PostgreSQL expose une stratégie `postgresql-bounded-batch-copy-eligible`.

Exemple CLI bulk en dry-run :

```bash
tmpdir="$(mktemp -d)"
token="$(python - <<'PY'
print("b" * 40)
PY
)"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token --data "$tmpdir/state.json" --tenant default --subject bulk-import-admin --role sot:operator --token "$token" >/dev/null
printf 'asset_key,kind,name,source,serial\ndevice/bulk-001,device,Bulk 001,csv_import,SN001\ndevice/bulk-002,device,Bulk 002,csv_import,SN002\n' > "$tmpdir/bulk.csv"
PYTHONPATH=src python -m openinfra.interfaces.cli import bulk-dataset \
  --data "$tmpdir/state.json" \
  --tenant default \
  --actor bulk-import-admin \
  --admin-token "$token" \
  --file "$tmpdir/bulk.csv" \
  --format csv \
  --mapping-json '{"key":"asset_key","kind":"kind","display_name":"name","source":"source","attributes.serial":"serial"}' \
  --batch-size 1000 \
  --checkpoint-interval 1000
```

Les commandes `openinfra import bulk-report --tenant default --job-id <uuid>` et `openinfra import bulk-checkpoint --tenant default --job-id <uuid>` relisent respectivement le rapport et le checkpoint persistés. L’API expose les mêmes contrats avec `POST /api/v1/imports/bulk-datasets`, `GET /api/v1/imports/bulk-report` et `GET /api/v1/imports/bulk-checkpoint`.

## Import framework générique P06 / EPIC-0601

La version `0.24.0` introduit un framework d’import générique exploitable pour alimenter la Source of Truth depuis des jeux de données CSV, JSON ou XLSX. L’import ne modifie jamais les données en dry-run et applique les écritures uniquement si toutes les lignes sont valides. En cas d’erreur, le rapport contient une DLQ, ou Dead Letter Queue, c’est-à-dire la liste exploitable des lignes rejetées avec leur numéro, leur champ et la cause précise du rejet.

Exemple CLI en dry-run :

```bash
tmpdir="$(mktemp -d)"
token="$(python - <<'PY'
print("i" * 40)
PY
)"
PYTHONPATH=src python -m openinfra.interfaces.cli security bootstrap-token --data "$tmpdir/state.json" --tenant default --subject import-admin --role sot:operator --token "$token" >/dev/null
printf 'asset_key,kind,name,source,serial\ndevice/srv-001,device,Server 001,csv_import,SN001\n' > "$tmpdir/devices.csv"
PYTHONPATH=src python -m openinfra.interfaces.cli import dataset \
  --data "$tmpdir/state.json" \
  --tenant default \
  --actor import-admin \
  --admin-token "$token" \
  --file "$tmpdir/devices.csv" \
  --format csv \
  --mapping-json '{"key":"asset_key","kind":"kind","display_name":"name","source":"source","attributes.serial":"serial"}'
```

Pour appliquer réellement l’import, ajouter `--apply`. La commande `openinfra import report --tenant default --job-id <uuid>` relit le rapport persisté. L’API expose les mêmes contrats avec `POST /api/v1/imports/datasets` et `GET /api/v1/imports/report`.

## Point d’entrée API

`GET /` retourne un document JSON de découverte du service au lieu d’une erreur `not_found`. Cette réponse permet de confirmer rapidement que le conteneur API répond correctement depuis un navigateur ou depuis `curl` :

```json
{
  "service": "openinfra-api",
  "status": "ok",
  "health": "/health",
  "readiness": "/ready",
  "api": {
    "version": "v1",
    "base_path": "/api/v1",
    "version_url": "/api/v1/version",
    "schema_url": "/api/v1/database/schema",
    "openapi_url": "/openapi.yaml"
  },
  "documentation": {
    "swagger_ui": "/docs",
    "swagger_alias": "/swagger",
    "redoc": "/redoc",
    "openapi_yaml": "/openapi.yaml",
    "versioned_openapi_yaml": "/api/v1/openapi.yaml"
  }
}
```

`GET /api/v1` expose le même document d’entrée pour la version courante de l’API. Le document inclut aussi les liens de documentation : Swagger UI sur `/docs`, alias Swagger sur `/swagger`, ReDoc sur `/redoc`, contrat OpenAPI YAML sur `/openapi.yaml` et alias versionné sur `/api/v1/openapi.yaml`. Au démarrage, `openinfra-api` écrit aussi un événement JSON `openinfra_api_started` sur stdout, visible via `docker logs openinfra-api` dans le lab Docker.

## Installation développeur

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install --requirement requirements/dev.txt
# Avec backend PostgreSQL runtime :
python -m pip install -e '.[postgresql]'
python -m pip install --requirement requirements/dev.txt
```

## Commandes de validation

```bash
python scripts/quality_gate.py
python -m pytest
python -m openinfra.interfaces.cli version
python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
python -m compileall -q src tests scripts docker
```

Lorsque les outils de qualité sont installés :

```bash
ruff format --check src tests scripts docker
ruff check src tests scripts docker
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
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vrf \
  --data .openinfra.json \
  --tenant default \
  --name prod \
  --route-distinguisher 65000:1
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-aggregate \
  --data .openinfra.json \
  --tenant default \
  --vrf prod \
  --cidr 10.0.0.0/8
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-prefix \
  --data .openinfra.json \
  --tenant default \
  --vrf prod \
  --cidr 10.10.0.0/24
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-range \
  --data .openinfra.json \
  --tenant default \
  --vrf prod \
  --prefix 10.10.0.0/24 \
  --start 10.10.0.10 \
  --end 10.10.0.200
PYTHONPATH=src python -m openinfra.interfaces.cli ipam allocate \
  --data .openinfra.json \
  --tenant default \
  --vrf prod \
  --prefix 10.10.0.0/24 \
  --hostname srv-app-01 \
  --idempotency-key req-0001
PYTHONPATH=src python -m openinfra.interfaces.cli ipam capacity \
  --data .openinfra.json \
  --tenant default \
  --vrf prod \
  --prefix 10.10.0.0/24
```


## Exemple DDI preview IPAM

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli ipam ddi-preview \
  --data .openinfra.json \
  --tenant default \
  --vrf prod \
  --idempotency-key req-0001 \
  --provider all \
  --dns-zone example.net \
  --mac-address aa:bb:cc:00:00:01
```

La commande ne contacte aucun service externe par défaut : elle produit un plan déterministe BIND/PowerDNS/Kea, les divergences détectées depuis les observations DNS/DHCP connues et les changements compensatoires à appliquer en rollback.

## Exemple IPAM réseau VLAN/VXLAN/BGP

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vlan-group \
  --data .openinfra.json --tenant default --name fabric --scope dc1 --description "Fabric DC1"
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vxlan-vni \
  --data .openinfra.json --tenant default --vni 100100 --name prod-servers --vrf prod \
  --route-target-import 65000:100 --route-target-export 65000:100
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-vlan \
  --data .openinfra.json --tenant default --group fabric --vlan-id 100 --name servers \
  --vrf prod --vni 100100
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-asn \
  --data .openinfra.json --tenant default --asn 65000 --name local-fabric
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-asn \
  --data .openinfra.json --tenant default --asn 65100 --name upstream
PYTHONPATH=src python -m openinfra.interfaces.cli ipam define-bgp-peer \
  --data .openinfra.json --tenant default --vrf prod --local-asn 65000 \
  --remote-asn 65100 --peer-address 192.0.2.1 --route-target-import 65000:100
PYTHONPATH=src python -m openinfra.interfaces.cli ipam network-bindings \
  --data .openinfra.json --tenant default --vrf prod
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
print("oi_" + secrets.token_urlsafe(48))
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

Les commandes `revoke-token` et `rotate-token` permettent de retirer un jeton compromis ou de remplacer un jeton administrateur sans exposer de hash ni secret en sortie. En backend PostgreSQL, les commandes acceptent `--backend postgresql` et `--postgres-dsn`, ou utilisent `OPENINFRA_DATABASE_DSN`. Le runtime natif de production s’appuie sur `systemd`, un virtualenv Python et PostgreSQL. Le lab Docker facultatif applique les migrations, crée un jeton d’amorçage depuis le `.env` local généré et lance l’API avec authentification obligatoire pour les tests.


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


## v0.14.0 — P04 EPIC-0403 QR codes et chemins d’intervention

La v0.14.0 poursuit le jalon roadmap P04 avec EPIC-0403. Elle ajoute l’identification terrain des équipements : génération d’un payload QR compact, fiche de localisation JSON ou HTML, chemin d’intervention humain depuis le site jusqu’au rack/U, et vérification auditée d’un scan QR.

Commandes principales :

```bash
openinfra dcim locator-sheet \
  --tenant default \
  --asset-tag SRV-001 \
  --format json

openinfra dcim verify-scan \
  --tenant default \
  --asset-tag SRV-001 \
  --payload "oi:loc:<payload>"
```

API ajoutées :

- `GET /api/v1/dcim/locator-sheet` : retourne la fiche terrain en JSON ou HTML encapsulé ;
- `POST /api/v1/dcim/verify-scan` : vérifie la preuve de scan et journalise l’opération.

Qualité : le seuil de couverture global de la CI passe désormais à `>= 98 %`. Les tests ajoutés couvrent le domaine QR, le service terrain, la CLI, l’API HTTP, les contrats d’erreur, les magasins JSON et les validations métier.


## v0.15.0 — P04 EPIC-0404 Plans 2D salle et rack elevation

La v0.15.0 poursuit strictement le jalon roadmap P04 avec EPIC-0404. Elle ajoute une visualisation terrain déterministe sans dépendance graphique lourde : plan 2D de salle par grille ligne/colonne, cellules occupées par rack ou équipement au sol, rendu SVG/HTML lisible, rack elevation par face avec unités U libres/occupées et audit des rendus. La localisation ligne/colonne/X/Y/Z, rack, face et U reste inchangée et rétrocompatible.

Commandes principales :

```bash
openinfra dcim room-plan \
  --tenant default \
  --site PAR1 \
  --building BAT-A \
  --room MMR1 \
  --format json

openinfra dcim rack-elevation \
  --tenant default \
  --site PAR1 \
  --building BAT-A \
  --room MMR1 \
  --rack R01 \
  --face front \
  --format html
```

API ajoutées :

- `GET /api/v1/dcim/room-plan` : retourne le plan 2D en JSON ou un rendu SVG/HTML encapsulé ;
- `GET /api/v1/dcim/rack-elevation` : retourne l’occupation verticale d’une face rack en JSON ou un rendu SVG/HTML encapsulé.

La migration PostgreSQL `0012_dcim_visualization_indexes.sql` ajoute des index de lecture pour les plans salle, les rack elevations et les événements d’audit `dcim.room-plan.rendered` / `dcim.rack-elevation.rendered`. La CI rend désormais les migrations `0001` à `0012` et le smoke Docker couvre les endpoints de visualisation.


## v0.16.0 — P04 EPIC-0405 Câblage DCIM fondation

La v0.16.0 poursuit strictement le jalon roadmap P04 avec EPIC-0405. Elle ajoute la fondation de câblage DCIM : panneaux de brassage montés en rack, ports DCIM attachés aux équipements ou aux panneaux, câbles point-à-point, validation de compatibilité connecteur/média, prévention des conflits d’endpoint actif et trace humaine du chemin de câble. Les localisations existantes ligne/colonne/X/Y/Z, rack, face et U restent préservées.

Commandes principales :

```bash
openinfra dcim define-patch-panel --tenant default --site PAR1 --building BAT-A --room MMR1 --rack R01 --patch-panel PP01 --rack-face front --u-position 2 --port-count 24 --connector rj45 --medium copper
openinfra dcim define-port --tenant default --owner-type equipment --owner-code SRV-001 --port-name ETH0 --connector rj45 --medium copper
openinfra dcim connect-cable --tenant default --cable-id CAB-0001 --a-owner-type equipment --a-owner-code SRV-001 --a-port-name ETH0 --b-owner-type patch_panel --b-owner-code PP01 --b-port-name P01 --medium copper --path "Rack R01" --path "Patch panel PP01"
openinfra dcim cable-trace --tenant default --cable-id CAB-0001
```

API ajoutées :

- `POST /api/v1/dcim/patch-panels` : crée un panneau de brassage racké et génère ses ports ;
- `POST /api/v1/dcim/ports` : crée un port DCIM pour équipement ou panneau ;
- `POST /api/v1/dcim/cables` : connecte deux ports compatibles ;
- `GET /api/v1/dcim/cable-trace` : retourne la trace humaine du câble et ses deux endpoints.

La migration PostgreSQL `0013_dcim_cabling_foundation.sql` ajoute les tables partitionnées `dcim_patch_panels`, `dcim_ports` et `dcim_cables`, ainsi que les index actifs par endpoint et les index d’audit `dcim.patch-panel.defined`, `dcim.port.defined`, `dcim.cable.connected` et `dcim.cable.traced`.

Production : le runtime officiel est désormais documenté comme déploiement serveur natif via `systemd`, virtualenv Python et PostgreSQL. Docker reste un lab optionnel de test/smoke et n’est pas une dépendance de production.


## v0.17.6 — Correctif CI Python 3.13 génération de jetons

La v0.17.6 est une livraison corrective sans nouveau jalon métier. Elle corrige l'échec GitHub Actions observé sur Python 3.13 lorsque `secrets.token_urlsafe(48)` générait occasionnellement une valeur commençant par `-`. Dans ce cas, l'appel shell `--token "$token"` pouvait être interprété par `argparse` comme une option manquante au lieu d'une valeur de jeton.

Corrections intégrées :

- tous les jetons générés dans `.github/workflows/ci.yml` sont préfixés par `ci_` ;
- les jetons applicatifs générés automatiquement par OpenInfra sont préfixés par `oi_` ;
- les scripts de smoke/lab facultatifs génèrent également des jetons préfixés ;
- `scripts/security_gate.py` refuse la réintroduction d'une génération CI non préfixée ;
- les tests valident que les jetons générés ne commencent jamais par `-`.

Cette correction ne modifie pas la compatibilité des jetons existants : les jetons déjà créés restent authentifiés par leur hash stocké.

## v0.17.5 — Correctif CI Dependency Review non exécutée sur push

La v0.17.5 est une livraison corrective sans nouveau jalon métier. Elle corrige l'affichage GitHub Actions `Dependency review / PR vulnerability gate (push) Skipped` en séparant les responsabilités CI :

- `.github/workflows/ci.yml` reste déclenché sur `push`, pull request, tag `v*` et lancement manuel ; il contient les contrôles bloquants de vulnérabilités applicables aux pushs : `bandit`, `pip-audit`, `security_gate.py`, CodeQL et la matrice Python `3.11` à `3.14` ;
- `.github/workflows/dependency-review.yml` est désormais un workflow séparé, déclenché uniquement par `pull_request`, car la revue différentielle des dépendances est un contrôle de PR ;
- aucun job PR-only n'est conservé dans le workflow de push, ce qui évite les checks `Skipped` sur push ;
- `scripts/security_gate.py` bloque toute régression réintroduisant `actions/dependency-review-action` ou `if: github.event_name == 'pull_request'` dans le workflow de push.

Checks requis conseillés :

- sur `push` / branches protégées : `Quality / Python 3.11`, `Quality / Python 3.12`, `Quality / Python 3.13`, `Quality / Python 3.14`, `Blocking push vulnerability gate / Python 3.11`, `Blocking push vulnerability gate / Python 3.12`, `Blocking push vulnerability gate / Python 3.13`, `Blocking push vulnerability gate / Python 3.14`, `CodeQL security analysis` ;
- sur pull request : ajouter `Dependency review / PR vulnerability gate`.

## v0.17.4 — Correctif CI audit vulnérabilités editable

La v0.17.4 est une livraison corrective sans nouveau jalon métier. Elle corrige l'échec GitHub Actions `distribution marked as editable` rencontré par `pip-audit` lorsque l'environnement CI contient le package projet installé en mode editable.

Le job sécurité bloquant n'audite plus l'environnement Python complet. Il exécute désormais :

```bash
python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off
```

Les fichiers `requirements/runtime.txt`, `requirements/postgresql.txt` et `requirements/dev.txt` séparent les dépendances production et dev/CI. `requirements/security-audit.txt` agrège explicitement ces fichiers pour auditer uniquement des dépendances tierces. Le package projet local est volontairement exclu, car il n'est pas une dépendance PyPI tierce et ne doit pas être résolu comme telle pendant l'audit de vulnérabilités.

## v0.17.3 — Correctif CI audit vulnérabilités et runtime PostgreSQL

La v0.17.3 est une livraison corrective sans nouveau jalon métier. Elle corrige le runtime PostgreSQL et initie la correction de l'audit GitHub Actions lié au package projet installé en editable. La v0.17.4 finalise cette correction en passant à un fichier d'audit dédié aux dépendances tierces.

Correction PostgreSQL runtime :

- `PostgreSQLDriver.connect()` encapsule les échecs de connexion réels de `psycopg` en `OpenInfraError` ;
- les erreurs DNS, réseau, serveur absent ou refus de connexion sont désormais reportées proprement par l'abstraction OpenInfra.

Le runtime de production reste serveur natif : virtualenv Python, `systemd` et PostgreSQL. Docker demeure uniquement un environnement facultatif de test/smoke local.

## v0.17.2 — Correctif CI sécurité bloquante

La v0.17.2 est une livraison corrective sans nouveau jalon métier. Elle renforce la CI pour que les contrôles sécurité soient réellement bloquants après un `push` et corrige le smoke RBAC qui utilisait un jeton `ipam:operator` pour des opérations d'administration de tokens.

Chaîne CI renforcée :

- matrice Python `3.11`, `3.12`, `3.13` et `3.14` ;
- job `blocking-security` exécuté sur `push`, pull request, tag `v*` et lancement manuel ;
- `bandit -q -r src/openinfra` pour l'analyse statique sécurité Python ;
- `python -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off` pour bloquer les dépendances connues vulnérables ;
- `scripts/security_gate.py` pour détecter des secrets committés et vérifier le durcissement workflow ;
- CodeQL avec les suites `security-extended` et `security-and-quality` ;
- `dependency-review-action` sur pull requests ;
- Dependabot pour `pip` et `github-actions`.

Correction RBAC CI :

```bash
openinfra security bootstrap-token --subject ci-security-admin --role security:admin --token "$security_admin_token"
openinfra security list-tokens --admin-token "$security_admin_token"
openinfra security revoke-token --target-token "$worker_token" --admin-token "$security_admin_token"
```

Le runtime de production reste serveur natif : virtualenv Python, `systemd` et PostgreSQL. Docker demeure uniquement un environnement facultatif de test/smoke local.

## v0.17.0 — P04 EPIC-0406 Énergie et refroidissement DCIM

La v0.17.0 poursuit strictement le jalon roadmap P04 avec la fondation énergie/refroidissement. Elle permet de déclarer des PDU/UPS, circuits A/B, zones de refroidissement, réservations de puissance par équipement et rapports de capacité rack. Les contrôles applicatifs empêchent la surallocation des sources électriques, circuits, capacités déclarées du rack et zones froides/chaudes.

Exemples CLI :

```bash
openinfra dcim define-power-device --data .openinfra.json --tenant default \
  --code PDU-A --kind pdu --site PAR1 --building BAT-A --room MMR1 \
  --rack R01 --side A --capacity-watts 8000 --derating-percent 80

openinfra dcim define-power-circuit --data .openinfra.json --tenant default \
  --circuit-id CIR-A-01 --source-device PDU-A --site PAR1 --building BAT-A \
  --room MMR1 --rack R01 --side A --capacity-watts 4000 --breaker-rating-amps 16

openinfra dcim define-cooling-zone --data .openinfra.json --tenant default \
  --site PAR1 --building BAT-A --room MMR1 --zone Z1 --role cold_aisle \
  --cooling-capacity-watts 12000 --supply-temperature-c 18 --return-temperature-c 30

openinfra dcim reserve-power --data .openinfra.json --tenant default \
  --asset-tag SRV-001 --circuit-id CIR-A-01 --expected-watts 1200

openinfra dcim energy-cooling-capacity --data .openinfra.json --tenant default \
  --site PAR1 --building BAT-A --room MMR1 --rack R01
```

Correction CI : `.github/workflows/ci.yml` déclenche désormais les validations sur toutes les branches en `push`, toutes les pull requests et en lancement manuel. L’ancien verrouillage sur `main` pouvait empêcher l’exécution après un push sur `master`, `develop` ou une branche de fonctionnalité.

## v0.21.0 — P05 / EPIC-0504 Détection conflits IPAM

OpenInfra ajoute un moteur de détection de conflits IPAM auditable couvrant les chevauchements de préfixes et de plages, les doublons d'adresses, les leases DHCP observés en conflit avec la source de vérité, les adresses observées hors préfixe géré et les divergences DNS/PTR. Les observations DNS et DHCP peuvent être ingérées par CLI/API, puis analysées par tenant et VRF avec un rapport typé, sévérité, preuves et action recommandée.

Commandes principales :

```bash
openinfra ipam observe-dns --tenant default --vrf prod --hostname srv.example.net --address 10.0.0.10 --ptr-hostname old.example.net
openinfra ipam observe-dhcp-lease --tenant default --vrf prod --prefix 10.0.0.0/24 --address 10.0.0.10 --mac-address aa:bb:cc:00:00:10 --hostname rogue
openinfra ipam detect-conflicts --tenant default --vrf prod
```



## v0.22.2 — Correctif runtime Docker/PostgreSQL

La version 0.22.2 corrige l’exécution Docker Compose de la livraison v0.22.0 : les migrations PostgreSQL n’utilisent plus la colonne inexistante `audit_events.occurred_at`, le healthcheck API n’est plus porté par le `Dockerfile` global et les conteneurs one-shot `migrate`/`auth-bootstrap` ne sont plus marqués `unhealthy` à cause d’un endpoint `/ready` qui ne les concerne pas. Les tags Docker par défaut ont aussi été alignés sur la version courante.

## v0.22.0 — P05 / EPIC-0505 UI IPAM opérationnelle

La version 0.22.0 ajoute une couche d’interface opérationnelle IPAM sans dépendance frontend externe : un view model applicatif, un rendu HTML serveur, des commandes CLI et des endpoints API dédiés. L’objectif est de permettre à un ingénieur réseau d’explorer les VRF, les préfixes, la capacité, les réservations et les conflits, puis de prévisualiser ou appliquer une réservation IP avec traçabilité.

Commandes ajoutées :

```bash
openinfra ipam ui-dashboard --tenant default [--vrf prod] [--format json|html]
openinfra ipam ui-search --tenant default --query srv-prod [--vrf prod]
openinfra ipam reservation-wizard --tenant default --vrf prod --prefix 10.0.0.0/24 --hostname srv01 --idempotency-key req-001 [--apply]
```

Endpoints ajoutés :

- `GET /api/v1/ipam/ui-dashboard`
- `GET /api/v1/ipam/ui-search`
- `POST /api/v1/ipam/reservation-wizard`
- `GET /ui/ipam`
