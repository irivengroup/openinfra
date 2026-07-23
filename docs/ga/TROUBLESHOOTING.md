# Diagnostic et support

Version cible : `0.34.20`

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
## PostgreSQL — erreur `identity_team_sync_sources_p 0` pendant la migration 0057

Cette erreur concerne uniquement la version 0.34.0. PostgreSQL `format()` applique une largeur minimale à `%s` en ajoutant des espaces ; `%1$02s` produit donc `p 0` et non `p00`. La version 0.34.2 utilise `lpad()` pour le suffixe et `%I` pour l’identifiant SQL.

La migration est exécutée dans la transaction de l’exécuteur OpenInfra. Après l’échec, aucune partition 0057 ni entrée `openinfra_schema_migrations` ne doit être réparée manuellement. Mettez à niveau le package puis relancez les migrations.

Déploiement serveur standard :

```bash
sudo /opt/openinfra/venv/bin/python -m pip install --upgrade /opt/openinfra/releases/openinfra-0.34.20-py3-none-any.whl
sudo systemctl start openinfra-migrate.service
sudo journalctl -u openinfra-migrate.service --no-pager --since today
```

Environnement Docker local :

```bash
docker compose --env-file .env up --build -d postgres migrate
docker compose --env-file .env logs --no-color --tail=200 migrate
```

Vérifiez ensuite que `0057_federated_identity_team_sync.sql` apparaît dans l’état du schéma et que les partitions vont de `p00` à `p31`.

