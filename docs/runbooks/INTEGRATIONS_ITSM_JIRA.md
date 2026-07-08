# Intégrations ITSM externes Jira Service Management Assets — OpenInfra v0.29.56

OpenInfra consomme Jira Service Management Assets comme système externe, sans ticketing natif interne.

## Validation du connecteur

```bash
openinfra integrations jira-validate \
  --tenant default \
  --instance-url https://tenant.atlassian.net \
  --object-type server \
  --auth-secret-ref vault://openinfra/jira/api-token
```

## Plan de synchronisation

```bash
openinfra integrations jira-asset-sync-plan \
  --tenant default \
  --resource-key SRV-PAR1-001 \
  --object-type server
```

## API

- `POST /api/v1/integrations/itsm/jira/validate`
- `POST /api/v1/integrations/itsm/jira/asset-sync-plan`

## Sécurité

- URL HTTPS obligatoire.
- Identifiants embarqués dans l’URL interdits.
- Secret seulement par référence (`auth_secret_ref`).
- `native_ticketing_enabled` reste toujours `false`.
