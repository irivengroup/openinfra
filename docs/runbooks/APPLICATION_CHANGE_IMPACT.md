# Analyse d’impact d’un changement applicatif — OpenInfra 0.34.13

Ce runbook couvre `TST-FUNC-0005`. Il produit un rapport borné et en lecture seule à partir du graphe RSOT afin d’identifier les services métier affectés, les dépendances critiques et les risques de point unique de défaillance (SPOF).

## Prérequis

- relations RSOT actives et datées entre applications, services, bases, serveurs et composants d’infrastructure ;
- jeton disposant de la permission de lecture RSOT ;
- clé RSOT de la ressource modifiée ;
- direction `incoming` pour rechercher les consommateurs dépendants d’une ressource technique.

## API

```bash
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer ${OPENINFRA_ADMIN_TOKEN}" \
  --get "${OPENINFRA_API_URL}/api/v1/graph/change-impact" \
  --data-urlencode "tenant_id=${OPENINFRA_TENANT}" \
  --data-urlencode "root_key=server/db-01" \
  --data-urlencode "direction=incoming" \
  --data-urlencode "max_depth=8" \
  --data-urlencode "max_nodes=2000"
```

## CLI

```bash
openinfra graph change-impact \
  --backend postgresql \
  --database-url "${OPENINFRA_DATABASE_URL}" \
  --tenant "${OPENINFRA_TENANT}" \
  --admin-token "${OPENINFRA_ADMIN_TOKEN}" \
  --root-key server/db-01 \
  --direction incoming \
  --max-depth 8 \
  --max-nodes 2000
```

## Lecture du rapport

- `business_services` : applications, services et bases métier potentiellement affectés ;
- `critical_dependencies` : nœuds dominateurs dont la perte rend au moins un service métier inaccessible depuis la racine analysée ;
- `affected_business_service_keys` : échantillon déterministe des services métier dépendants ;
- `root_spof_risk` : indique que la ressource modifiée est elle-même indispensable aux services métier listés ;
- `complete=false` : le graphe a atteint `max_nodes`; augmenter la borne avant toute décision de changement.

Le rapport ne modifie jamais RSOT. Les résultats sont ordonnés de manière déterministe et l’opération est journalisée dans l’audit avec les compteurs d’impact, de services métier et de dépendances critiques.
