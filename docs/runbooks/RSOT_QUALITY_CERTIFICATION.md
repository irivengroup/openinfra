# Certification qualité RSOT — preuve TST-RSOTQUAL-046

Ce runbook couvre `TST-RSOTQUAL-046` : un objet RSOT complet, récent et alimenté par une source autoritative obtient un score de qualité supérieur ou égal à 90 et le statut `certified`.

## Invariants vérifiés

- les attributs obligatoires du type de ressource sont présents ;
- la fraîcheur est calculée à partir de `updated_at` ;
- les règles de gouvernance identifient la source autoritative par attribut ;
- une source non autoritative ne peut pas obtenir silencieusement la certification ;
- le score agrège complétude, fraîcheur, autorité et confiance ;
- le statut `certified` exige un score `>= 90` et l’absence d’erreur ou d’avertissement ;
- les lectures exigent la permission `rsot.quality.read` ;
- chaque évaluation et synthèse produit un événement d’audit ;
- service, CLI, API HTTP, portail React et portail runtime exposent le même contrat ;
- le JSON brut reste disponible sous le rapport accessible.

## Commandes

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
pytest -q tests/integration/test_contract_rsot_quality_certification.py
node --test web/tests/rsot-quality-certification.test.mjs
```
