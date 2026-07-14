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
