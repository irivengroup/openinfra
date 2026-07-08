# Discovery Enterprise agent bootstrap

OpenInfra v0.29.63 prepares the future `openinfra-agent.service` runtime through a backend/CLI/API bootstrap plan. The plan is Enterprise-only and is intentionally side-effect free.

## CLI

```bash
openinfra discovery agent-bootstrap-plan \
  --tenant default \
  --admin-token "$OPENINFRA_BOOTSTRAP_TOKEN" \
  --name "Agent Enterprise PAR1" \
  --role site \
  --scope site/par1 \
  --backend-url https://openinfra-api.example.com \
  --certificate-fingerprint aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --enrollment-secret-ref vault://openinfra/discovery/agent/par1
```

## API

`POST /api/v1/discovery/agent-bootstrap-plan` returns:

- `systemd_unit_name=openinfra-agent.service`;
- hardened `systemd_unit` content;
- `config_document` with backend API publication endpoints;
- `mtls_required=true`;
- `publishes_results_via_api=true`;
- `install_executed=false`;
- `secrets_materialized=false`.

## Security guardrails

- Enterprise edition only.
- Backend URL must be HTTPS origin-only and must not embed credentials.
- Enrollment secret must remain a `vault://` reference.
- The service user must be a dedicated non-root Unix account.
- The generated unit uses `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true` and explicit writable runtime directories.
- The operator remains responsible for reviewing, installing and enabling the unit on the target host.
