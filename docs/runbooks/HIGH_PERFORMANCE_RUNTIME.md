# Runbook — Runtime haute performance Pro et Entreprise

## Variables API

```ini
OPENINFRA_API_RUNTIME=asgi
OPENINFRA_API_WORKERS=0
OPENINFRA_API_LIMIT_CONCURRENCY=1000
OPENINFRA_API_BACKLOG=2048
OPENINFRA_API_KEEPALIVE_SECONDS=5
OPENINFRA_DB_POOL_MIN_SIZE=1
OPENINFRA_DB_POOL_MAX_SIZE=8
OPENINFRA_DB_POOL_TIMEOUT_SECONDS=5
OPENINFRA_DB_POOL_MAX_IDLE_SECONDS=300
OPENINFRA_DB_POOL_MAX_LIFETIME_SECONDS=1800
OPENINFRA_DB_CONNECTION_BUDGET=80
```

Pour Entreprise, les valeurs initiales sont `pool min=2`, `pool max=12`, `budget=192`. `OPENINFRA_API_WORKERS=0` active la politique automatique bornée par édition.

## Variables Web

```ini
OPENINFRA_WEB_RUNTIME=asgi
OPENINFRA_WEB_WORKERS=0
OPENINFRA_WEB_LIMIT_CONCURRENCY=1000
OPENINFRA_WEB_BACKLOG=2048
OPENINFRA_WEB_KEEPALIVE_SECONDS=5
OPENINFRA_WEB_HTTP_MAX_CONNECTIONS=200
OPENINFRA_WEB_HTTP_MAX_KEEPALIVE_CONNECTIONS=50
OPENINFRA_WEB_HTTP_KEEPALIVE_EXPIRY_SECONDS=30
OPENINFRA_WEB_HTTP_CONNECT_TIMEOUT_SECONDS=2
OPENINFRA_WEB_HTTP_READ_TIMEOUT_SECONDS=30
OPENINFRA_WEB_HTTP_WRITE_TIMEOUT_SECONDS=30
OPENINFRA_WEB_HTTP_POOL_TIMEOUT_SECONDS=2
```

Entreprise utilise initialement 500 connexions HTTP et 100 keep-alive par worker Web. Ces valeurs doivent être réduites si le backend ou le load balancer possède une capacité inférieure.

## Validation avant redémarrage

1. Calculer le budget total PostgreSQL sur tous les réplicas.
2. Réserver des connexions distinctes pour migrations, supervision et administration.
3. Vérifier mémoire et descripteurs de fichiers.
4. Vérifier que le BFF n’accède jamais directement à PostgreSQL.
5. Exécuter les tests ciblés :

```bash
python -m pytest -q --no-cov \
  tests/integration/test_asgi_performance_runtime.py \
  tests/performance/test_high_performance_runtime_benchmark.py
PYTHONPATH=src:. python scripts/benchmark_high_performance_runtime.py \
  --requests 500 --concurrency 50 --warmups 25 \
  --output build/reports/high-performance-runtime.json --enforce
python scripts/quality_gate.py
```

## Démarrage

```bash
systemctl daemon-reload
systemctl restart openinfra.service
systemctl restart openinfra-web.service
systemctl status openinfra.service openinfra-web.service
```

## Signaux à surveiller

- p95 et p99 par route ;
- requêtes en vol et réponses 429/503 ;
- attente et timeout du pool PostgreSQL ;
- connexions utilisées/disponibles ;
- saturation CPU, mémoire et threadpool ;
- taux de réutilisation keep-alive BFF ;
- erreurs réseau et délais connect/read/write ;
- lag des réplicas dès leur activation.

## Rollback contrôlé

Configurer temporairement :

```ini
OPENINFRA_API_RUNTIME=legacy
OPENINFRA_API_WORKERS=1
OPENINFRA_WEB_RUNTIME=legacy
OPENINFRA_WEB_WORKERS=1
```

Puis redémarrer les services. Ce mode ne doit pas être utilisé comme solution de dimensionnement Pro/Entreprise. Conserver le pool PostgreSQL désactivé uniquement si l’incident est explicitement lié au pool ; documenter alors le risque de saturation et réduire la concurrence en amont.

## Critères de sortie d’incident

- erreurs techniques revenues sous 0,1 % au débit nominal ;
- p95/p99 dans le SLO ;
- aucune fuite de connexion après endurance ;
- pool sous 80 % en régime stable ;
- cause racine et correction validées avant retour ASGI.

## Portée du benchmark P19

Le benchmark ci-dessus est un gate de régression du transport ASGI. Il doit produire `capacity_certification=false`. Il ne valide ni la capacité PostgreSQL, ni le dimensionnement final des pools, ni l’endurance d’une topologie Pro/Entreprise. Ces validations sont obligatoires en P20 sur l’infrastructure cible ou un environnement représentatif.
