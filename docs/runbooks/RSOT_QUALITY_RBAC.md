# Contrôle RBAC de la qualité RSOT — preuve TST-RSOTQUAL-047

Ce runbook couvre `TST-RSOTQUAL-047` : un rôle ne possédant pas la permission `rsot.quality.read` ne peut consulter ni l’évaluation d’un objet RSOT ni une synthèse de qualité.

## Invariants de sécurité

- le contrôle d’autorisation est exécuté avant toute lecture du repository RSOT ;
- les commandes `quality-object` et `quality-summary` exigent toutes deux `rsot.quality.read` ;
- un jeton valide associé uniquement au rôle `dcim:operator` est refusé par le service, la CLI et l’API HTTP ;
- aucune clé d’objet, aucun nom affiché, aucun numéro de série, score ou statut de certification n’est renvoyé au rôle refusé ;
- une tentative refusée ne produit aucun événement d’évaluation ou de synthèse et ne modifie pas l’état persistant ;
- la CLI retourne un code non nul et n’écrit aucun résultat sur la sortie standard ;
- l’API retourne une réponse d’authentification refusée générique ;
- les portails React et runtime exécutent réellement les opérations qualité contre le backend protégé, sans jeton d’administration embarqué dans le navigateur ;
- une réponse HTTP refusée ne peut pas être présentée comme une opération réussie.

## Vérification CLI

```bash
openinfra rsot quality-object \
  --backend postgresql \
  --tenant default \
  --admin-token "$TOKEN_SANS_RSOT_QUALITY_READ" \
  --key device/core-router-01

test "$?" -ne 0
```

```bash
openinfra rsot quality-summary \
  --backend postgresql \
  --tenant default \
  --admin-token "$TOKEN_SANS_RSOT_QUALITY_READ" \
  --kind device

test "$?" -ne 0
```

## Vérification API

```http
GET /api/v1/rsot/quality/object?tenant_id=default&key=device/core-router-01
Authorization: Bearer <token-sans-rsot.quality.read>
```

La réponse attendue est un refus générique sans donnée RSOT dans le corps.

## Validation automatisée

```bash
python -m pytest -q --no-cov \
  tests/integration/test_contract_rsot_quality_rbac.py

node --test web/tests/rsot-quality-rbac.test.mjs
```
