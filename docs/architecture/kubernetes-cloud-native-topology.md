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


## EPIC-2102 — Expositions et dépendances réseau cloud-native

OpenInfra 0.33.1 étend les instantanés immuables avec les ressources `load-balancer`, `dns-record` et `mesh-route`. Les services et ingress peuvent également porter des métadonnées d’exposition normalisées. Aucun nouveau stockage n’est créé : l’état observé reste versionné dans le snapshot Kubernetes, tandis que les déclarations de flux et les dépendances RSOT demeurent leurs propres sources de vérité.

Le rapport d’exposition est une projection **read-only**, déterministe et calculée à la demande. Il corrèle :

- les hôtes, adresses IP, ports et scopes `cluster`, `internal` ou `external` ;
- les cibles Kubernetes typées jusqu’aux workloads et pods ;
- les déclarations de flux `ANY`, `CIDR` et `OBJECT` existantes ;
- les références `rsot_object_keys` et leurs relations de dépendance.

Le graphe ajoute les relations `forwards-to`, `resolves-to`, `routes-to`, `exposes`, `correlates-to` et `governed-by-flow`. Une exposition externe non corrélée à une déclaration de flux reste visible comme **non gouvernée** ; OpenInfra ne l’autorise ni ne la bloque automatiquement.

### Bornes et complexité

La projection conserve la borne de 50 000 ressources par snapshot et limite la corrélation à 10 000 déclarations de flux, 10 000 relations RSOT et 2 048 objets de dépendance. Les lectures sont paginées, les curseurs cycliques sont refusés et le rapport expose `correlation_truncated` lorsqu’une borne protège la plateforme. Les index par UID, endpoints et clés RSOT évitent les recherches non bornées dans le graphe Kubernetes.

### Sécurité

Les valeurs de secrets restent interdites dans les attributs. Les DNS, IP, ports, protocoles, types de service et scopes sont normalisés et validés. La projection réutilise `kubernetes.read`; l’import reste protégé par `kubernetes.write`. Aucune règle de firewall, DNS, load balancer ou service mesh n’est modifiée par cette fonctionnalité.
