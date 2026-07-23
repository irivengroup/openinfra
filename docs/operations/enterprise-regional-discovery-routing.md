# Discovery régionale distribuée — Enterprise

OpenInfra Enterprise route les jobs Discovery vers un proxy régional explicitement autorisé pour un triplet **région / site / VRF**. Le routage est déterministe, isolé par tenant, audité et ne contourne jamais les contrôles du service Discovery existant.

## Préconditions

- édition `enterprise` ;
- site DCIM existant ;
- proxy Discovery actif de type `network-proxy` ou `datacenter-proxy` ;
- endpoint HTTPS déclaré ;
- portée du proxy contenant exactement la portée déterministe de la route :
  `region/<region>/site/<site>/vrf/<vrf>` en minuscules ;
- jeton possédant la permission `multisite.admin`.

Les collectors `site-proxy`, inactifs, sans endpoint HTTPS ou hors portée sont rejetés. Les éditions Lite et Pro ne peuvent ni créer une route régionale ni router un job par ce mécanisme.

## Enrôlement du proxy régional

Exemple pour la région `EU-WEST`, le site `PAR1` et la VRF `PROD` :

```bash
openinfra discovery proxy-enroll-local \
  --edition enterprise \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --name eu-west-par1-prod \
  --kind network-proxy \
  --certificate-fingerprint "$OPENINFRA_AGENT_CERT_SHA256" \
  --scope region/eu-west/site/par1/vrf/prod \
  --version 0.29.103 \
  --endpoint-url https://agent-par1.example.net:8443 \
  --vault-secret-ref vault://openinfra/agents/eu-west-par1-prod
```

La commande retourne l’identifiant du collector, utilisé lors de la configuration de la route.

## Configuration et exploitation

```bash
openinfra multisite route-configure \
  --edition enterprise \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --region-code EU-WEST \
  --site-code PAR1 \
  --vrf-code PROD \
  --collector-id "$COLLECTOR_ID"

openinfra multisite routes \
  --edition enterprise \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --region-code EU-WEST \
  --site-code PAR1

openinfra multisite job-route \
  --edition enterprise \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --region-code EU-WEST \
  --site-code PAR1 \
  --vrf-code PROD \
  --job-type network-inventory \
  --target 10.20.0.0/24 \
  --idempotency-key eu-west-par1-prod-20260711-001
```

L’idempotence, les tentatives, les baux de traitement, le fencing token, les retries et la DLQ restent gérés par le moteur Discovery existant. Une route ne réalise aucun scan et n’écrit jamais directement dans le RSOT.

## API HTTP

Les cinq routes sont disponibles sous `/api/v1/multisite/regional-discovery` :

- `GET /routes` ;
- `GET /routes/get` ;
- `POST /routes/configure` ;
- `POST /routes/disable` ;
- `POST /jobs/route`.

Les contrats complets, codes d’erreur et schémas sont publiés dans les deux documents OpenAPI.

## Persistance et concurrence

La migration `0051_enterprise_regional_discovery_routing.sql` :

- étend de manière additive la contrainte des types de collectors Discovery ;
- crée `multisite_regional_discovery_routes`, partitionnée par hachage du tenant ;
- impose l’unicité du triplet tenant/région/site/VRF ;
- conserve une clé étrangère vers le collector ;
- indexe les recherches de routage, les collectors et les événements d’audit.

La reconfiguration d’un triplet réaffecte la route existante sans créer de doublon. La désactivation est logique et auditée.

## Audit et sécurité

Les événements suivants sont enregistrés :

- `multisite.regional_route.configured` ;
- `multisite.regional_route.disabled` ;
- `multisite.regional_discovery.routed`.

Le routage revalide le collector au moment de chaque soumission. Un collector désactivé, supprimé, hors portée ou dont la configuration devient invalide ne reçoit aucun nouveau job.

## Rollback

La migration est non destructive. Pour un rollback applicatif :

1. désactiver les routes avec `openinfra multisite route-disable` ;
2. terminer ou mettre en DLQ les jobs déjà soumis selon le runbook Discovery ;
3. revenir au binaire précédent ;
4. conserver la table `multisite_regional_discovery_routes` pour l’audit et une reprise ultérieure.

Aucune suppression de table n’est requise ou recommandée.
