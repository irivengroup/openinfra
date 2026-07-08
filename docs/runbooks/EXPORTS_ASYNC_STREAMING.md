# OpenInfra — exports asynchrones et streaming signé

Depuis v0.29.53, les artefacts produits par `openinfra export run` peuvent être lus par chunks bornés sans modifier le téléchargement complet existant.

## Flux opérateur

```bash
openinfra export request \
  --data state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --resource source_objects \
  --format json \
  --limit 100000

openinfra export run \
  --data state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --job-id "$JOB_ID"

openinfra export artifact-chunk \
  --data state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --job-id "$JOB_ID" \
  --offset 0 \
  --size 65536 \
  --output chunk-000.bin
```

## Contrat API

`GET /api/v1/exports/artifact-chunk?tenant_id=default&job_id=<job>&offset=0&size=65536`

Le service vérifie toujours l’artefact complet avant extraction du chunk :

- SHA-256 stocké dans les métadonnées de l’artefact ;
- signature HMAC-SHA256 ;
- bornes `offset >= 0` et `1 <= size <= 1048576`.

La réponse JSON contient `content_base64`, `chunk_sha256`, `next_offset` et `final_chunk`. Le client continue tant que `next_offset` n’est pas `null`.
