# Guide d’exploitation

Version cible : `0.33.0`

## Démarrage et arrêt

Démarrage standard :

```powershell
python scripts/docker_environment.py up
```

Démarrage avec observabilité :

```powershell
docker compose --env-file .env --profile observability up --build -d
```

Arrêt sans suppression des données :

```powershell
python scripts/docker_environment.py down
```

Ne jamais utiliser `down --volumes` pendant une maintenance ordinaire.

## Supervision

```powershell
python scripts/docker_environment.py status
curl.exe -f http://127.0.0.1:8080/ready
curl.exe -f http://127.0.0.1:2006/health
```

Journal applicatif :

```powershell
docker compose --env-file .env logs -f --tail=200 api web migrate auth-bootstrap
```

Journal base et pooling :

```powershell
docker compose --env-file .env logs -f --tail=200 postgres postgres-replica pgbouncer-primary pgbouncer-replica
```

Sur runtime natif :

```bash
journalctl -u openinfra.service -f
journalctl -u openinfra-web.service -f
journalctl -u openinfra-agent.service -f
```

## Sauvegardes

Les sauvegardes doivent couvrir :

- PostgreSQL avec capacité PITR ;
- `/opt/openinfra/config` ;
- les certificats et références de secrets ;
- le stockage d’artefacts asynchrones ;
- les manifestes et rapports de release ;
- les preuves d’audit selon la politique de rétention.

Chaque sauvegarde doit être chiffrée, contrôlée par checksum, répliquée hors site et restaurée périodiquement sur une cible isolée.

## Maintenance

Avant intervention :

1. vérifier `/ready`, le lag du réplica, la DLQ et les jobs actifs ;
2. geler les mutations si l’intervention l’exige ;
3. prendre et vérifier la sauvegarde ;
4. enregistrer la version et le manifeste SHA-256 ;
5. exécuter la procédure de mise à niveau ;
6. lancer les smokes et réouvrir le trafic.

Validation générale :

```powershell
python scripts/docker_environment.py validate
```

## Incidents courants

- API non prête : vérifier migrations, PgBouncer et DSN primaire.
- Web en erreur : vérifier la santé API, le token BFF et `OPENINFRA_WEB_BACKEND_URL`.
- DLQ croissante : suspendre les rejeux automatiques et analyser le dernier échec.
- Réplica trop en retard : router les lectures vers le primaire et traiter la cause.
- Métriques Prometheus refusées : vérifier `PROMETHEUS_MULTIPROC_DIR` et l’UID/GID 10001.
- Quota atteint : ne pas augmenter silencieusement la limite ; faire valider la capacité et l’édition.
