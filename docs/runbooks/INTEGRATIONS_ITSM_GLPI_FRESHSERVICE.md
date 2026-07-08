# Intégrations ITSM externes GLPI Inventory et Freshservice Assets — OpenInfra v0.29.57

OpenInfra consomme GLPI Inventory et Freshservice Assets comme systèmes externes de contexte. Cette livraison ne crée aucun ticketing natif interne : aucun ticket, incident, demande ou changement n’est créé dans OpenInfra.

## GLPI Inventory

### Validation du connecteur

```bash
openinfra integrations glpi-validate \
  --tenant default \
  --instance-url https://glpi.example.com \
  --item-type computer \
  --auth-secret-ref vault://openinfra/glpi/tokens
```

### Plan de synchronisation

```bash
openinfra integrations glpi-asset-sync-plan \
  --tenant default \
  --resource-key SRV-PAR1-001 \
  --item-type computer
```

### Mapping par défaut

- `resource_key -> serial`
- `display_name -> name`
- `resource_type -> itemtype`
- `entity -> entities_id`
- `source -> openinfra_source`

## Freshservice Assets

### Validation du connecteur

```bash
openinfra integrations freshservice-validate \
  --tenant default \
  --instance-url https://tenant.freshservice.com \
  --asset-type server \
  --auth-secret-ref vault://openinfra/freshservice/api-token
```

### Plan de synchronisation

```bash
openinfra integrations freshservice-asset-sync-plan \
  --tenant default \
  --resource-key SRV-PAR1-001 \
  --asset-type server
```

### Mapping par défaut

- `resource_key -> asset_tag`
- `display_name -> name`
- `resource_type -> asset_type_name`
- `asset_tag -> asset_tag`
- `source -> openinfra_source`

## API

- `POST /api/v1/integrations/itsm/glpi/validate`
- `POST /api/v1/integrations/itsm/glpi/asset-sync-plan`
- `POST /api/v1/integrations/itsm/freshservice/validate`
- `POST /api/v1/integrations/itsm/freshservice/asset-sync-plan`

## Sécurité

- URL HTTPS obligatoire.
- Identifiants embarqués dans l’URL interdits.
- Secret seulement par référence (`auth_secret_ref`).
- Les endpoints sont protégés par `security:admin` quand l'authentification API est active.
- `native_ticketing_enabled` reste toujours `false`.
