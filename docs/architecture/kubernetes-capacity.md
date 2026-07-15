# Capacité Kubernetes cluster et namespace

OpenInfra P21 / EPIC-2105 calcule des read models de capacité à partir des snapshots Kubernetes immuables déjà gouvernés par EPIC-2101. Aucune nouvelle source de vérité ni collecte implicite n'est introduite.

## Modèle de mesure

Les métriques sont stockées dans `resource.attributes.capacity` avec des unités explicites : CPU en millicores, mémoire et stockage en octets.

- `node` : capacités CPU, mémoire et stockage ;
- `pod` : demandes, limites et consommation CPU/mémoire ;
- `volume` : demandes, limites, consommation et capacité stockage.

Les autres kinds refusent les métriques de capacité. Les valeurs sont des entiers non négatifs et une demande ne peut pas dépasser sa limite lorsqu'elles sont toutes deux renseignées.

## Agrégation

- capacité CPU/mémoire du cluster : somme des Nodes ;
- demandes, limites et consommation CPU/mémoire : somme des Pods ;
- capacité, demandes, limites et consommation stockage : somme des Volumes ;
- agrégats namespace : Pods et Volumes appartenant au namespace.

Les marges et pourcentages sont calculés sans écriture. Les alertes `warning` et `critical` utilisent des seuils explicites, avec `1 <= warning < critical <= 100`.

## Bornes

- 50 000 ressources maximum par snapshot, héritées d'EPIC-2101 ;
- 5 000 namespaces maximum par rapport ;
- 96 snapshots maximum par tendance ;
- 1 000 000 de ressources cumulées maximum par calcul de tendance.

La tendance s'arrête avec `truncated=true` si le budget cumulé est atteint.

## Compatibilité

Les snapshots historiques sans bloc `capacity` conservent exactement leur sérialisation et leur fingerprint. Aucune migration PostgreSQL supplémentaire n'est requise : le payload JSONB immuable de la migration `0055_kubernetes_topology_inventory.sql` porte les nouvelles métriques lorsqu'elles sont présentes.
