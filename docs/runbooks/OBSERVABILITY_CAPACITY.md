# Runbook — observabilité et certification de capacité

## 1. Prérequis

- OpenInfra 0.31.4 en runtime ASGI ;
- accès privé aux endpoints `/metrics` API et web ;
- Docker Compose pour la pile locale d'observabilité ;
- pour une certification : topologie Enterprise représentative, dataset minimal, runner dédié et fenêtre de maintenance pour les scénarios de chaos ;
- runner GitHub Actions auto-hébergé en version `2.327.1` ou ultérieure pour les actions Node.js 24 utilisées par le workflow de certification.
- pour Docker Compose, reconstruire obligatoirement l'image `0.31.4` afin d'appliquer l'identité non-root `10001:10001` utilisée par le tmpfs Prometheus.

## 2. Activer la pile d'observabilité

Renseigner au minimum dans `.env` :

```dotenv
OPENINFRA_OTEL_ENABLED=true
OPENINFRA_OTEL_TRACE_SAMPLE_RATIO=0.1
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OPENINFRA_GRAFANA_ADMIN_PASSWORD=<secret-fort>
```

Démarrer ensuite les services applicatifs et la pile optionnelle :

```bash
docker compose --env-file .env --profile observability up -d \
  postgres postgres-replica pgbouncer-primary pgbouncer-replica \
  api web tempo otel-collector prometheus grafana
```

Vérifier :

```bash
curl --fail --silent http://127.0.0.1:8080/metrics | grep openinfra_build_info
curl --fail --silent http://127.0.0.1:2006/metrics | grep openinfra_build_info
curl --fail --silent http://127.0.0.1:9090/-/ready
curl --fail --silent http://127.0.0.1:3000/api/health
```

Ne pas exposer `/metrics`, Prometheus, Tempo ou Grafana directement sur Internet.

## 3. Valider la configuration hors ligne

```bash
PYTHONPATH=src:. python scripts/validate_observability.py --project-root .
python -m pytest -q --no-cov \
  tests/unit/test_observability_runtime.py \
  tests/unit/test_capacity_certification.py \
  tests/unit/test_capacity_tooling.py \
  tests/integration/test_observability_interfaces.py
```

Cette validation contrôle les contrats, pas la disponibilité réelle des images ni une certification de capacité.

## 4. Diagnostiquer les métriques

Contrôler en priorité :

- `openinfra_http_request_duration_seconds` ;
- `openinfra_http_requests_total` ;
- `openinfra_http_requests_in_flight` ;
- `openinfra_async_queue_depth` et `openinfra_async_oldest_ready_age_seconds` ;
- `openinfra_worker_runs_total` et `openinfra_outbox_dispatch_total` ;
- `openinfra_db_pool_state` ;
- `openinfra_db_replica_lag_seconds` et `openinfra_db_replica_eligible` ;
- `openinfra_process_resident_memory_bytes` et `openinfra_process_cpu_seconds`.

Une DLQ non vide, une file prête vieillissante, une attente de pool ou une réplique inéligible doit être traitée avant d'augmenter la capacité.

## 5. Préparer une certification Enterprise

Créer une preuve de topologie protégée conforme à ce schéma :

```json
{
  "edition": "enterprise",
  "api_instances": 2,
  "web_instances": 2,
  "specialized_workers": 4,
  "database_primaries": 1,
  "database_replicas": 1,
  "pgbouncer_instances": 2,
  "regions": 1,
  "dataset_objects": 100000,
  "dataset_relations": 100000,
  "topology_fingerprint": "<sha256-ou-identifiant-immuable>"
}
```

Les cinq phases de charge doivent être exécutées avec les durées du profil versionné. Exemple non certifiant à durée réduite :

```bash
PYTHONPATH=src:. python scripts/run_enterprise_capacity_profile.py \
  --base-url https://openinfra.example \
  --metrics-url https://openinfra.example/metrics \
  --stage baseline --duration-seconds 60 --concurrency 20 --target-rps 10 \
  --output build/capacity/stages/baseline.json
```

Une durée réduite est utile pour un smoke test mais ne remplace pas le profil officiel.

## 6. Exécuter les scénarios de chaos

Le runner Compose n'accepte que les scénarios et services préautorisés. Exemple :

```bash
PYTHONPATH=src:. python scripts/run_enterprise_chaos_profile.py \
  --scenario api-worker-loss \
  --health-url https://openinfra.example/ready \
  --integrity-url https://openinfra.example/api/v1/version \
  --output build/capacity/chaos/api-worker-loss.json
```

Exécuter les quatre scénarios : `api-worker-loss`, `web-worker-loss`, `db-replica-loss`, `pgbouncer-restart`.

## 7. Assembler et certifier

```bash
PYTHONPATH=src:. python scripts/assemble_enterprise_capacity_evidence.py \
  --profile docs/operations/enterprise-capacity-profile.json \
  --topology build/capacity/topology.json \
  --stages build/capacity/stages \
  --chaos build/capacity/chaos \
  --output build/capacity/evidence.json

PYTHONPATH=src:. python scripts/certify_enterprise_capacity.py \
  --evidence build/capacity/evidence.json \
  --output build/capacity/certification-report.json \
  --enforce
```

Un rapport `status=rejected` est bloquant. Il ne doit pas être renommé, contourné ou remplacé par un benchmark local.

## 8. GitHub Actions

Le workflow `enterprise-capacity.yml` est manuel et requiert :

- un runner portant le label `openinfra-enterprise-capacity` ;
- un environnement protégé `enterprise-capacity` ;
- `OPENINFRA_CAPACITY_BEARER_TOKEN` ;
- `OPENINFRA_CAPACITY_TOPOLOGY_JSON` ;
- les URLs HTTPS de base, métriques et intégrité.

Les preuves sont publiées comme artefact avec une rétention de 90 jours.

## 9. Rollback

```bash
docker compose --env-file .env --profile observability stop \
  grafana prometheus otel-collector tempo
```

Puis définir `OPENINFRA_OTEL_ENABLED=false` et redémarrer API/web. Aucun rollback de base de données n'est requis.
