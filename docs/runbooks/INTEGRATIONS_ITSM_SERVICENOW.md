# Intégrations ITSM externes ServiceNow — OpenInfra v0.29.55

OpenInfra expose des contrats de connexion vers ServiceNow comme ITSM externe. Cette capacité ne crée aucun module natif de ticketing, incident, demande ou changement dans OpenInfra.

## CLI

```bash
openinfra integrations itsm-providers --data .openinfra.json
openinfra integrations servicenow-validate \
  --data .openinfra.json \
  --tenant default \
  --instance-url https://instance.service-now.com \
  --table-name cmdb_ci \
  --auth-secret-ref vault://openinfra/servicenow/oauth
openinfra integrations servicenow-ci-sync-plan \
  --data .openinfra.json \
  --tenant default \
  --resource-key SRV-PAR1-001
```

## API

- `GET /api/v1/integrations/itsm/providers`
- `POST /api/v1/integrations/itsm/servicenow/validate`
- `POST /api/v1/integrations/itsm/servicenow/ci-sync-plan`

## Sécurité

- Les secrets ne sont jamais saisis en clair : `auth_secret_ref` référence un coffre ou une variable sécurisée.
- Les URL ServiceNow doivent être HTTPS et ne peuvent pas inclure d'identifiants.
- Les endpoints sont protégés par `security:admin` quand l'authentification API est active.

## Mapping minimal CI

Le mapping par défaut couvre :

- `resource_key -> correlation_id`
- `display_name -> name`
- `resource_type -> sys_class_name`
- `lifecycle -> install_status`
- `source -> discovery_source`
