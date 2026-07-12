# OpenInfra v0.30.7 — rapport de validation

Date : 2026-07-12

## Périmètre

Cette livraison réalise P20 / EPIC-2002 pour les éditions Pro et Entreprise : pagination PostgreSQL keyset par curseur opaque signé et génération progressive des exports JSON, CSV et XLSX.

## Fonctionnalités validées

### Pagination keyset

- curseurs Base64URL signés HMAC-SHA256 ;
- liaison du curseur au tenant, au contexte, aux filtres, à l'ordre et aux positions de tri ;
- prédicats lexicographiques indexables, y compris pour les tris mixtes ascendants/descendants ;
- rejet des curseurs altérés, hors contexte ou associés à d'autres filtres ;
- compatibilité ascendante temporaire avec les curseurs numériques historiques ;
- migration de la page suivante vers un curseur opaque dès qu'un secret stable est configuré ;
- absence de clause `OFFSET` directe dans les repositories PostgreSQL ;
- validation explicite des valeurs entières, flottantes, booléennes, dates et datetimes ;
- migration additive `0053_keyset_pagination_indexes.sql` avec index composés tenant/tri.

### Exports progressifs

- parcours de la source page par page ;
- sérialisation progressive JSON, CSV et XLSX ;
- tampon `SpooledTemporaryFile` borné à 8 MiB avant débordement disque ;
- conservation des signatures HMAC et SHA-256 ;
- conservation du téléchargement par chunks ;
- maintien des formats et contrats publics existants ;
- aucun chargement préalable de toutes les lignes dans une collection Python.

## Validation backend

- 1 008 tests Python collectés et réussis ;
- couverture : 35 712 lignes couvertes sur 36 440, soit 98,0022 % ;
- seuil contractuel de 98 % : PASS ;
- Ruff format : 295 fichiers conformes ;
- Ruff lint : PASS ;
- mypy strict : 94 modules, PASS ;
- `compileall` : PASS ;
- Bandit : PASS ;
- security gate : PASS ;
- quality gate : PASS ;
- deux contrats OpenAPI : PASS ;
- six profils installateurs : PASS ;
- alignement Enterprise : PASS ;
- CDC 4.9.0 : 840 exigences / 529 entités, PASS ;
- roadmap 2.1.0 : 21 phases / 125 epics / 10 gates / 106 tests, PASS ;
- 53 migrations PostgreSQL validées, dernière migration `0053_keyset_pagination_indexes.sql`.

## Validation frontend

- 51 tests Node.js réussis ;
- contrat statique : PASS ;
- ESLint JSX : PASS ;
- WCAG 2.2 AA : PASS ;
- build Vite : PASS ;
- audit npm : 0 vulnérabilité ;
- bundle JavaScript : 320,39 KiB brut / 92,87 KiB gzip ;
- bundle CSS : 281,84 KiB brut / 40,15 KiB gzip.

## Benchmark de construction keyset

Configuration : 5 000 itérations par scénario, seuil p95 de 1 ms.

| Scénario | p50 | p95 | p99 | Résultat |
|---|---:|---:|---:|---|
| Première page | 0,001512 ms | 0,001642 ms | 0,004567 ms | PASS |
| Page profonde | 0,016235 ms | 0,023255 ms | 0,030626 ms | PASS |

Le rapport porte explicitement `scope=keyset-query-construction-regression` et `capacity_certification=false`. Il démontre que le coût de décodage et de construction du prédicat ne dépend pas de la profondeur logique ; il ne remplace pas un test `EXPLAIN (ANALYZE, BUFFERS)` sur PostgreSQL réel.

## Sécurité des dépendances

- audit npm : PASS, aucune vulnérabilité ;
- Bandit et security gate : PASS ;
- `pip-audit --strict` a été installé et exécuté, mais n'a pas pu résoudre `pypi.org` ;
- le gate `pip-audit` demeure bloquant dans GitHub Actions avec accès réseau.

## Limites d'environnement

- Docker et Podman ne sont pas disponibles ;
- PostgreSQL réel et `psql` ne sont pas disponibles ;
- les index `0053`, les plans d'exécution, la réplication, PgBouncer, l'endurance et la saturation n'ont donc pas été exécutés sur une topologie réelle ;
- aucune certification de capacité Pro/Entreprise n'est revendiquée par le benchmark local.

## Compatibilité et rollback

- les clients utilisant encore un curseur numérique continuent de fonctionner ;
- la compatibilité numérique est temporaire et isolée dans l'adaptateur de pagination ;
- les index de la migration `0053` sont additifs et peuvent rester en place lors d'un rollback applicatif ;
- un serveur antérieur à 0.30.7 ne comprend pas les nouveaux curseurs opaques : après rollback, les clients doivent reprendre à la première page ;
- aucune fonctionnalité, route, commande CLI ou format d'export existant n'a été supprimé.

Le CDC reste en version 4.9.0 et la roadmap en version 2.1.0 : EPIC-2002 y était déjà planifié. La traçabilité et le runbook opérationnel ont été mis à jour dans la livraison.
