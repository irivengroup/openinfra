# Runbook — Réconciliation Discovery multisource

## Objet

Ce runbook décrit l’enregistrement de preuves Discovery immuables, leur rapprochement, la résolution gouvernée des conflits et les contrôles d’exploitation. Le workflow ne modifie jamais automatiquement le RSOT.

## Préconditions

- migration PostgreSQL `0038_discovery_multisource_reconciliation.sql` appliquée ;
- token disposant de `rsot:governance:write` pour soumettre, rapprocher et résoudre ;
- token disposant de `rsot:governance:read` pour consulter et lister ;
- horodatages ISO-8601 avec fuseau, de préférence UTC ;
- payload JSON sans secret, mot de passe, jeton, clé privée ou secret client.

## Contrat de sécurité

Les preuves sont immuables. Une nouvelle observation produit un nouvel identifiant et une nouvelle empreinte. Le payload est limité à 1 MiB, validé récursivement et n’est pas copié dans l’audit. Les références de source servent à identifier le collecteur ou connecteur, jamais à transporter un secret.

Le rapprochement exige au moins deux preuves provenant de deux identités de source distinctes et concernant la même clé et le même type d’objet. Il produit une décision gouvernée avec `rsot_write_executed=false`.

## Workflow CLI

Configurer les paramètres de session :

```bash
export OPENINFRA_DATA=/var/lib/openinfra/openinfra.json
export OPENINFRA_TENANT=default
export OPENINFRA_ADMIN_TOKEN='token-fourni-par-le-vault'
```

Soumettre une preuve VMware :

```bash
openinfra discovery evidence-submit \
  --backend json \
  --data "$OPENINFRA_DATA" \
  --tenant "$OPENINFRA_TENANT" \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor discovery-vcenter-par1 \
  --object-key server/srv-app-01 \
  --object-kind server \
  --source vmware \
  --source-ref vcenter-par1 \
  --scope site/par1 \
  --external-id vm-421 \
  --confidence 0.95 \
  --observed-at 2026-07-10T20:00:00+00:00 \
  --payload-json '{"hostname":"srv-app-01","cpu":{"cores":8},"memory_gib":32}'
```

Soumettre une preuve Kubernetes sur le même objet :

```bash
openinfra discovery evidence-submit \
  --backend json \
  --data "$OPENINFRA_DATA" \
  --tenant "$OPENINFRA_TENANT" \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor discovery-k8s-par1 \
  --object-key server/srv-app-01 \
  --object-kind server \
  --source kubernetes \
  --source-ref cluster-k8s-par1 \
  --scope site/par1 \
  --external-id node-srv-app-01 \
  --confidence 0.88 \
  --observed-at 2026-07-10T20:01:00+00:00 \
  --payload-json '{"hostname":"srv-app-01","cpu":{"cores":16},"memory_gib":32}'
```

Lister les preuves et relever leurs identifiants :

```bash
openinfra discovery evidence-list \
  --backend json \
  --data "$OPENINFRA_DATA" \
  --tenant "$OPENINFRA_TENANT" \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --object-key server/srv-app-01 \
  --limit 100
```

Créer le cas de rapprochement, en répétant `--evidence-id` :

```bash
openinfra discovery reconcile \
  --backend json \
  --data "$OPENINFRA_DATA" \
  --tenant "$OPENINFRA_TENANT" \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor rsot-governance \
  --object-key server/srv-app-01 \
  --evidence-id 11111111-1111-4111-8111-111111111111 \
  --evidence-id 22222222-2222-4222-8222-222222222222 \
  --max-age-seconds 86400
```

Pour un conflit `cpu.cores`, sélectionner explicitement la preuve retenue :

```bash
openinfra discovery reconciliation-resolve \
  --backend json \
  --data "$OPENINFRA_DATA" \
  --tenant "$OPENINFRA_TENANT" \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor rsot-governance \
  --case-id 33333333-3333-4333-8333-333333333333 \
  --selections-json '{"cpu.cores":"11111111-1111-4111-8111-111111111111"}' \
  --justification 'La capacité VMware est la source contractuelle validée pour les cœurs physiques.'
```

Les UUID ci-dessus illustrent le format attendu ; en exploitation, utiliser exclusivement les identifiants retournés par OpenInfra.

## API HTTP

Les endpoints sont :

- `POST /api/v1/discovery/evidence` ;
- `GET /api/v1/discovery/evidence` ;
- `GET /api/v1/discovery/evidence-list` ;
- `POST /api/v1/discovery/reconciliation` ;
- `GET /api/v1/discovery/reconciliation` ;
- `GET /api/v1/discovery/reconciliation-list` ;
- `POST /api/v1/discovery/reconciliation/resolve`.

Le contrat complet, les champs obligatoires et les codes de réponse sont publiés dans `docs/api/openapi.yaml`, Swagger UI et ReDoc.

## Calcul de qualité

Le score global est déterministe : 60 % confiance déclarée, 25 % fraîcheur et 15 % complétude. La fraîcheur décroît linéairement jusqu’à zéro à l’âge maximal configuré. La complétude correspond au ratio de feuilles JSON renseignées.

Le score aide l’opérateur mais ne tranche jamais silencieusement une divergence. Toute valeur conflictuelle doit être sélectionnée explicitement.

## Exploitation PostgreSQL

Les tables `discovery_evidence` et `discovery_reconciliation_cases` sont partitionnées par hash du tenant en 16 partitions. Les requêtes sont indexées par objet, source, statut et date. Le payload JSON dispose d’un index GIN. Les listes sont paginées par curseur.

Contrôles après migration :

```sql
SELECT count(*) FROM pg_inherits
WHERE inhparent IN ('discovery_evidence'::regclass, 'discovery_reconciliation_cases'::regclass);

SELECT conname
FROM pg_constraint
WHERE conname = 'discovery_reconciliation_no_direct_rsot_write';
```

Le premier contrôle doit retourner 32 partitions et le second la contrainte interdisant `rsot_write_executed=true`.

## Incidents et reprise

- **Payload refusé** : retirer tout secret et corriger les clés JSON non sûres ; ne jamais contourner la validation.
- **Preuve déjà existante avec contenu différent** : conserver l’ancienne preuve et soumettre une nouvelle preuve avec un nouvel UUID.
- **Sources insuffisantes** : ajouter une preuve issue d’une identité de source distincte.
- **Résolution incomplète** : fournir une sélection valide pour chaque `attribute_path` conflictuel.
- **Cas déjà résolu** : ne pas le rouvrir ; soumettre de nouvelles preuves et créer un nouveau cas.
- **Échec transactionnel** : aucune écriture partielle n’est validée ; relancer la commande idempotente.

## Validation

```bash
ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
pytest -q --no-cov tests/unit/test_discovery_domain.py tests/integration/test_discovery_reconciliation.py
pytest -q --no-cov tests/integration/test_cli_discovery.py tests/integration/test_http_api.py tests/integration/test_openinfra_web.py
pytest -q --no-cov tests/integration/test_postgresql_migration.py tests/integration/test_postgresql_migration_policy.py
```
