# Multisite Pro centralisé — EPIC-1701

## Objectif

OpenInfra Pro et Enterprise peuvent administrer plusieurs sites DCIM depuis un backend central. Le périmètre reste centralisé : aucun agent régional, proxy collector ou réplication interrégionale n’est activé par cette fonctionnalité. Ces capacités distribuées restent réservées à l’édition Enterprise.

## Modèle d’autorisation

L’autorisation combine les permissions globales du jeton et une affectation locale au site :

- `multisite.read` : consultation des sites accessibles ;
- `multisite.report` : génération et lecture des rapports consolidés ;
- `multisite.admin` : administration des affectations et vue globale ;
- niveaux locaux `viewer`, `operator`, `admin`, ordonnés du moins au plus privilégié.

Un rôle global ne contourne pas le périmètre local, à l’exception explicite de `multisite.admin`. Un utilisateur sans affectation active ne voit aucun site. La révocation est conservée avec sa date, son auteur et son historique d’audit.

Rôles fournis : `multisite:reader`, `multisite:operator`, `multisite:admin`. Le rôle global `admin` conserve toutes les permissions.

## Rapports consolidés

Un rapport est une photographie immuable des sites accessibles au moment de la génération. Il agrège, par site et au total : bâtiments, étages, salles, racks/châssis et équipements localisés. Une sélection contenant un site inconnu ou hors périmètre est rejetée intégralement ; aucun rapport partiel n’est produit.

## API HTTP

- `GET /api/v1/multisite/site-access/grants`
- `POST /api/v1/multisite/site-access/grants/upsert`
- `POST /api/v1/multisite/site-access/grants/revoke`
- `GET /api/v1/multisite/sites`
- `GET /api/v1/multisite/reports`
- `GET /api/v1/multisite/reports/get`
- `POST /api/v1/multisite/reports/generate`

Toutes les routes exigent un jeton Bearer et un `tenant_id`. Les listes utilisent une pagination bornée par curseur.

## CLI

```bash
openinfra multisite grant-upsert --data /var/lib/openinfra/state.json \
  --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --subject ops.paris --site-code PAR1 --access-level operator

openinfra multisite sites --data /var/lib/openinfra/state.json \
  --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --subject ops.paris --required-level viewer

openinfra multisite report-generate --data /var/lib/openinfra/state.json \
  --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --subject ops.paris --site-code PAR1
```

## Persistance et montée en charge

La migration `0050_pro_centralized_multisite.sql` crée deux ensembles hash-partitionnés par tenant : affectations de sites et rapports. Les index couvrent les recherches par identité, site, état actif et date de génération. Les écritures sont transactionnelles et les requêtes PostgreSQL utilisent exclusivement des paramètres.

## Audit et sécurité

Les créations, révisions, révocations, contrôles de feature gate et générations de rapports sont audités. Aucun secret n’est stocké dans les affectations ni dans les rapports. Les identités et codes de site sont normalisés et validés avant persistance.

## Validation

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/unit/test_multisite_domain.py \
  tests/integration/test_multisite_services.py \
  tests/integration/test_multisite_cli.py \
  tests/integration/test_multisite_http_api.py \
  tests/integration/test_multisite_migration.py \
  tests/integration/test_multisite_postgresql_repository.py \
  tests/integration/test_multisite_web_contract.py
```
