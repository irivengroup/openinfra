# Intégration future OpenService — OpenInfra v0.29.58

OpenService est prévu comme solution ITSM/CMDB autonome, développée dans un projet distinct après OpenInfra. OpenInfra v0.29.58 ne développe aucune fonctionnalité OpenService ; elle prépare uniquement le contrat de raccordement futur côté OpenInfra Pro et Enterprise.

## Frontière produit

- OpenInfra reste RSOT, IPAM, DCIM, ITAM et référentiel d’infrastructure.
- OpenService portera son propre périmètre ITSM et sa propre interface web.
- `openinfra-web` ne doit pas embarquer d’écran OpenService.
- OpenInfra ne crée aucun ticket, incident, demande, changement, SLA ou workflow ITSM natif.

## Commandes CLI

```bash
openinfra integrations openservice-validate \
  --tenant default \
  --instance-url https://openservice.example.com \
  --collection configuration_item \
  --auth-secret-ref vault://openinfra/openservice/oauth

openinfra integrations openservice-cmdb-sync-plan \
  --tenant default \
  --resource-key SRV-PAR1-001 \
  --collection configuration_item
```

## API HTTP

- `POST /api/v1/integrations/itsm/openservice/validate`
- `POST /api/v1/integrations/itsm/openservice/cmdb-sync-plan`

Quand l’authentification HTTP est active, ces routes exigent `security:admin`.

## Collections OpenService bornées

Le CDC OpenService futur précisera le modèle complet. Côté OpenInfra, seules les collections d’échange stables sont admises pour éviter un couplage prématuré :

- `configuration_item`
- `asset`
- `relationship`
- `service`
- `software`
- `contract`

## Sécurité

- URL HTTPS obligatoire.
- Credentials interdits dans l’URL.
- Secrets uniquement par référence `auth_secret_ref`.
- Aucun secret ou token en clair dans CLI/API/logs.
- `native_ticketing_enabled` reste `false`.
- `openinfra_web_ui_enabled` reste `false`.

## Validation

Les tests couvrent :

- domaine fournisseur/alias/politique ;
- validation de profil OpenService ;
- plan CMDB déterministe ;
- CLI ;
- API HTTP protégée ;
- discovery ;
- OpenAPI ;
- non-exposition dans `openinfra-web`.
