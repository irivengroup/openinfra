# Graphe de dépendances — exploitation, impact et SPOF

Le graphe est une projection en lecture du RSOT. Il ne duplique ni les objets ni les relations et n’écrit aucune donnée métier. Les opérations exigent la permission `rsot.read` et sont auditées.

## Sémantique des directions

Une relation RSOT `source_key → target_key` est parcourue :

- `outgoing` depuis la source vers la cible ;
- `incoming` depuis la cible vers les sources qui la référencent ;
- `both` dans les deux sens.

Pour une relation `application → serveur` de type `runs_on`, une analyse d’impact d’une panne du serveur utilise généralement `incoming`, afin de retrouver les applications dépendantes.

## Détection des SPOF

Un **SPOF** (*Single Point of Failure*, point unique de défaillance) est déterminé par une analyse de **dominateurs enracinés**. Pour une racine et une direction données, un candidat est retenu lorsque tous les chemins permettant d’atteindre au moins un autre objet passent par lui. Sa suppression logique rend alors ces objets inaccessibles depuis la racine.

Garanties :

- la racine n’est jamais classée SPOF ;
- les chemins alternatifs empêchent un faux positif ;
- le classement est déterministe : impact décroissant, impact direct décroissant, puis clé canonique ;
- les filtres restreignent les candidats restitués, jamais la topologie utilisée pour calculer les chemins ;
- `complete=false` signifie que `max_nodes` a été atteint : le rapport reste exact sur la projection retournée, mais ne doit pas être considéré exhaustif sur le RSOT complet ;
- aucun changement ni aucune remédiation automatique n’est appliqué aux ressources.

## Bornes de sécurité

- profondeur : 1 à 12 ;
- nœuds : 2 à 5 000 ;
- page SPOF : 1 à 500 candidats ;
- échantillon d’objets affectés : 1 à 200 ;
- parcours déterministe et résistant aux cycles ;
- curseur de pagination opaque, signé logiquement par l’empreinte des paramètres ;
- résultat `truncated=true` lorsque la borne de nœuds est atteinte.

## Objectifs de performance et benchmark volumétrique

Le benchmark P15/EPIC-1506 mesure le moteur de graphe avec un adaptateur synthétique indexé. Il isole ainsi le coût du parcours applicatif, des filtres, de l’analyse des dominateurs et de la pagination, sans masquer les régressions derrière les performances variables d’un stockage ou d’un réseau. Les benchmarks PostgreSQL live et les essais de charge distribués restent couverts par P18/EPIC-1801.

Profil CI de référence :

- 5 000 nœuds et 4 999 arêtes pour le parcours à un niveau ;
- 100 candidats SPOF répartissant les dépendances d’un graphe de 5 000 nœuds ;
- 1 warm-up puis 3 mesures ;
- percentile p95 calculé par rang supérieur ;
- cardinalités vérifiées à chaque échantillon pour empêcher un gain obtenu par résultat incomplet ;
- exécution dédiée sur Python 3.13 dans GitHub Actions.

Seuils bloquants du profil :

| Scénario | Seuil p95 | Garantie fonctionnelle associée |
|---|---:|---|
| Parcours à un niveau | 1 500 ms | 5 000 nœuds, aucune troncature |
| Parcours filtré | 1 500 ms | filtre `calls`, cardinalité exacte |
| Analyse SPOF | 5 000 ms | 100 candidats, projection complète |
| Pagination SPOF complète | 15 000 ms | toutes les pages, aucun doublon ni omission |

Commande reproductible :

```bash
PYTHONPATH=src python -m openinfra.quality.dependency_graph_benchmark \
  --nodes 5000 \
  --spof-hubs 100 \
  --samples 3 \
  --warmups 1 \
  --one-level-threshold-ms 1500 \
  --filtered-threshold-ms 1500 \
  --spof-threshold-ms 5000 \
  --pagination-threshold-ms 15000 \
  --output build/reports/dependency-graph-benchmark.json
```

Le processus retourne `0` lorsque tous les seuils sont respectés, `1` pour un dépassement de seuil et `2` pour une configuration ou une invariance fonctionnelle invalide. Le rapport JSON est écrit atomiquement et contient l’environnement, la configuration, chaque échantillon, p50, p95, le seuil, les cardinalités observées et le verdict.

## CLI

```bash
openinfra graph traverse \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --root-key application/portal \
  --direction outgoing \
  --max-depth 4 \
  --max-nodes 500 \
  --relation-type calls

openinfra graph impact \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --root-key server/db-01 \
  --direction incoming

openinfra graph path \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --source-key application/portal \
  --target-key server/db-01

openinfra graph spof \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --root-key application/portal \
  --direction outgoing \
  --candidate-resource-category network-device \
  --minimum-affected-nodes 2 \
  --affected-sample-limit 25 \
  --limit 100

openinfra graph export \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --root-key application/portal \
  --direction outgoing \
  --format graphml \
  --include-spof \
  --output /var/tmp/openinfra-portal.graphml
```

L’écriture CLI utilise un fichier temporaire dans le répertoire cible puis `os.replace`, afin que le fichier final ne soit jamais partiellement écrit.

## API

- `GET /api/v1/graph/traverse`
- `GET /api/v1/graph/impact`
- `GET /api/v1/graph/path`
- `GET /api/v1/graph/spof`
- `GET /api/v1/graph/export`

Le paramètre `relation_type` peut être répété. `as_of` accepte une date ISO-8601 avec fuseau horaire et applique simultanément l’historique des objets et la validité temporelle des relations.

La route SPOF accepte les filtres répétables `candidate_kind`, `candidate_resource_category`, `candidate_resource_type` et `candidate_status`, ainsi que `minimum_affected_nodes`, `affected_sample_limit`, `limit` et `cursor`.

L’export supporte :

- `json` : projection complète et annotations SPOF structurées ;
- `csv` : lignes normalisées `node` et `edge`, adaptées aux traitements tabulaires ;
- `graphml` : graphe dirigé interopérable avec les outils de visualisation.

La réponse d’export fournit un `Content-Disposition: attachment` et peut désactiver les annotations avec `include_spof=false`.

## Portail web et accessibilité

Le portail React et le runtime statique packagé exposent les mêmes opérations :

- vue en couches du graphe, avec zone navigable au clavier et liste textuelle équivalente des nœuds ;
- tableau de classement SPOF avec rang, impact total, impact direct, ratio et échantillon ;
- statut textuel d’analyse complète ou bornée ;
- résultat JSON brut toujours disponible ;
- téléchargement direct JSON, CSV ou GraphML.

Aucune information n’est portée uniquement par la couleur. Les vues supportent les lecteurs d’écran, les couleurs forcées, le zoom, le responsive et `prefers-reduced-motion`.

## Observabilité et audit

Chaque opération produit un événement :

- `graph.traverse` ;
- `graph.impact.analyze` ;
- `graph.path.find` ;
- `graph.spof.analyze` ;
- `graph.export`.

Les métadonnées incluent les bornes, volumes, troncature, nombre de SPOF, format et taille d’export. Aucun contenu exporté ni secret n’est copié dans l’audit.
