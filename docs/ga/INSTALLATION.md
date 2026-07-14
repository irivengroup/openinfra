# Installation et démarrage

Version cible : `0.33.3`

## Prérequis

Pour le runtime Docker local :

- Docker Engine 26 ou Docker Desktop récent ;
- plugin Docker Compose v2 ;
- Python 3.11 ou supérieur pour les scripts d’administration ;
- ports locaux 2006, 5050 et 8080 disponibles ;
- au moins 4 vCPU, 8 Gio de RAM et 20 Gio libres pour la topologie complète.

Pour la production native : Linux compatible RHEL 9, Debian 12, Ubuntu 22.04 LTS ou version supérieure, `systemd`, LVM et PostgreSQL 15 ou supérieur.

## Docker Compose

Depuis la racine du projet :

```powershell
python scripts/docker_environment.py init

docker compose --env-file .env config --quiet

python scripts/docker_environment.py up
```

Démarrage avec observabilité :

```powershell
docker compose --env-file .env --profile observability up --build -d
```

État des services :

```powershell
python scripts/docker_environment.py status

docker compose --env-file .env --profile observability ps
```

Contrôles fonctionnels :

```powershell
curl.exe -f http://127.0.0.1:8080/health
curl.exe -f http://127.0.0.1:8080/ready
curl.exe -f http://127.0.0.1:8080/metrics
curl.exe -f http://127.0.0.1:2006/health
```

Validation Compose complète :

```powershell
python scripts/docker_environment.py validate
```

## Installation native

Toujours commencer par un dry-run du scope ciblé :

```bash
python installers/setup/lite/install.py --dry-run --json
python installers/setup/pro/server/install.py --dry-run --json
python installers/setup/pro/web/install.py --dry-run --json
python installers/setup/enterprise/server/install.py --dry-run --json
python installers/setup/enterprise/web/install.py --dry-run --json
python installers/setup/enterprise/agent/install.py --dry-run --json
```

Exemple d’installation Pro backend :

```bash
sudo OPENINFRA_DATABASE_DSN="$OPENINFRA_DATABASE_DSN" \
  python installers/setup/pro/server/install.py --execute
```

Exemple de construction d’une image système isolée :

```bash
python installers/setup/enterprise/server/install.py \
  --execute \
  --target-root /tmp/openinfra-enterprise-image \
  --skip-service-enable
```

Docker ne fait pas partie de la chaîne d’exécution production native. Les unités `openinfra.service`, `openinfra-web.service` et `openinfra-agent.service` sont rendues par les installateurs selon le scope.

## Validation post-installation

```bash
openinfra version
openinfra database status --root installers/migrations/postgresql
systemctl status openinfra.service --no-pager
journalctl -u openinfra.service -n 200 --no-pager
```

Pour un nœud web :

```bash
systemctl status openinfra-web.service --no-pager
curl -fsS http://127.0.0.1:2006/health
```

Pour un proxy collector Enterprise :

```bash
systemctl status openinfra-agent.service --no-pager
journalctl -u openinfra-agent.service -n 200 --no-pager
```

## Désinstallation contrôlée

L’arrêt Docker sans suppression des volumes :

```powershell
python scripts/docker_environment.py down
```

La remise à zéro destructive du laboratoire Docker :

```powershell
python scripts/docker_environment.py reset
```

Pour une installation native, arrêter et désactiver le service, archiver `/opt/openinfra/config`, vérifier les sauvegardes PostgreSQL, puis supprimer les fichiers uniquement selon la procédure de changement approuvée. Le filesystem PostgreSQL `/data/openinfra` ne doit jamais être supprimé avant validation explicite de la restauration et de la rétention.
