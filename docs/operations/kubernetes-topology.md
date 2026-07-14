# Exploitation — inventaire et topologie Kubernetes

## Pré-requis

- un jeton disposant de `kubernetes.write` pour l’import ;
- `kubernetes.read` pour la consultation ;
- des ressources Discovery déjà normalisées ;
- uniquement des **références** de secrets, jamais leurs valeurs.

## Import CLI

```bash
openinfra kubernetes import \
  --data ./openinfra-state.json \
  --tenant default \
  --admin-token "$OPENINFRA_API_TOKEN" \
  --cluster-key cluster-par-01 \
  --cluster-name prod-par-01 \
  --provider kubernetes \
  --kubernetes-version v1.34.1 \
  --source-ref discovery:k8s-prod-par-01 \
  --observed-at 2026-07-14T12:00:00Z \
  --resources-file ./kubernetes-resources.json \
  --region eu-west \
  --site-code par-01
```

Le fichier `resources-file` doit être un tableau JSON. Un import identique retourne l’instantané déjà enregistré : l’opération est idempotente par empreinte canonique.

## Consultation CLI

```bash
openinfra kubernetes list --data ./openinfra-state.json --tenant default --admin-token "$OPENINFRA_API_TOKEN" --cluster-key cluster-par-01
openinfra kubernetes latest --data ./openinfra-state.json --tenant default --admin-token "$OPENINFRA_API_TOKEN" --cluster-key cluster-par-01
openinfra kubernetes latest-topology --data ./openinfra-state.json --tenant default --admin-token "$OPENINFRA_API_TOKEN" --cluster-key cluster-par-01
```

## API

Les routes sont documentées dans Swagger/ReDoc sous **Discovery · Kubernetes et cloud-native** :

- `GET /api/v1/kubernetes/topologies` ;
- `GET /api/v1/kubernetes/topologies/get` ;
- `GET /api/v1/kubernetes/topologies/latest` ;
- `GET /api/v1/kubernetes/topologies/topology` ;
- `GET /api/v1/kubernetes/topologies/latest-topology` ;
- `POST /api/v1/kubernetes/topologies/import`.

## Surveillance

À contrôler :

- croissance du nombre d’instantanés ;
- couverture de mapping des nodes ;
- échecs de validation référentielle ;
- saturation des imports ou de l’outbox ;
- rétention des historiques selon la politique d’exploitation.

## Rollback

La migration 0055 est additive. Un rollback applicatif vers une version antérieure n’exige pas la suppression des tables : elles peuvent rester inutilisées. La suppression de données ou de tables n’est jamais exécutée automatiquement par OpenInfra.


## EPIC-2102 — Expositions réseau cloud-native

Les ressources suivantes peuvent être importées dans le même `resources-file` immuable :

- `service` : `service_type`, `cluster_ips`, `external_ips`, `external_name`, `ports`, `scope`, `rsot_object_keys` ;
- `ingress` : `hosts`, `addresses`, `ports`, `scope`, `tls`, `rsot_object_keys` ;
- `load-balancer` : `hosts`, `addresses`, `ports`, `scope`, `scheme`, `rsot_object_keys` ;
- `dns-record` : `record_type` (`A`, `AAAA`, `CNAME`), `values`, `ttl`, `scope`, `rsot_object_keys` ;
- `mesh-route` : `mesh`, `protocol`, `hosts`, `ports`, `scope`, `rsot_object_keys`.

Les cibles restent des UID Kubernetes présents dans le snapshot : load balancer vers ingress/service, DNS vers ingress/load balancer/service et route mesh vers service/workload/pod.

### Rapport par snapshot

```bash
openinfra kubernetes exposure \
  --data ./openinfra-state.json \
  --tenant default \
  --admin-token "$OPENINFRA_API_TOKEN" \
  --snapshot-id "$SNAPSHOT_ID"
```

API : `GET /api/v1/kubernetes/topologies/exposure?tenant_id=default&snapshot_id=<uuid>`.

### Rapport du dernier snapshot

```bash
openinfra kubernetes latest-exposure \
  --data ./openinfra-state.json \
  --tenant default \
  --admin-token "$OPENINFRA_API_TOKEN" \
  --cluster-key cluster-par-01
```

API : `GET /api/v1/kubernetes/topologies/latest-exposure?tenant_id=default&cluster_key=cluster-par-01`.

Le résultat indique notamment le nombre d’expositions externes, les corrélations de flux autorisées/refusées, les expositions externes non gouvernées, les dépendances RSOT et l’état `correlation_truncated`. Une troncature protège la plateforme et doit déclencher une analyse opérationnelle ; elle ne doit jamais être interprétée comme une absence de dépendance.
