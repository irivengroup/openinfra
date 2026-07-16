# Diagnostic et support

Version cible : `0.33.12`

## Collecte minimale

Collecter sans secret :

```powershell
python scripts/docker_environment.py status
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=300 api web migrate auth-bootstrap postgres postgres-replica pgbouncer-primary pgbouncer-replica
```

```bash
openinfra version
openinfra database status --root installers/migrations/postgresql
```

Joindre l’heure UTC, le scénario, le résultat attendu, le code HTTP, l’identifiant de corrélation, la version et les changements récents. Expurger tokens, mots de passe, DSN, clés privées et données personnelles.

## API indisponible

1. vérifier `postgres`, `migrate`, `auth-bootstrap`, PgBouncer et `api` ;
2. consulter les logs du premier service en échec ;
3. vérifier le DSN, les secrets et les migrations ;
4. tester `GET /health` puis `GET /ready` ;
5. vérifier les budgets workers × pool PostgreSQL.

```powershell
curl.exe -f http://127.0.0.1:8080/health
curl.exe -f http://127.0.0.1:8080/ready
```

## Web indisponible

1. vérifier que l’API est prête ;
2. contrôler `OPENINFRA_WEB_BACKEND_URL` ;
3. contrôler le token BFF ;
4. consulter les logs `web` ;
5. faire un rechargement forcé uniquement après validation des assets servis.

```powershell
curl.exe -f http://127.0.0.1:2006/health
```

## PostgreSQL et migrations

```bash
openinfra database status --root installers/migrations/postgresql
openinfra database apply-migrations --root installers/migrations/postgresql --dry-run
```

Une divergence de checksum interdit de modifier le fichier déjà appliqué. Restaurer la version correcte du fichier ou la base ; ne pas forcer l’enregistrement de migration.

## Observabilité

Si les workers Prometheus échouent sur `/tmp/openinfra-prometheus` :

```powershell
docker compose --env-file .env exec api sh -c 'id && stat -c "%u:%g %a %n" /tmp/openinfra-prometheus && test -w /tmp/openinfra-prometheus'
```

Le compte attendu est `10001:10001` et le répertoire doit être inscriptible. Recréer l’image sans cache si une couche antérieure utilise encore un UID dynamique.

## Escalade

Escalader au niveau supérieur lorsque :

- l’intégrité d’audit échoue ;
- une migration diverge ;
- une perte de données est suspectée ;
- le réplica ne peut pas rattraper le primaire ;
- la DLQ contient des opérations non rejouables ;
- un secret ou une donnée sensible apparaît dans les logs ;
- le correctif exige une modification de schéma, de sécurité ou de contrat public.
