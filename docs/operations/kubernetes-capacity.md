# Exploitation de la capacité Kubernetes

## Importer des mesures

Les mesures de capacité sont intégrées aux ressources du snapshot Kubernetes.

```json
{
  "kind": "pod",
  "uid": "pod-api-01",
  "name": "api-01",
  "namespace": "production",
  "attributes": {
    "capacity": {
      "cpu_request_millicores": 500,
      "cpu_limit_millicores": 1000,
      "cpu_usage_millicores": 720,
      "memory_request_bytes": 1073741824,
      "memory_limit_bytes": 2147483648,
      "memory_usage_bytes": 1610612736
    }
  }
}
```

## Consulter

```bash
openinfra kubernetes latest-capacity \
  --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --cluster-key cluster-par-01
```

```bash
openinfra kubernetes capacity-trend \
  --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --cluster-key cluster-par-01 --limit 24
```

## Exporter

```bash
openinfra kubernetes latest-capacity-export \
  --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --cluster-key cluster-par-01 --format csv > capacity.csv
```

Les exports disponibles sont `json` et `csv`.

## Alertes

Les seuils par défaut sont 80 % pour `warning` et 90 % pour `critical`. Ils peuvent être ajustés par requête sans modifier le snapshot source. Les alertes couvrent :

- consommation cluster / capacité ;
- demandes cluster / capacité ;
- consommation namespace / limite lorsqu'une limite existe.

Aucune action corrective n'est déclenchée automatiquement.
