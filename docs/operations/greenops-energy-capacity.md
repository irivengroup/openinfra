# GreenOps, énergie et capacité

## Périmètre

GreenOps est intégré sous **DCIM → GreenOps**. Le module consolide les mesures énergétiques, calcule des indicateurs PUE et CO₂e, détecte les anomalies, projette les risques de capacité et produit des recommandations consultatives. Il ne pilote aucun équipement et n’applique aucun changement de production.

## Sources, mesures et unités

Une source de mesure possède un code stable, un type, un propriétaire et un état actif. Une mesure contient obligatoirement : tenant, clé d’idempotence, source, nature `observed` ou `estimated`, périmètre, site, début, fin et énergie en kWh. Les périmètres supportés sont site, salle, rack, PDU, actif et application.

Les valeurs quantitatives utilisent `Decimal` avec six décimales. Les taux de capacité et d’utilisation sont bornés entre 0 et 100. Les horodatages sont timezone-aware et normalisés en UTC. Les métadonnées sont limitées à 128 KiB, sérialisables en JSON et refusent récursivement les clés sensibles.

Une estimation reste marquée `estimated` dans les API, exports et rapports. Elle n’est jamais requalifiée en observation.

## PUE et empreinte carbone

Le PUE (Power Usage Effectiveness) est calculé à partir de l’énergie totale du site divisée par l’énergie IT lorsqu’elles sont toutes deux disponibles. À défaut, la politique du site fournit un PUE estimé et le rapport expose `pue_source=policy-estimate`.

Les facteurs carbone sont versionnés par code, région, période de validité, valeur en grammes CO₂e/kWh, source et URI facultative. Le rapport conserve le facteur exact, sa provenance et sa période. Les émissions sont des estimations calculées ; OpenInfra ne prétend pas produire une mesure réglementaire certifiée.

## Capacité et recommandations

Les seuils de politique déterminent les alertes d’énergie, refroidissement, espace et poids. Les prévisions indiquent les échantillons utilisés, la tendance, l’horizon et le niveau de risque. Les recommandations de consolidation, déplacement, revue de retrait ou revue de capacité portent toujours `requires_human_approval=true`.

Aucune recommandation ne déclenche un arrêt, un déplacement, une suppression ou une modification d’infrastructure. Une action réelle doit suivre les mécanismes de gouvernance et de changement de l’organisation.

## Idempotence et persistance

La clé d’idempotence est unique par tenant. Le registre `greenops_measurement_idempotency` lie cette clé à l’empreinte SHA-256 du contenu avant l’écriture dans une partition temporelle. Une répétition identique retourne la mesure existante ; une charge différente avec la même clé est rejetée.

La migration `0047_greenops_energy_capacity.sql` fournit les tables, partitions, index et outbox PostgreSQL. Le dépôt JSON applique les mêmes contrats pour le mode local. Les événements critiques sont enregistrés dans l’outbox de la transaction métier.

## Permissions

- `greenops.read` : consultation des sources, politiques, facteurs, mesures, rapports et analyses ;
- `greenops.write` : création des sources, facteurs, politiques et mesures ;
- `greenops.report` : génération et export des rapports ;
- `greenops.admin` : administration des politiques et référentiels GreenOps.

## CLI

```bash
openinfra greenops source-create --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --code dcim-meter --name "Compteur DCIM" --source-type dcim --owner facilities

openinfra greenops factor-create --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --code fr-2026 --region fr --grams-co2e-per-kwh 50 --source-name RTE \
  --period-start 2026-01-01 --period-end 2026-12-31

openinfra greenops policy-upsert --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --site-code par-01 --default-pue 1.40 --energy-cost-per-kwh 0.20 \
  --currency EUR --carbon-factor-code fr-2026

openinfra greenops measurement-ingest --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --idempotency-key greenops-par01-20260701 --source-code dcim-meter \
  --kind observed --scope site --scope-key par-01 --site-code par-01 \
  --period-start 2026-07-01T00:00:00+00:00 \
  --period-end 2026-07-02T00:00:00+00:00 --energy-kwh 250

openinfra greenops report-generate --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --site-code par-01 --period-start 2026-07-01 --period-end 2026-07-31
```

## API et exports

Les 16 routes sont publiées sous `/api/v1/greenops/*`. Les rapports sont exportables en JSON ou CSV. Les résultats sont isolés par tenant, paginés et bornés. Les deux documents OpenAPI doivent rester byte-alignés sur les routes et refuser toute clé YAML dupliquée.

## Exploitation et contrôle

Avant une génération de rapport :

1. vérifier que la source et la politique du site sont actives ;
2. contrôler la période du facteur carbone ;
3. distinguer les mesures observées des estimations ;
4. examiner les données manquantes et hypothèses ;
5. vérifier les alertes et la qualité des échantillons.

Après restauration PostgreSQL, contrôler le registre d’idempotence et les empreintes avant de reprendre les ingestions.

## Validation

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/unit/test_greenops_domain.py \
  tests/unit/test_greenops_edge_cases.py \
  tests/integration/test_greenops_services.py \
  tests/integration/test_greenops_cli.py \
  tests/integration/test_greenops_http_api.py \
  tests/integration/test_greenops_migration.py \
  tests/integration/test_greenops_postgresql_repository.py \
  tests/integration/test_greenops_web_contract.py

PYTHONPATH=src:. python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
```
