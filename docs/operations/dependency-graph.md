# Dependency graph — exploitation

Le graphe de dépendances est une projection en lecture du RSOT. Il ne duplique ni les objets ni les relations et n'écrit aucune donnée métier.

## Sémantique des directions

Une relation RSOT `source_key → target_key` est parcourue :

- `outgoing` depuis la source vers la cible ;
- `incoming` depuis la cible vers les sources qui la référencent ;
- `both` dans les deux sens.

Pour une relation `application → serveur` de type `runs_on`, une analyse d'impact d'une panne du serveur utilise généralement `incoming`, afin de retrouver l'application dépendante.

## Bornes de sécurité

- profondeur : 1 à 12 ;
- nœuds : 2 à 5 000 ;
- parcours en largeur déterministe ;
- déduplication des relations ;
- cycles tolérés sans boucle infinie ;
- résultat `truncated=true` lorsque la borne de nœuds est atteinte.

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
```

## API

- `GET /api/v1/graph/traverse`
- `GET /api/v1/graph/impact`
- `GET /api/v1/graph/path`

Les trois routes exigent un Bearer token disposant de `rsot.read`. Le paramètre `relation_type` peut être répété. `as_of` accepte une date ISO-8601 avec fuseau horaire et applique simultanément l'historique des objets et la validité temporelle des relations.

## Observabilité et audit

Chaque opération produit un événement d'audit :

- `graph.traverse` ;
- `graph.impact.analyze` ;
- `graph.path.find`.

Les métadonnées enregistrent les bornes demandées, le nombre d'objets et de relations, le statut de troncature et, pour les chemins, le nombre de sauts.
