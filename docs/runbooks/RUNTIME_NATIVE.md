# Runbook production — déploiement serveur natif OpenInfra

OpenInfra est conçu pour être exécuté directement sur des serveurs Linux. Le runtime de production officiel est un service système natif piloté par `systemd`, avec Python virtualenv, configuration runtime canonique et PostgreSQL accessible via DSN ou références de secrets. Les fichiers Docker du dépôt servent uniquement aux essais locaux ou aux smokes optionnels ; ils ne sont pas requis pour installer, démarrer ni superviser OpenInfra en production.

## Systèmes cibles

- Debian 12, Ubuntu 22.04 LTS ou version supérieure.
- RHEL 9 compatible ou équivalent entreprise.
- Python 3.11 ou supérieur.
- PostgreSQL 15 ou supérieur, local ou clusterisé.
- Compte système dédié `openinfra`.

## Arborescence runtime

```text
/opt/openinfra              code applicatif, virtualenv, configuration réelle et migrations runtime
/opt/openinfra/config       configuration canonique, certificats, verrou d'installation
/etc/openinfra              symlink vers /opt/openinfra/config
/opt/openinfra/share        assets runtime, dont migrations PostgreSQL
/var/lib/openinfra          données locales JSON si backend JSON utilisé hors production critique
/var/log/openinfra          journaux du service si redirection fichier activée
```

Le filesystem applicatif `/opt/openinfra` est créé/validé par LVM pour les scopes applicatifs `all-in-one`, `server`, `web` et `enterprise/agent` conformément au CDC. Le scope `enterprise/agent` ne crée aucun LV PostgreSQL, aucun PGDATA, aucun symlink data et aucune migration backend.

## Installation native

```bash
sudo install -d -o root -g root -m 0755 /opt/openinfra
sudo install -d -o root -g openinfra -m 0750 /opt/openinfra/config /opt/openinfra/share /var/log/openinfra
sudo ln -sfn /opt/openinfra/config /etc/openinfra
python3.11 -m venv /opt/openinfra/venv
/opt/openinfra/venv/bin/python -m pip install --upgrade pip
/opt/openinfra/venv/bin/python -m pip install /opt/openinfra/openinfra-*.whl
```

Le compte système est créé par l'équipe d'exploitation selon les standards internes. Exemple générique :

```bash
sudo useradd --system --home-dir /opt/openinfra --shell /usr/sbin/nologin openinfra
```

## Configuration `/opt/openinfra/config/openinfra.conf`

`install.ini` et `.env` sont utilisés pendant le bootstrap. Après installation, la configuration runtime canonique est `/opt/openinfra/config/openinfra.conf`. Les unités systemd chargent `EnvironmentFile=/etc/openinfra/openinfra.conf`, qui pointe réellement vers `/opt/openinfra/config/openinfra.conf` via le symlink `/etc/openinfra`.

Exemple minimal backend :

```bash
OPENINFRA_EDITION="enterprise"
OPENINFRA_SCOPE="server"
OPENINFRA_RUNTIME_CONFIG="/opt/openinfra/config/openinfra.conf"
OPENINFRA_MIGRATIONS_ROOT="/opt/openinfra/share/migrations/postgresql"
OPENINFRA_DATABASE_DSN_REF="env:OPENINFRA_DATABASE_DSN_SECRET"
OPENINFRA_INSTALL_SECURITY_TRANSPORT="mtls"
OPENINFRA_INSTALL_SECURITY_TLS_MIN_VERSION="TLSv1.3"
OPENINFRA_INSTALL_SECURITY_MTLS_REQUIRED="true"
PYTHONUNBUFFERED="1"
```

Le DSN peut pointer vers un cluster PostgreSQL, un VIP, un service DNS interne ou un proxy haute disponibilité. Les secrets sont fournis par le gestionnaire de secrets de l'entreprise, par fichier protégé ou par mécanisme d'injection système sécurisé. Aucun secret n'est stocké dans le code ni en clair dans `openinfra.conf`.

Permissions attendues :

```bash
sudo chown root:openinfra /opt/openinfra/config/openinfra.conf
sudo chmod 0640 /opt/openinfra/config/openinfra.conf
sudo chown -h root:root /etc/openinfra
```

## Verrou d'installation

Après succès, l'installateur crée `/opt/openinfra/config/.openinfra-installed.lock`. Une seconde installation doit s'arrêter avant toute modification lorsque ce verrou existe. Une réinstallation contrôlée doit passer par la procédure de maintenance avec sauvegarde et rollback.

## Service `systemd`

Les unités sont rendues par l'installateur selon l'édition et le scope. Aucun fichier statique `deploy/systemd` n'est livré. Exemple de rendu backend :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli installer render-systemd --edition enterprise --scope server \
  | sudo tee /etc/systemd/system/openinfra.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now openinfra.service
sudo systemctl status openinfra.service
```

La commande de démarrage utilise directement le binaire Python installé dans `/opt/openinfra/venv/bin/openinfra-api`. Les protections `systemd` sont rendues par l'installateur, limitent l'accès au système de fichiers et bloquent les privilèges additionnels.

## Migrations PostgreSQL

Avant ouverture du service aux utilisateurs :

```bash
/opt/openinfra/venv/bin/openinfra database render-migration --name 0014_dcim_energy_cooling_foundation --root /opt/openinfra/share/migrations/postgresql >/tmp/openinfra-0014.sql
/opt/openinfra/venv/bin/openinfra database apply-migrations --root /opt/openinfra/share/migrations/postgresql
```

La résolution du DSN suit l'ordre : argument `--postgres-dsn`, variable `OPENINFRA_DATABASE_DSN`, valeur ou référence présente dans `/opt/openinfra/config/openinfra.conf`.

## Sécurité des flux

- Lite : boucle locale uniquement.
- Frontend vers backend : HTTPS TLS 1.3 avec mTLS et jeton applicatif opérateur.
- Agent vers backend : HTTPS TLS 1.3 avec mTLS et jeton/enrôlement technique.
- Backend vers backend : TLS 1.3 avec mTLS et ports internes non exposés dans `install.ini`.

Le backend ne réalise pas de login LDAP/IPA opérateur direct. Le frontend porte l'authentification opérateur ; le backend applique API, RBAC et audit.

## Contrôles de santé

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/ready
/opt/openinfra/venv/bin/python /opt/openinfra/scripts/native_runtime_smoke.py --base-url http://127.0.0.1:8080
```

Le smoke natif valide les actifs de déploiement et, lorsque `--base-url` est fourni, vérifie `/health`, `/ready` et `/api/v1/version` sans dépendre d'un moteur de conteneurs.

## Exploitation

- Supervision : `systemctl is-active openinfra.service`, `/ready`, métriques externes et logs journald.
- Redémarrage : `sudo systemctl restart openinfra.service`.
- Arrêt contrôlé : `sudo systemctl stop openinfra.service`.
- Journal : `journalctl -u openinfra.service -f`.
- Mise à jour : installer la nouvelle roue Python, appliquer les migrations, puis redémarrer le service.

## Règles de production

1. Docker ne fait pas partie de la chaine d'execution production.
2. Le backend PostgreSQL est la persistance de référence pour la production.
3. Les migrations sont exécutées avant activation de la version applicative.
4. Les secrets sont gérés hors dépôt et hors image applicative.
5. Le service fonctionne sous utilisateur non privilégié.
6. Les contrôles `/health` et `/ready` sont intégrés au superviseur et au load balancer.

## CI GitHub Actions

Le workflow se déclenche sur toutes les branches en `push`, toutes les pull requests et via `workflow_dispatch`. Le runtime natif reste contrôlé dans `scripts/quality_gate.py`; Docker n'est pas une condition d'exécution production.
