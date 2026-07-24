# Consultation historique RSOT « time travel » — OpenInfra 0.34.21

Ce runbook couvre `TST-FUNC-0009`. Il restitue l’état cohérent d’un objet RSOT à une date ISO-8601, avec la version résolue, la provenance du snapshot et les relations valides à cet instant.

## Garanties

- résolution du dernier snapshot dont `changed_at` est inférieur ou égal à `as_of` ;
- cohérence vérifiée entre la clé demandée, l’identifiant, la version et le payload du snapshot ;
- provenance explicite : système source, acteur, horodatage et identifiant du snapshot ;
- relations entrantes et sortantes filtrées par leur fenêtre de validité historique ;
- déduplication et ordre déterministes ;
- résultat borné par `relation_limit` entre 1 et 500 ;
- `complete=false` lorsque la borne empêche de restituer toutes les relations ;
- opération strictement en lecture seule et journalisée sous `rsot.object.time-travel.read`.

## API HTTP

```bash
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer ${OPENINFRA_ADMIN_TOKEN}" \
  --get "${OPENINFRA_API_URL}/api/v1/rsot/object-as-of" \
  --data-urlencode "tenant_id=${OPENINFRA_TENANT}" \
  --data-urlencode "key=server/db-01" \
  --data-urlencode "as_of=2026-07-01T10:30:00+00:00" \
  --data-urlencode "relation_limit=100"
```

## CLI

```bash
openinfra rsot get-object-as-of \
  --backend postgresql \
  --database-url "${OPENINFRA_DATABASE_URL}" \
  --tenant "${OPENINFRA_TENANT}" \
  --admin-token "${OPENINFRA_ADMIN_TOKEN}" \
  --key server/db-01 \
  --as-of 2026-07-01T10:30:00+00:00 \
  --relation-limit 100
```

## Lecture du rapport

- `resolved_version` : version réellement applicable à la date demandée ;
- `snapshot_id` et `snapshot_changed_at` : identité et horodatage du snapshot ;
- `provenance` : système source, acteur et preuve temporelle ;
- `relations` : relations entrantes et sortantes valides à `as_of` ;
- `relation_count` : nombre de relations restituées après déduplication ;
- `coherent=true` : invariants du snapshot et des relations vérifiés ;
- `complete=false` : état historiquement cohérent mais relations volontairement bornées.

Une réponse `complete=false` ne doit pas être présentée comme une cartographie exhaustive. Augmenter `relation_limit` dans la limite contractuelle ou utiliser une extraction dédiée.

## Validation ciblée

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/integration/test_contract_functional_time_travel.py
node --test web/tests/time-travel.test.mjs
python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/09-API/OpenAPI/openapi.yaml
```
