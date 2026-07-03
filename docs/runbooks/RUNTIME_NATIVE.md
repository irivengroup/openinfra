# Runbook production — déploiement serveur natif OpenInfra

OpenInfra est conçu pour être exécuté directement sur des serveurs Linux. Le runtime de production officiel est un service système natif piloté par `systemd`, avec Python virtualenv et PostgreSQL accessible via DSN. Les fichiers Docker du dépôt servent uniquement aux essais locaux ou aux smokes optionnels ; ils ne sont pas requis pour installer, démarrer ni superviser OpenInfra en production.

## Systèmes cibles

- Debian 12, Ubuntu 22.04 LTS ou version supérieure.
- RHEL 9 compatible ou équivalent entreprise.
- Python 3.11 ou supérieur.
- PostgreSQL 15 ou supérieur, local ou clusterisé.
- Compte système dédié `openinfra`.

## Arborescence recommandée

```text
/opt/openinfra              code applicatif, virtualenv et documentation
/etc/openinfra              configuration d'environnement
/var/lib/openinfra          données locales JSON si backend JSON utilisé hors production critique
/var/log/openinfra          journaux du service si redirection fichier activée
```

## Installation native

```bash
sudo install -d -o root -g root -m 0755 /opt/openinfra
sudo install -d -o openinfra -g openinfra -m 0750 /etc/openinfra /var/lib/openinfra /var/log/openinfra
python3.11 -m venv /opt/openinfra/venv
/opt/openinfra/venv/bin/python -m pip install --upgrade pip
/opt/openinfra/venv/bin/python -m pip install /opt/openinfra/openinfra-*.whl
```

Le compte système est créé par l’équipe d’exploitation selon les standards internes. Exemple générique :

```bash
sudo useradd --system --home-dir /var/lib/openinfra --shell /usr/sbin/nologin openinfra
```

## Configuration `/etc/openinfra/openinfra.env`

```bash
OPENINFRA_DATABASE_DSN=postgresql://openinfra@postgresql.service/openinfra
OPENINFRA_AUTH_REQUIRED=true
PYTHONUNBUFFERED=1
```

Le DSN peut pointer vers un cluster PostgreSQL, un VIP, un service DNS interne ou un proxy haute disponibilité. Les secrets sont fournis par le gestionnaire de secrets de l’entreprise, par fichier d’environnement protégé ou par mécanisme d’injection système sécurisé. Aucun secret n’est stocké dans le code.

Permissions attendues :

```bash
sudo chown root:openinfra /etc/openinfra/openinfra.env
sudo chmod 0640 /etc/openinfra/openinfra.env
```

## Service `systemd`

Le fichier livré `deploy/systemd/openinfra-api.service` lance l’API native :

```bash
sudo install -o root -g root -m 0644 deploy/systemd/openinfra-api.service /etc/systemd/system/openinfra-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now openinfra-api.service
sudo systemctl status openinfra-api.service
```

La commande de démarrage utilise directement le binaire Python installé dans `/opt/openinfra/venv/bin/openinfra-api`. Les protections `systemd` limitent l’accès au système de fichiers, bloquent les privilèges additionnels et n’autorisent l’écriture que dans `/var/lib/openinfra`, `/var/log/openinfra` et `/etc/openinfra`.

## Migrations PostgreSQL

Avant ouverture du service aux utilisateurs :

```bash
/opt/openinfra/venv/bin/openinfra database render-migration --name 0014_dcim_energy_cooling_foundation --root /opt/openinfra/migrations/postgresql >/tmp/openinfra-0014.sql
/opt/openinfra/venv/bin/openinfra database apply-migrations --postgres-dsn "$OPENINFRA_DATABASE_DSN" --root /opt/openinfra/migrations/postgresql
```

La migration `0014_dcim_energy_cooling_foundation` ajoute les tables partitionnées pour PDU/UPS, circuits électriques, zones de refroidissement et réservations de puissance, ainsi que les index de recherche et d’audit.

## Contrôles de santé

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/ready
/opt/openinfra/venv/bin/python /opt/openinfra/scripts/native_runtime_smoke.py --base-url http://127.0.0.1:8080
```

Le smoke natif valide les actifs de déploiement et, lorsque `--base-url` est fourni, vérifie `/health`, `/ready` et `/api/v1/version` sans dépendre d’un moteur de conteneurs.

## Exploitation

- Supervision : `systemctl is-active openinfra-api.service`, `/ready`, métriques externes et logs journald.
- Redémarrage : `sudo systemctl restart openinfra-api.service`.
- Arrêt contrôlé : `sudo systemctl stop openinfra-api.service`.
- Journal : `journalctl -u openinfra-api.service -f`.
- Mise à jour : installer la nouvelle roue Python, appliquer les migrations, puis redémarrer le service.

## Règles de production

1. Docker ne fait pas partie de la chaîne d’exécution production.
2. Le backend PostgreSQL est la persistance de référence pour la production.
3. Les migrations sont exécutées avant activation de la version applicative.
4. Les secrets sont gérés hors dépôt et hors image applicative.
5. Le service fonctionne sous utilisateur non privilégié.
6. Les contrôles `/health` et `/ready` sont intégrés au superviseur et au load balancer.


## CI GitHub Actions

Le workflow se déclenche sur toutes les branches en `push`, toutes les pull requests et via `workflow_dispatch`. Le runtime natif reste contrôlé dans `scripts/quality_gate.py`; Docker n’est pas une condition d’exécution production.
