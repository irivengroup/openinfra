## v0.29.61 — discovery locale Lite/Pro sans agent

OpenInfra expose une brique de planification pour la discovery locale des éditions **Lite** et **Pro**. Cette brique ne lance pas de scan réseau et ne modifie pas le RSOT : elle produit un plan auditable à revoir par l’opérateur avant toute future exécution contrôlée.

### CLI

```bash
openinfra discovery local-plan \
  --edition lite \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --name "Discovery PAR1" \
  --scope site/par1 \
  --protocol snmp \
  --target 10.20.30.20 \
  --target srv-app-01 \
  --credential-secret-ref vault://openinfra/discovery/local/par1 \
  --max-concurrency 4 \
  --rate-limit-per-minute 120
```

### API

`POST /api/v1/discovery/local-plan`

```json
{
  "tenant_id": "default",
  "actor": "operator",
  "name": "Discovery PAR1",
  "scope": "site/par1",
  "protocol": "snmp",
  "targets": ["10.20.30.20", "srv-app-01"],
  "credential_secret_ref": "vault://openinfra/discovery/local/par1",
  "max_concurrency": 4,
  "rate_limit_per_minute": 120
}
```

### Garde-fous contractuels

- `dry_run=true` systématique.
- `agent_required=false`.
- `network_scan_executed=false`.
- `rsot_write_enabled=false`.
- Secrets uniquement référencés par `vault://...`.
- Protocoles bornés à `snmp`, `ssh`, `winrm`.
- Éditions autorisées : `lite`, `pro`.
- Runtime `enterprise` refusé pour ce flux local, qui doit utiliser les agents/proxy Enterprise.
