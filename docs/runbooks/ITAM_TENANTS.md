# Runbook — Tenants ITAM

## Objectif

Le référentiel des tenants ITAM permet de segmenter les données ITAM par périmètre opératoire tout en conservant un comportement simple pour les installations mono-tenant.

## Commandes opérateur

Lister les tenants actifs :

```bash
openinfra itam tenants --tenant default --admin-token "$OPENINFRA_ADMIN_TOKEN"
```

Créer un tenant et le définir comme défaut :

```bash
openinfra itam tenant-create \
  --tenant production \
  --scope-tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --name "Production" \
  --status active \
  --default
```

Modifier le tenant par défaut :

```bash
openinfra itam tenant-update \
  --tenant production \
  --scope-tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --default
```

Retirer logiquement un tenant :

```bash
openinfra itam tenant-delete \
  --tenant production \
  --scope-tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN"
```

## Règles de sécurité et de cohérence

- Le retrait est logique : le tenant passe en `retired`, sans suppression physique.
- Un tenant `suspended` ou `retired` ne peut pas devenir tenant par défaut.
- Lorsqu’un tenant devient défaut, les autres tenants perdent automatiquement le drapeau `is_default`.
- Si un seul tenant actif existe, le portail web le sélectionne automatiquement.
- Les opérations d’administration utilisent un tenant de sécurité `scope_tenant_id`, par défaut `default`, pour éviter de dépendre du tenant en cours de création.

## API

- `GET /api/v1/itam/tenants`
- `GET /api/v1/itam/tenant`
- `POST /api/v1/itam/tenant/create`
- `POST /api/v1/itam/tenant/update`
- `POST /api/v1/itam/tenant/delete`
