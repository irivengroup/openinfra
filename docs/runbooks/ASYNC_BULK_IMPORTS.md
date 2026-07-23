# Imports massifs asynchrones CSV/XLSX

## Objectif

OpenInfra accepte un inventaire CSV ou XLSX par flux binaire, le stocke dans un artefact tenant-isolé adressé par contenu, puis soumet un job `imports.bulk-dataset` au worker spécialisé `imports`. L’API interactive ne traite pas le dataset dans le thread HTTP et reste disponible pendant l’import.

Le parcours est exposé dans les portails React et runtime embarqué sous **Imports / Exports → Soumettre un import massif asynchrone**.

## Garanties

- upload sans encodage Base64 et sans chargement intégral du fichier en mémoire ;
- artefact SHA-256 adressé par contenu, vérifié lors de sa matérialisation ;
- clé d’idempotence obligatoire : une relance strictement identique retourne le job existant ;
- rejet d’une même clé associée à un fichier ou à des paramètres différents ;
- traitement par lots et checkpoints persistants ;
- reprise par `resume_job_id` après interruption ;
- résultat, progression, DLQ et audit persistants ;
- disponibilité de l’API interactive indépendante de la durée du worker ;
- aucune présence du jeton d’administration dans l’URL ou le payload métier.

## Limites et protections

| Format | Limite d’upload | Traitement |
|---|---:|---|
| CSV | 512 Mio | lecture ligne par ligne |
| XLSX | 50 Mio | validation ZIP, nombre d’entrées borné, taille XML et taille décompressée bornées |

Le nom transmis dans `X-OpenInfra-Filename` doit être encodé en URL, ne contenir aucun séparateur de chemin et se terminer par `.csv` ou `.xlsx`. Les archives XLSX chiffrées sont refusées.

Le mapping doit au minimum définir `key`, `kind`, `display_name` et `source`. Une valeur `literal:<valeur>` peut fournir une constante indépendante des colonnes du fichier.

## Soumission HTTP

Variables sûres :

```bash
set -euo pipefail
API_BASE="${OPENINFRA_API_BASE:-http://127.0.0.1:2006}"
TENANT_ID="${OPENINFRA_TENANT_ID:-default}"
: "${OPENINFRA_TOKEN:?OPENINFRA_TOKEN est obligatoire}"
SOURCE_FILE="/var/lib/openinfra/imports/inventory.csv"
IDEMPOTENCY_KEY="inventory-$(sha256sum "$SOURCE_FILE" | awk '{print $1}')"
MAPPING_JSON='{"key":"asset_key","kind":"kind","display_name":"name","source":"source","tags":"tags","attributes.serial":"serial"}'
ENCODED_MAPPING="$(python -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$MAPPING_JSON")"
```

Soumission idempotente :

```bash
curl --fail-with-body --silent --show-error \
  --request POST \
  --header "Authorization: Bearer ${OPENINFRA_TOKEN}" \
  --header "Content-Type: text/csv" \
  --header "X-OpenInfra-Filename: inventory.csv" \
  --data-binary "@${SOURCE_FILE}" \
  "${API_BASE}/api/v1/imports/async-bulk-datasets?tenant_id=${TENANT_ID}&actor=operator&format=csv&mapping_json=${ENCODED_MAPPING}&apply=true&idempotency_key=${IDEMPOTENCY_KEY}&batch_size=5000&checkpoint_interval=25000&sample_limit=100&max_attempts=3"
```

La réponse HTTP `202` contient :

- `job.id` : identifiant du job asynchrone ;
- `job.status` : normalement `queued` ;
- `source_artifact` : clé, empreinte, taille et type du fichier ;
- `status_url` : suivi consolidé du job et du rapport ;
- `result_url` : artefact de résultat brut.

## Exécution du worker

Un worker importe au plus un job par appel :

```bash
curl --fail-with-body --silent --show-error \
  --request POST \
  --header "Authorization: Bearer ${OPENINFRA_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "{\"tenant_id\":\"${TENANT_ID}\",\"worker_id\":\"imports-worker-$(hostname -s)\",\"lease_seconds\":300,\"retry_delay_seconds\":30}" \
  "${API_BASE}/api/v1/async/workers/imports/run-once"
```

En production, cette commande est exécutée par le service worker avec concurrence bornée. Un job loué possède un `lease_token`; un échec transitoire passe en `retry-wait`, puis en dead-letter lorsque `max_attempts` est atteint.

## Suivi

```bash
JOB_ID="<uuid retourné à la soumission>"
curl --fail-with-body --silent --show-error \
  --header "Authorization: Bearer ${OPENINFRA_TOKEN}" \
  "${API_BASE}/api/v1/imports/async-bulk-status?tenant_id=${TENANT_ID}&job_id=${JOB_ID}"
```

`result` reste `null` tant que le job n’est pas `completed`. Une fois terminé, `result.report` expose notamment :

- `status` : `validated`, `applied` ou `failed` ;
- `total_rows`, `valid_rows`, `invalid_rows` ;
- `create_count`, `update_count` ;
- `checkpoint.next_row_number` ;
- `metrics.batches_completed` et `metrics.resumed_from_row` ;
- `impact_sample` et `dlq_sample`.

## Reprise

Pour reprendre un import interrompu, soumettre de nouveau le même fichier avec une **nouvelle** clé d’idempotence et `resume_job_id=<job-import-métier>`. Cet identifiant est celui de `result.report.job_id`, pas celui de la file asynchrone.

Le service relit le fichier, ignore les lignes antérieures au checkpoint et poursuit les compteurs et lots. Le fichier et le mapping doivent rester identiques à ceux de l’import initial.

## Rollback

Un import appliqué peut être annulé par le mécanisme conflict-aware décrit dans [IMPORTS_BULK_ROLLBACK.md](IMPORTS_BULK_ROLLBACK.md). Le rollback relit le même dataset jusqu’au checkpoint, restaure les versions précédentes et met en retrait les objets créés sans suppression physique.

## Audit et sécurité

Permissions :

- soumission : `async.submit` et, lors du traitement, `rsot.write` ;
- suivi : `async.read` ;
- worker : `async.worker` et `rsot.write`.

Événements principaux :

- `async.artifact.stored` avec `streamed=true` ;
- `async.job.submitted` ;
- `import.bulk_dataset.<status>` ;
- événements de transition de file et d’outbox.

Le jeton est exclusivement transmis dans `Authorization: Bearer`. Les journaux et rapports ne contiennent ni le jeton ni le contenu brut du fichier.

## Validation ciblée

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/integration/test_contract_functional_bulk_import.py \
  tests/integration/test_async_processing_services.py \
  tests/integration/test_specialized_workers.py \
  tests/unit/test_async_artifact_stores.py \
  tests/unit/test_async_processing_domain.py

node --test web/tests/bulk-import.test.mjs
python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/09-API/OpenAPI/openapi.yaml
```
