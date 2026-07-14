# OpenInfra — Observabilité multisite P17 / EPIC-1705

## Objectif

Cette procédure active une vue SRE par site pour les éditions Pro et Enterprise sans créer une seconde source de vérité. Chaque backend OpenInfra conserve ses métriques locales. Le Prometheus central fédère les endpoints `/metrics` des sites configurés et ajoute uniquement trois labels bornés : `region`, `site` et `service`.

Les signaux obligatoires sont : disponibilité API, latence API, heartbeat des agents Discovery, lag de réplication PostgreSQL, files de jobs et santé opérationnelle du site.

## Sécurité et cardinalité

- Les cibles multisites sont collectées en HTTPS uniquement.
- Les redirections HTTP sont refusées.
- Le fichier de découverte ne contient aucun secret, jeton ou identifiant utilisateur.
- Les labels autorisés sont exactement `region`, `site` et `service`.
- Les identifiants de tenant ne sont jamais exportés comme labels Prometheus.
- Le provider backend est borné à 10 000 routes Discovery actives et déduplique les agents utilisés par plusieurs VRF d’un même site.
- Le répertoire des cibles est monté en lecture seule dans Prometheus.

## Configuration du tenant observé

Le backend calcule le lag des agents depuis les heartbeats Discovery persistés pour le tenant d’observabilité :

```dotenv
OPENINFRA_OBSERVABILITY_TENANT_ID=default
OPENINFRA_MULTISITE_AGENT_STALE_AFTER_SECONDS=120
```

La valeur `OPENINFRA_MULTISITE_AGENT_STALE_AFTER_SECONDS` doit être comprise entre 10 et 86 400 secondes.

## Déclaration des cibles multisites

Créer un fichier JSON dans `docker/observability/multisite-targets/`. Exemple de structure :

```json
[
  {
    "targets": ["par1.openinfra.internal:443"],
    "labels": {
      "region": "EU-WEST",
      "site": "PAR1",
      "service": "openinfra-api"
    }
  },
  {
    "targets": ["lon1.openinfra.internal:443"],
    "labels": {
      "region": "EU-WEST",
      "site": "LON1",
      "service": "openinfra-api"
    }
  }
]
```

Valider le fichier avant déploiement :

```bash
python scripts/validate_multisite_observability.py \
  --project-root . \
  --targets docker/observability/multisite-targets/sites.json
```

Chaque cible est un `host:port` sans schéma ni chemin. Le job Prometheus impose `https` et `/metrics`.

## Démarrage

```bash
docker compose --env-file .env --profile observability down --volumes --remove-orphans && docker compose --env-file .env --profile observability up --build -d
```

Vérifier les services :

```bash
docker compose --env-file .env --profile observability ps
```

## Dashboard

Grafana provisionne automatiquement le dashboard `OpenInfra Multisite Operations` (`uid=openinfra-multisite-operations`). Les variables `Region` et `Site` filtrent :

- disponibilité de l’API ;
- p95 HTTP ;
- ratio d’erreurs 5xx ;
- retard maximal des heartbeats agents ;
- santé agrégée des agents ;
- lag PostgreSQL ;
- âge du plus ancien job prêt ;
- profondeur des files par statut.

## Alertes

Les alertes bloquantes ou opérationnelles suivantes sont provisionnées :

- `OpenInfraMultisiteApiUnavailable` ;
- `OpenInfraMultisiteApiP95LatencyHigh` ;
- `OpenInfraMultisiteAgentLagHigh` ;
- `OpenInfraMultisiteAgentUnhealthy` ;
- `OpenInfraMultisiteDatabaseLagHigh` ;
- `OpenInfraMultisiteJobsStalled`.

Les seuils du profil v1 sont :

| Signal | Seuil |
|---|---:|
| Heartbeat agent | 120 s |
| Lag réplica PostgreSQL | 5 s |
| API p95 | 0,5 s |
| Plus ancien job prêt | 300 s |

Le contrat machine-readable est `docs/operations/multisite-observability-profile.json`.

## Diagnostic

### Une cible est `down`

1. Vérifier la résolution DNS et la connectivité TCP depuis le conteneur Prometheus.
2. Vérifier le certificat TLS présenté par la cible.
3. Vérifier que `/metrics` répond sans redirection.
4. Vérifier que les labels `region`, `site` et `service` sont présents dans le fichier de découverte.

### Le lag agent est élevé

1. Vérifier le dernier heartbeat du collector concerné dans Discovery.
2. Vérifier l’état du service `openinfra-agent.service` sur le site.
3. Vérifier la connectivité agent → backend et l’identité mTLS utilisée par l’agent.
4. Vérifier les routes régionales actives ; un même agent utilisé par plusieurs VRF n’est compté qu’une fois par région/site.

### Les métriques DB ou jobs sont absentes

Vérifier que la cible correspond bien au backend API du site et qu’elle exécute la version OpenInfra attendue. Les métriques DB et files sont produites par le backend local puis enrichies avec les labels de site lors du scrape central.

## Validation projet

```bash
python scripts/validate_multisite_observability.py --project-root .
python scripts/validate_observability.py --project-root .
python -m pytest tests/unit/test_multisite_observability_runtime.py tests/integration/test_multisite_observability_contract.py
```

La CI doit rester bloquante si les métriques, alertes, dashboard, profil, montage Prometheus ou bornes de cardinalité ne sont plus cohérents.
