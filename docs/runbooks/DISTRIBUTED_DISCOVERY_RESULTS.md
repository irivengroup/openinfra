# Résultats de découverte distribuée SNMP/SSH — OpenInfra 0.34.12

## Objectif

Ce runbook couvre `TST-FUNC-0004` : exécuter une découverte distribuée SNMP/SSH, historiser chaque observation comme preuve immuable et interdire tout écrasement silencieux.

L’incrément réutilise les jobs Discovery, les collectors Enterprise, les baux avec jetons de fencing, le dépôt de preuves et le moteur de rapprochement existants. Aucune migration de base de données n’est ajoutée.

## Invariants de sécurité et de cohérence

- Le résultat n’est accepté que pour le collector assigné au job et authentifié par son empreinte de certificat.
- Un collector SNMP ne peut publier qu’un résultat SNMP ; la même règle s’applique à SSH et WinRM.
- Le jeton de fencing et le worker doivent correspondre au bail actif.
- L’identifiant de preuve est dérivé du job afin de rendre la publication idempotente.
- Une répétition strictement identique retourne la preuve existante ; une charge différente pour le même job est rejetée.
- La preuve est persistée avant la complétion du job, dans la même unité de travail.
- Le SHA-256 de la preuve devient le `result_hash` du job.
- Les secrets, références de secrets et identifiants d’authentification sont interdits dans la charge de découverte.
- Des observations ultérieures créent de nouvelles preuves ; les précédentes restent consultables.
- Un conflit entre sources reste explicite et bloque toute écriture RSOT jusqu’à résolution gouvernée.

## Parcours CLI

Après soumission et réservation du job par le collector :

```bash
openinfra discovery job-result \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --tenant default \
  --collector-id "$OPENINFRA_COLLECTOR_ID" \
  --certificate-fingerprint "$OPENINFRA_COLLECTOR_CERT_FINGERPRINT" \
  --job-id "$OPENINFRA_DISCOVERY_JOB_ID" \
  --worker-id worker-par1-01 \
  --lease-token "$OPENINFRA_DISCOVERY_LEASE_TOKEN" \
  --object-key device:par1-core-01 \
  --object-kind network-device \
  --confidence 0.98 \
  --observed-at 2026-07-22T18:00:00+00:00 \
  --payload-json '{"hostname":"par1-core-01","serial_number":"SN-PAR1-001","os_version":"17.9.4"}'
```

La sortie contient le job complété, la preuve immuable et l’indicateur `idempotent_replay`.

## Parcours API collector

```bash
curl --fail-with-body --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id":"default",
    "collector_id":"'"$OPENINFRA_COLLECTOR_ID"'",
    "certificate_fingerprint":"'"$OPENINFRA_COLLECTOR_CERT_FINGERPRINT"'",
    "job_id":"'"$OPENINFRA_DISCOVERY_JOB_ID"'",
    "worker_id":"worker-par1-01",
    "lease_token":'"$OPENINFRA_DISCOVERY_LEASE_TOKEN"',
    "object_key":"device:par1-core-01",
    "object_kind":"network-device",
    "confidence":0.98,
    "observed_at":"2026-07-22T18:00:00+00:00",
    "payload":{
      "hostname":"par1-core-01",
      "serial_number":"SN-PAR1-001",
      "os_version":"17.9.4"
    }
  }' \
  "$OPENINFRA_API_URL/api/v1/discovery/jobs/result"
```

Le premier enregistrement retourne HTTP `201`. Un rejeu identique retourne HTTP `200`. Un rejeu divergent retourne HTTP `400`.

Les portails React et runtime embarqué exposent **Soumettre un job distribué** et **Enregistrer le résultat d’un job** sous **Discovery**.

## Historique et rapprochement

Lister les preuves d’un objet :

```bash
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer $OPENINFRA_TOKEN" \
  "$OPENINFRA_API_URL/api/v1/discovery/evidence-list?tenant_id=default&object_key=device%3Apar1-core-01&limit=100"
```

Rapprocher les dernières observations SNMP et SSH :

```bash
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer $OPENINFRA_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id":"default",
    "actor":"operator@example.org",
    "object_key":"device:par1-core-01",
    "evidence_ids":["'"$SNMP_EVIDENCE_ID"'","'"$SSH_EVIDENCE_ID"'"],
    "max_age_seconds":86400
  }' \
  "$OPENINFRA_API_URL/api/v1/discovery/reconciliation"
```

Un attribut divergent, tel qu’un numéro de série, produit un rapprochement `conflict` avec `rsot_write_executed=false`.

## Vérifications automatisées

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/integration/test_contract_functional_distributed_discovery.py \
  tests/integration/test_cli_discovery.py \
  tests/integration/test_contract_proof_registry.py \
  tests/unit/test_gate14_qualification.py

PYTHONPATH=src python scripts/validate_frontend.py
PYTHONPATH=src python scripts/validate_openapi.py docs/api/openapi.yaml
```

## Diagnostic

- HTTP `401` : vérifier l’empreinte du certificat et l’état du collector.
- HTTP `400` avec jeton périmé : abandonner le résultat et réserver à nouveau le job ; ne jamais réutiliser un ancien fencing token.
- HTTP `400` avec conflit de résultat : conserver la preuve existante, comparer les payloads et ouvrir un incident de collector.
- Rapprochement `conflict` : résoudre explicitement chaque chemin divergent avant écriture RSOT.

## Rollback

Le rollback applicatif vers 0.34.11 ne nécessite aucune migration. Les preuves et jobs déjà persistés restent compatibles et consultables ; seule l’opération atomique `jobs/result` et son formulaire dédié ne sont plus disponibles. Arrêter les workers 0.34.12 avant de revenir à une version antérieure.
