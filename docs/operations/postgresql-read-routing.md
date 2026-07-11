# PgBouncer, réplication et routage lecture/écriture

## Périmètre

Cette architecture s’applique aux éditions Pro et Entreprise. Lite reste sur une connexion primaire locale sans standby obligatoire.

## Flux

- les migrations, écritures, allocations, leases et mutations IAM utilisent toujours le primaire ;
- les requêtes HTTP `GET` et `HEAD` sont éligibles au standby ;
- le standby n’est utilisé que lorsque `pg_is_in_recovery()` est vrai et que le lag de replay reste inférieur au seuil configuré ;
- une réplique indisponible ou trop en retard provoque un fallback vers le primaire lorsque la politique l’autorise ;
- le mode strict refuse la lecture plutôt que de masquer l’indisponibilité.

Chaque requête de lecture utilise une portée transactionnelle unique. Les repositories conservent donc leur invariant d’unité de travail, et les lectures multiples d’une même requête partagent la même connexion et le même snapshot.

## Cohérence lecture-après-écriture

Après une mutation réussie, l’API émet `X-OpenInfra-Consistency-Token`. Le BFF le conserve dans un cookie `HttpOnly`, `SameSite=Strict`, limité au chemin `/api`, puis le retransmet aux lectures suivantes. Tant que le jeton HMAC-SHA256 est valide, la lecture est forcée sur le primaire. Il ne contient aucune donnée métier ni secret.

Le secret `OPENINFRA_READ_CONSISTENCY_SECRET` doit contenir au moins 32 caractères aléatoires, être injecté depuis un gestionnaire de secrets et être identique sur tous les workers API.

## Paramètres essentiels

```ini
OPENINFRA_DB_READ_ROUTING_ENABLED=true
OPENINFRA_DB_MAX_REPLICA_LAG_SECONDS=5
OPENINFRA_DB_REPLICA_PROBE_INTERVAL_SECONDS=2
OPENINFRA_DB_READ_FALLBACK_TO_PRIMARY=true
OPENINFRA_DB_READ_REQUIRE_RECOVERY=true
OPENINFRA_READ_AFTER_WRITE_TTL_SECONDS=10
```

## Supervision

```bash
curl -H "Authorization: Bearer $OPENINFRA_TOKEN" \
  "https://openinfra.example/api/v1/database/routing?tenant_id=default"
```

Surveiller :

- `replica.eligible` ;
- `replica.lag_seconds` ;
- `counters.replica_fallbacks` ;
- saturation PgBouncer et temps d’attente du pool ;
- divergence entre le budget PgBouncer et `max_connections` PostgreSQL.

## Déploiement et mise à niveau

Le service `replication-bootstrap` crée ou remet en conformité le rôle de réplication et la règle `pg_hba.conf` dédiée à chaque déploiement. Cette étape fonctionne aussi avec un volume primaire existant. Un volume standby vide est initialisé par `pg_basebackup`; un volume déjà initialisé est conservé.

Ne jamais réutiliser le volume primaire pour le standby. Avant suppression d’un volume standby, vérifier qu’il ne contient aucune donnée unique et qu’un nouveau base backup peut être produit.

## Rollback

1. Définir `OPENINFRA_DB_READ_ROUTING_ENABLED=false`.
2. Redémarrer uniquement l’API ; toutes les lectures reviennent au primaire.
3. Conserver PgBouncer primaire et le standby pour diagnostic.
4. Ne supprimer le volume standby qu’après validation d’une reconstruction complète.

Le rollback ne nécessite aucune migration et ne modifie aucune donnée métier.

## Réparation d’un déploiement 0.30.1

L’erreur `no pg_hba.conf entry for replication connection` est corrigée en 0.30.4. Conserver le volume primaire, recréer le réseau Compose puis reconstruire le standby :

```powershell
docker compose --env-file .env down --remove-orphans
docker volume rm openinfra-runtime_openinfra-postgres-replica-data 2>$null
docker compose --env-file .env up --build -d postgres replication-bootstrap postgres-replica pgbouncer-primary pgbouncer-replica migrate auth-bootstrap api web pgadmin
```

Ne jamais supprimer `openinfra-postgres-data` pendant cette réparation. Le sous-réseau `OPENINFRA_DOCKER_SUBNET` doit être libre sur l’hôte ; sa valeur par défaut est `172.30.0.0/24`.
