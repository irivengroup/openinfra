# Localisation DCIM et réservation IP concurrente — OpenInfra 0.34.24

## Objectif

Ce runbook couvre les preuves contractuelles automatisées suivantes :

- `TST-FUNC-0001` : un équipement est localisable sans ambiguïté jusqu’au site, bâtiment, étage, salle, grille, zone éventuelle, rack, position U, face et coordonnées ;
- `TST-FUNC-0002` : plusieurs demandes concurrentes ne peuvent jamais réserver la même adresse IP dans un préfixe donné.

La charte graphique, les schémas PostgreSQL/Oracle et les contrats existants restent inchangés.

## Invariants de localisation

Une localisation valide conserve les identifiants structurés et produit un chemin humain déterministe. La zone et le rack sont facultatifs pour les équipements au sol ; lorsqu’une position U est fournie, le rack, la face et la hauteur doivent rester cohérents avec les contraintes DCIM.

### CLI

```bash
openinfra dcim locate \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --tenant default \
  --actor operator@example.org \
  --asset-tag PAR-SRV-001 \
  --equipment-name srv-app-01 \
  --site PAR1 \
  --building BAT-A \
  --floor F01 \
  --room MMR1 \
  --row B \
  --column 12 \
  --rack R42 \
  --u-position 10 \
  --u-height 2 \
  --rack-face front \
  --x 12 --y 4 --z 0

openinfra dcim locator-sheet \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --tenant default \
  --actor operator@example.org \
  --asset-tag PAR-SRV-001 \
  --format json
```

### API

```bash
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer $OPENINFRA_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id":"default",
    "actor":"operator@example.org",
    "asset_tag":"PAR-SRV-001",
    "equipment_name":"srv-app-01",
    "site":"PAR1",
    "building":"BAT-A",
    "floor":"F01",
    "room":"MMR1",
    "row":"B",
    "column":"12",
    "rack":"R42",
    "u_position":10,
    "rack_face":"front",
    "u_height":2,
    "x":12,
    "y":4,
    "z":0
  }' \
  "$OPENINFRA_API_URL/api/v1/dcim/locations"

curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer $OPENINFRA_TOKEN" \
  "$OPENINFRA_API_URL/api/v1/dcim/locator-sheet?tenant_id=default&asset_tag=PAR-SRV-001&format=json"
```

Les portails React et runtime embarqué exposent les opérations **Localiser un équipement** et **Fiche d’intervention équipement** sous **DCIM → Localisation & capacité**.

## Invariants de réservation IP

- Le verrou est acquis dans l’unité de travail qui persiste la réservation.
- Le backend JSON sérialise l’allocation avec un verrou réentrant local.
- PostgreSQL utilise un verrou transactionnel consultatif par tenant, VRF et préfixe.
- Une clé d’idempotence rejouée retourne la réservation initiale sans consommer une nouvelle adresse.
- Le mode aperçu n’écrit aucune réservation.
- L’absence d’adresse libre échoue explicitement ; aucune allocation partielle n’est conservée.

### CLI

```bash
openinfra ipam reservation-wizard \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --tenant default \
  --actor operator@example.org \
  --vrf production \
  --prefix 10.72.0.0/27 \
  --hostname srv-app-01 \
  --idempotency-key change-20260722-001

openinfra ipam reservation-wizard \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --tenant default \
  --actor operator@example.org \
  --vrf production \
  --prefix 10.72.0.0/27 \
  --hostname srv-app-01 \
  --idempotency-key change-20260722-001 \
  --apply
```

La première commande est un aperçu. La seconde applique la réservation. Le même identifiant d’idempotence doit être réutilisé lors d’une reprise après interruption.

### API

```bash
curl --fail-with-body --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id":"default",
    "actor":"operator@example.org",
    "vrf":"production",
    "prefix":"10.72.0.0/27",
    "hostname":"srv-app-01",
    "idempotency_key":"change-20260722-001",
    "apply":true
  }' \
  "$OPENINFRA_API_URL/api/v1/ipam/reservation-wizard"
```

Le portail expose **Assistant de réservation IPAM** et exige une clé d’idempotence visible dans le formulaire.

## Vérifications automatisées

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/integration/test_contract_functional_physical_location.py \
  tests/integration/test_contract_functional_ipam_concurrency.py \
  tests/integration/test_contract_proof_registry.py \
  tests/unit/test_gate14_qualification.py

PYTHONPATH=src python -m openinfra.quality.contract_completeness_promotion \
  --project-root . \
  --candidate-id openinfra-0.34.24-local \
  --source-commit 0000000000000000000000000000000000000000 \
  --output artifacts/gate14/report.json \
  --enforce
```

## Exploitation et diagnostic

Pour une localisation incorrecte, vérifier d’abord les référentiels site, bâtiment, étage, salle, zone et rack, puis relancer la génération de la fiche. Ne corriger ni le QR compact ni son checksum manuellement.

Pour une allocation IP inattendue, rechercher la clé d’idempotence, le tenant, la VRF et le préfixe avant toute nouvelle tentative. Ne supprimer une réservation qu’au travers des services IPAM afin de préserver l’audit et les intégrations DDI.

## Rollback

L’incrément n’introduit aucune migration. Un rollback applicatif vers 0.34.9 est donc possible après sauvegarde de l’état et arrêt des writers. Les localisations et réservations créées restent compatibles avec 0.34.9 ; seule l’opération de portail dédiée à la fiche d’intervention disparaît lors du rollback.
