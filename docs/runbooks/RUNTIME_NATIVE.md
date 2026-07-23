# Runbook production — déploiement serveur natif OpenInfra

OpenInfra s’exécute directement sur des serveurs Linux sous systemd. Docker ne fait pas partie de la chaine d'execution production. Docker sert uniquement aux essais locaux et aux smokes facultatifs ; il n’est ni requis ni supposé en production. PostgreSQL 15+ reste le backend par défaut. Oracle Database est disponible uniquement pour l’édition Enterprise.

## Systèmes cibles

- Debian 12 / Ubuntu 22.04 LTS ou version supérieure ;
- RHEL 9 compatible ou équivalent entreprise ;
- Python 3.11 ou supérieur ;
- PostgreSQL 15+ par défaut, ou Oracle Database lorsque sélectionné ;
- compte système non privilégié `openinfra`.

## Arborescence

```text
/opt/openinfra                         application, virtualenv et assets
/opt/openinfra/config/openinfra.conf   configuration runtime canonique
/etc/openinfra                         symlink vers /opt/openinfra/config
/etc/openinfra/secrets                 secrets administrés hors configuration
/opt/openinfra/share/migrations        migrations du backend sélectionné
/var/lib/openinfra/secrets             jeton bootstrap runtime
/var/lib/openinfra/team-sync            snapshots Auth Proxy éventuels
/var/log/openinfra                     journaux fichiers éventuels
```

## Installation

```bash
sudo groupadd --system openinfra 2>/dev/null || true
id openinfra >/dev/null 2>&1 || sudo useradd --system --gid openinfra --home-dir /opt/openinfra --shell /usr/sbin/nologin openinfra
sudo install -d -o openinfra -g openinfra -m 0750 /opt/openinfra /opt/openinfra/config /var/log/openinfra
sudo install -d -o root -g openinfra -m 0750 /etc/openinfra/secrets /var/lib/openinfra/secrets /var/lib/openinfra/team-sync
sudo ln -sfn /opt/openinfra/config /etc/openinfra
python3.11 -m venv /opt/openinfra/venv
/opt/openinfra/venv/bin/python -m pip install --upgrade pip
/opt/openinfra/venv/bin/python -m pip install '/opt/openinfra/openinfra-0.34.20-py3-none-any.whl[postgresql,advanced-identity]'
```

Pour Oracle, utiliser l’extra `oracle` à la place de `postgresql`.

## Configuration canonique

Les installateurs fusionnent les paramètres de bootstrap dans `/opt/openinfra/config/openinfra.conf`. Les secrets ne sont pas stockés en clair dans ce fichier : utiliser des références `file://`, ou le mécanisme sécurisé de l’entreprise.

Configuration PostgreSQL minimale :

```ini
OPENINFRA_EDITION="enterprise"
OPENINFRA_SCOPE="server"
OPENINFRA_DATABASE_BACKEND="postgresql"
OPENINFRA_DATABASE_DSN_REF="file:///etc/openinfra/secrets/postgresql-dsn"
OPENINFRA_RUNTIME_CONFIG="/opt/openinfra/config/openinfra.conf"
OPENINFRA_MIGRATIONS_ROOT="/opt/openinfra/share/migrations/postgresql"
```

Oracle est refusé en Lite et Pro avant tout chargement du pilote ou accès réseau.

Configuration Oracle minimale :

```ini
OPENINFRA_DATABASE_BACKEND="oracle"
OPENINFRA_ORACLE_DSN="db.internal:1521/OPENINFRA"
OPENINFRA_ORACLE_USER="OPENINFRA"
OPENINFRA_ORACLE_PASSWORD_REF="file:///etc/openinfra/secrets/oracle-password"
OPENINFRA_MIGRATIONS_ROOT="/opt/openinfra/share/migrations/oracle"
```

Les paramètres SAML, LDAP avancé et Team Sync sont documentés dans `ADVANCED_IDENTITY_ORACLE_SYSTEMD.md`.

## Unités systemd

- `openinfra-runtime-secrets.service` : génère le jeton bootstrap sous l’identité Unix réelle ;
- `openinfra-migrate.service` : applique les migrations du backend sélectionné ;
- `openinfra.service` : API/backend ;
- `openinfra-web.service` : BFF et portail Web ;
- `openinfra-team-sync.service` : synchronisation one-shot ;
- `openinfra-team-sync.timer` : planification persistante ;
- `openinfra-agent.service` : proxy collector Enterprise uniquement.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openinfra-runtime-secrets.service
sudo systemctl start openinfra-migrate.service
sudo systemctl enable --now openinfra.service openinfra-web.service openinfra-team-sync.timer
```

## Migrations

```bash
sudo -u openinfra /opt/openinfra/venv/bin/openinfra-server-runtime migrate
```

Le runtime lit `OPENINFRA_DATABASE_BACKEND` depuis `openinfra.conf`. En l’absence de valeur, PostgreSQL est sélectionné. Oracle n’est jamais activé implicitement.

## Identité et autorité RBAC

SAML et LDAP authentifient ou alimentent des identités externes. L’autorité finale reste le RBAC OpenInfra : les groupes externes sont traduits en rôles par des mappings configurés côté serveur. Team Sync ne supprime pas une identité locale non gérée par sa source et ne retire que les appartenances qu’elle possède.

## Exploitation

```bash
sudo systemctl status openinfra.service openinfra-web.service openinfra-team-sync.timer
sudo systemctl restart openinfra.service openinfra-web.service
sudo systemctl stop openinfra-team-sync.timer openinfra-web.service openinfra.service
sudo journalctl -u openinfra.service -u openinfra-web.service -u openinfra-team-sync.service -f
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/ready
```

## Mise à jour sûre

1. sauvegarder la configuration, les secrets et la base ;
2. installer le nouveau wheel dans le virtualenv ;
3. appliquer les migrations ;
4. redémarrer l’API et le Web ;
5. vérifier `/ready`, les logs et un Team Sync de qualification ;
6. conserver le wheel précédent pour rollback applicatif, sans annuler une migration déjà appliquée.
