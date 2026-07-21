# FinOps, coûts et showback

## Périmètre

OpenInfra consolide les coûts d’infrastructure, de cloud, de SaaS, de licences, de support, d’énergie et de contrats. La capacité est rattachée à **ITAM → FinOps & coûts**. Elle produit des vues showback et des calculs chargeback contrôlés, sans générer d’écriture comptable, de facture ou de changement ITSM.

## Modèle et précision financière

Tous les montants sont représentés par `Decimal` avec six décimales. Les devises utilisent un code ISO 4217 à trois lettres. Une ligne importée contient une période, une source, une catégorie, un montant, un propriétaire et des métadonnées gouvernées. Les clés susceptibles de contenir un secret (`password`, `token`, `api_key`, `private_key`, etc.) sont refusées récursivement.

Les imports sont idempotents par tenant et clé métier. Le SHA-256 de la charge lie définitivement une clé d’idempotence à son contenu. Un import est d’abord enregistré dans l’état `queued`, puis exécuté explicitement. Les états terminaux, compteurs et erreurs sont persistés et audités.

## Allocation et qualité

Les règles sont ordonnées par priorité et peuvent filtrer une catégorie ou une source. Les dimensions prises en charge sont : actif, application, service métier, tenant, propriétaire, tag, centre de coûts, environnement et dépendance. Toute fraction non attribuable est conservée dans `financial-quality/unallocated` ; elle n’est jamais perdue ni répartie arbitrairement.

Chaque coût reçoit un statut de qualité : `allocated`, `partial` ou `unallocated`. Les rapports exposent le montant non alloué et un score de qualité. Les anomalies couvrent notamment les coûts non attribués et les hausses significatives par rapport à l’historique comparable.

## Budgets, prévisions et périodes

Les budgets sont versionnés par dimension, cible, période et devise. Le dépassement du seuil configuré publie l’événement `budget.threshold.crossed`. Les prévisions utilisent jusqu’à douze périodes historiques et indiquent leur nombre de périodes de référence, leur confiance et l’empreinte des données sources.

La clôture d’une période calcule un digest SHA-256 de toutes les lignes normalisées. Après clôture, aucun nouvel import ne peut modifier la période. Un rapport généré sur une période clôturée est reproductible : la même requête et le même digest retournent le même rapport.

## Showback et chargeback

Le **showback** répartit les coûts à titre informatif. Le **chargeback** applique éventuellement une majoration bornée, mais conserve `production_billing_mutation=false`. OpenInfra ne crée aucune écriture dans un ERP, aucun prélèvement et aucune facture.

Les exports sont disponibles en JSON et CSV. Les rapports, lignes, budgets, anomalies et prévisions sont isolés par tenant et paginés.

## Permissions

- `finops.read` : consultation des règles, coûts, budgets, périodes, rapports, anomalies et prévisions ;
- `finops.write` : règles, budgets et génération de rapports ;
- `finops.import` : soumission, exécution et annulation des imports ;
- `finops.export` : export des rapports ;
- `finops.admin` : clôture des périodes.

## API et CLI

Les 18 routes sont publiées sous `/api/v1/finops/*`. La CLI correspondante est disponible sous `openinfra finops` :

```bash
openinfra finops rule-create --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --name "Applications cloud" --dimension application \
  --selector-key application_key --percentage 100 --category cloud

openinfra finops import-submit --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --idempotency-key finops-aws-2026-06-0001 --source aws-cur \
  --records-file costs.json

openinfra finops import-run --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --job-id "$JOB_ID"

openinfra finops report-generate --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --kind showback --period-start 2026-06-01 --period-end 2026-06-30 \
  --group-by application --currency EUR
```

## Persistance et exploitation

La migration `0046_finops_costs_showback.sql` crée les tables partitionnées et indexées pour les règles, imports, coûts, allocations, périodes, budgets, anomalies, prévisions, rapports et outbox. Le backend JSON fournit les mêmes contrats pour le mode local. Les événements critiques sont enregistrés dans l’outbox au sein de la transaction métier.

Avant clôture, sauvegarder la base et vérifier les imports en échec ou en attente. Après restauration, contrôler les digests des périodes clôturées avant toute nouvelle génération de rapport.

## Validation

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_finops_domain.py \
  tests/unit/test_finops_edge_cases.py \
  tests/integration/test_finops_services.py \
  tests/integration/test_finops_http_api.py \
  tests/integration/test_finops_cli.py \
  tests/integration/test_finops_migration.py \
  tests/integration/test_finops_web_contract.py

PYTHONPATH=src:. python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.10.0/09-API/OpenAPI/openapi.yaml
```
