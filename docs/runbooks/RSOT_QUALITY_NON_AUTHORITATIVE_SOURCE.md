# Source non autoritative et qualité RSOT — preuve TST-RSOTQUAL-048

Ce runbook couvre `TST-RSOTQUAL-048` : lorsqu’un attribut RSOT est alimenté par une source différente de celle déclarée autoritative par la gouvernance, l’évaluation qualité produit un avertissement explicite et visible sur tous les canaux.

## Invariants vérifiés

- la règle de gouvernance est résolue pour le type d’objet et le chemin d’attribut, y compris un chemin imbriqué ;
- une donnée présente sur ce chemin et portée par une autre source génère le code stable `non_authoritative_source` ;
- le finding expose le champ gouverné, la source observée, la source attendue et le nom de la règle ;
- le score d’autorité est dégradé de manière déterministe et le statut ne peut pas rester `certified` ;
- la synthèse tenant comptabilise l’objet dans `warning` ;
- service applicatif, CLI, API HTTP, portail React et portail runtime exposent le même diagnostic ;
- l’objet RSOT et ses attributs restent inchangés pendant les lectures qualité ;
- les événements d’audit enregistrent le score d’autorité et le nombre de findings non autoritatifs ;
- la permission `rsot.quality.read` reste obligatoire.

## Préparation de la gouvernance

```bash
openinfra rsot governance-rule-create \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --name hardware-serial-authority \
  --object-kind device \
  --attribute-path hardware.serial_number \
  --authoritative-source inventory.cmdb \
  --priority 100 \
  --conflict-strategy reject
```

## Évaluation CLI

```bash
openinfra rsot quality-object \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --key device/core-router-01

openinfra rsot quality-summary \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --kind device \
  --limit 100
```

Le finding attendu contient au minimum :

```json
{
  "severity": "warning",
  "code": "non_authoritative_source",
  "field": "hardware.serial_number",
  "expected_source": "inventory.cmdb",
  "actual_source": "discovery.snmp",
  "governance_rule": "hardware-serial-authority"
}
```

## API

```http
GET /api/v1/rsot/quality/object?tenant_id=default&key=device/core-router-01
Authorization: Bearer <token>
```

```http
GET /api/v1/rsot/quality/summary?tenant_id=default&kind=device&limit=100
Authorization: Bearer <token>
```

## Validation automatisée

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/integration/test_contract_rsot_quality_non_authoritative.py
node --test web/tests/rsot-quality-non-authoritative.test.mjs
```
