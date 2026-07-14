# Kubernetes & Cloud-native — inventaire et topologie physique

## Objectif

OpenInfra 0.33.0 ouvre **P21 / REL-11** avec `EPIC-2101`. Le domaine Discovery peut désormais conserver des instantanés Kubernetes immuables et reconstruire un graphe déterministe depuis le cluster jusqu’à l’infrastructure physique référencée dans RSOT/DCIM.

Le modèle couvre les ressources `namespace`, `node`, `workload`, `pod`, `service`, `ingress`, `network-policy` et `volume`. Un instantané est borné à **50 000 ressources**, isolé par tenant, versionné par date d’observation et dédupliqué par empreinte SHA-256 canonique.

## Architecture

Le flux respecte l’architecture hexagonale :

1. **Interface** : CLI, API HTTP et portail Discovery reçoivent un inventaire JSON sans secret.
2. **Application** : `KubernetesTopologyService` applique RBAC, idempotence, transaction, événement de domaine et audit.
3. **Domaine** : `KubernetesTopologySnapshot` valide l’intégrité du graphe et calcule l’empreinte immuable.
4. **Infrastructure** : repositories JSON et PostgreSQL implémentent le même port.
5. **Projection** : le graphe restitue les relations Kubernetes et les liens externes `rsot:*` sans recopier les objets RSOT/DCIM.

## Invariants

- un UID et une identité `(kind, namespace, name)` sont uniques dans un instantané ;
- les ressources namespacées référencent un namespace présent ;
- `node_name` est réservé aux pods et référence un node présent ;
- un owner ou une cible ne peut se référencer lui-même ;
- les relations service, ingress, network-policy et volume sont typées et ne traversent pas les namespaces ;
- `physical_path` est réservé aux nodes ;
- rack ou salle exigent un `site_code` ;
- les clés d’attributs ressemblant à un secret, mot de passe, token, credential, clé API ou clé privée sont refusées ;
- aucune mutation RSOT/DCIM n’est déclenchée par l’import Kubernetes.

## Topologie produite

Les relations internes utilisent des nœuds `k8s:<uid>` :

- cluster `contains` namespace/node ;
- namespace `contains` ressource namespacée ;
- owner `owns` ressource ;
- node `hosts` pod ;
- service `routes-to` workload/pod ;
- ingress `publishes` service ;
- network-policy `governs` workload/pod ;
- volume `mounted-by` pod.

Les relations physiques utilisent des références externes `rsot:<key>` et peuvent enchaîner :

`node → VM → hyperviseur → serveur → rack → salle → site`.

Un chemin partiel est accepté lorsque la source Discovery ne possède qu’une partie des corrélations. La couverture de mapping des nodes est exposée dans le résumé de l’instantané.

## Persistance et performance

La migration `0055_kubernetes_topology_inventory.sql` ajoute :

- `kubernetes_topology_snapshots`, partitionnée par hash du tenant en 16 partitions ;
- `kubernetes_topology_event_outbox`, également partitionnée ;
- unicité `(tenant_id, fingerprint)` ;
- index latest cluster et provider/site ;
- index GIN sur le payload JSONB ;
- index partiel et BRIN pour l’outbox.

La liste PostgreSQL utilise la pagination curseur/keyset sur `(observed_at, imported_at, id)`. La construction du graphe utilise des index mémoire par UID, node et namespace, donc sans recherche quadratique.

## Sécurité

Les permissions dédiées sont `kubernetes.read` et `kubernetes.write`. Les rôles `kubernetes:reader` et `kubernetes:operator` permettent une délégation minimale ; le rôle administrateur conserve l’ensemble des permissions. Les imports sont audités et produisent l’événement `kubernetes.topology.imported`.
