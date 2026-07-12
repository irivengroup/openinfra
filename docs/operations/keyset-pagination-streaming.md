# Pagination keyset et exports progressifs

## Objectif

OpenInfra 0.30.7 réalise P20 / EPIC-2002 pour les éditions Pro et Entreprise. Les collections PostgreSQL non bornées utilisent une pagination keyset indexable. Les exports parcourent ces pages sans accumuler toutes les lignes en mémoire.

## Contrat des curseurs

Un curseur opaque contient uniquement la position de tri nécessaire à la reprise. Il est sérialisé en JSON canonique, encodé en Base64URL et signé avec HMAC-SHA256. La signature couvre :

- le composant et le contexte de collection ;
- le tenant ;
- les filtres normalisés ;
- les valeurs ordonnées de la dernière ligne ;
- la version du format de curseur.

Un curseur modifié, utilisé avec un autre tenant, un autre filtre ou un autre endpoint est rejeté. Le secret dédié `OPENINFRA_CURSOR_SIGNING_SECRET` est facultatif ; lorsqu’il est absent, OpenInfra utilise le secret de cohérence lecture-après-écriture. Les topologies multiprocessus doivent fournir un secret stable partagé par tous les workers.

## Compatibilité ascendante

Les curseurs numériques historiques sont encore acceptés comme offsets de transition. Cette voie est isolée dans `PostgreSQLKeysetPage.offset_sql`. Dès la page suivante, le serveur émet un curseur opaque signé lorsque le codec est configuré. Aucun repository PostgreSQL ne contient directement de clause `OFFSET`.

La suppression définitive des curseurs numériques nécessitera une annonce de dépréciation et un jalon de rupture distinct.

## Index PostgreSQL

La migration `0053_keyset_pagination_indexes.sql` ajoute les index composés correspondant exactement aux tris de pagination, avec `tenant_id` en première colonne. Elle est additive, transactionnelle et ne modifie aucune donnée.

Sur une base très volumineuse, la création de ces index doit être planifiée dans une fenêtre de maintenance. Une installation existante doit vérifier l’espace disque, la durée de création et le lag du standby avant promotion.

## Exports progressifs

`ExportArtifactStreamBuilder` consomme un itérateur de lignes page par page et écrit progressivement :

- JSON : tableau valide, ligne après ligne ;
- CSV : en-tête puis lignes via `csv.DictWriter` ;
- XLSX : feuille XML écrite dans le conteneur ZIP sans construire le document complet en mémoire.

Le tampon `SpooledTemporaryFile` conserve les petits artefacts en mémoire et bascule automatiquement sur disque au-delà de 8 MiB. Le repository d’artefacts reçoit encore le contenu final en bytes afin de préserver le contrat de stockage existant ; l’externalisation vers un stockage objet est prévue en EPIC-2003.

## Validation

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_cursor_pagination.py \
  tests/unit/test_export_stream_builder.py \
  tests/integration/test_keyset_pagination_migration.py \
  tests/integration/test_export_services.py \
  tests/integration/test_postgresql_runtime.py \
  tests/performance/test_cursor_pagination_benchmark.py

PYTHONPATH=src:. python scripts/benchmark_cursor_pagination.py \
  --iterations 5000 \
  --p95-threshold-ms 1 \
  --output build/reports/cursor-pagination.json \
  --enforce
```

Le benchmark valide que la construction du prédicat et le décodage d’un curseur profond restent indépendants de la profondeur logique. Il ne remplace pas `EXPLAIN (ANALYZE, BUFFERS)` sur PostgreSQL réel et porte `capacity_certification=false`.

## Rollback

La migration ne doit pas être supprimée en urgence : les index supplémentaires sont compatibles avec l’ancienne version. Pour revenir temporairement à 0.30.6, conserver la migration appliquée et le secret partagé. Les nouveaux curseurs opaques ne seront pas compris par un serveur antérieur ; les clients doivent alors reprendre depuis la première page.
