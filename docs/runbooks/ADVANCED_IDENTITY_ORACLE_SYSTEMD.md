# Runbook — SAML, LDAP avancé, Team Sync et Oracle sous systemd

## Objet et périmètre

Ce runbook décrit le déploiement natif OpenInfra Pro/Enterprise sur Linux, sans Docker. PostgreSQL est le backend par défaut. Oracle Database est activé uniquement par configuration explicite. Les paramètres de confiance et les secrets d’identité restent côté serveur ; les clients HTTP ne peuvent pas fournir de certificat SAML, d’endpoint fournisseur, de jeton OAuth/Okta ni de secret Auth Proxy.

## Comptes, chemins et permissions

```bash
sudo groupadd --system openinfra 2>/dev/null || true
id openinfra >/dev/null 2>&1 || sudo useradd --system --gid openinfra --home-dir /opt/openinfra --shell /usr/sbin/nologin openinfra
sudo install -d -o openinfra -g openinfra -m 0750 /opt/openinfra /opt/openinfra/config /var/log/openinfra
sudo install -d -o root -g openinfra -m 0750 /var/lib/openinfra/secrets /etc/openinfra/secrets
sudo ln -sfn /opt/openinfra/config /etc/openinfra
```

Le jeton bootstrap est créé par `openinfra-runtime-secrets.service`. Le répertoire reste `0700` et le fichier `0400`, tous deux attribués à l’utilisateur/groupe OpenInfra effectif.

## Backend PostgreSQL par défaut

`/opt/openinfra/config/openinfra.conf` :

```ini
OPENINFRA_EDITION="enterprise"
OPENINFRA_SCOPE="server"
OPENINFRA_DATABASE_BACKEND="postgresql"
OPENINFRA_DATABASE_DSN_REF="file:///etc/openinfra/secrets/postgresql-dsn"
OPENINFRA_CURSOR_SIGNING_SECRET_REF="file:///etc/openinfra/secrets/cursor-signing-secret"
OPENINFRA_RUNTIME_CONFIG="/opt/openinfra/config/openinfra.conf"
OPENINFRA_MIGRATIONS_ROOT="/opt/openinfra/share/migrations/postgresql"
```

```bash
sudo install -o root -g openinfra -m 0640 /dev/stdin /etc/openinfra/secrets/postgresql-dsn <<'EOF_SECRET'
postgresql://openinfra:REPLACE_AT_DEPLOYMENT@db-vip.internal:5432/openinfra
EOF_SECRET
```

Le secret réel doit être injecté par le gestionnaire de secrets de l’entreprise. La valeur ci-dessus est uniquement un gabarit d’exploitation et ne doit pas être validée en production.

## Backend Oracle optionnel

```ini
OPENINFRA_DATABASE_BACKEND="oracle"
OPENINFRA_ORACLE_DSN="db.example.internal:1521/OPENINFRA"
OPENINFRA_ORACLE_USER="OPENINFRA"
OPENINFRA_ORACLE_PASSWORD_REF="file:///etc/openinfra/secrets/oracle-password"
OPENINFRA_ORACLE_POOL_MIN="1"
OPENINFRA_ORACLE_POOL_MAX="10"
OPENINFRA_ORACLE_POOL_INCREMENT="1"
OPENINFRA_ORACLE_TIMEOUT_SECONDS="30"
OPENINFRA_MIGRATIONS_ROOT="/opt/openinfra/share/migrations/oracle"
```

```bash
sudo install -o root -g openinfra -m 0640 /dev/stdin /etc/openinfra/secrets/oracle-password
```

Saisir le mot de passe dans l’entrée standard sans l’inscrire dans l’historique shell. Le mode thin de `python-oracledb` est utilisé par défaut ; Oracle Client n’est pas requis pour ce mode.

### Catalogue et application des migrations Oracle

OpenInfra livre un catalogue Oracle 19c complet de `0001_bootstrap.sql` à `0057_federated_identity_team_sync.sql`. Chaque migration conserve le numéro et le nom fonctionnel de sa source PostgreSQL. Le manifeste `manifest.json` contient les empreintes SHA-256 PostgreSQL/Oracle et le nombre d’instructions attendues.

Avant promotion d’une release depuis les sources :

```bash
python scripts/validate_oracle_migrations.py
```

Cette commande ne modifie aucun fichier. Elle échoue si le catalogue Oracle, le manifeste, l’ordre, un nom ou une empreinte diverge de la conversion déterministe attendue. La régénération explicite, réservée au développement, utilise :

```bash
python scripts/generate_oracle_migrations.py
python scripts/validate_oracle_migrations.py
```

Sur le serveur cible, après sauvegarde Oracle et avec le compte applicatif réel :

```bash
sudo -u openinfra /opt/openinfra/venv/bin/openinfra database status \
  --backend oracle \
  --root /opt/openinfra/share/migrations/oracle
sudo -u openinfra /opt/openinfra/venv/bin/openinfra database apply-migrations \
  --backend oracle \
  --root /opt/openinfra/share/migrations/oracle
sudo -u openinfra /opt/openinfra/venv/bin/openinfra database status \
  --backend oracle \
  --root /opt/openinfra/share/migrations/oracle
```

L’état final doit indiquer `expected_count=57`, `applied_count=57`, `current=true` et une liste `drift` vide. Le journal `openinfra_schema_migrations` conserve les états `applying`, `applied` ou `failed`, l’empreinte Oracle, l’empreinte PostgreSQL source et le message d’erreur borné. Une ancienne installation ne contenant que `0001_document_state.sql` est reprise de manière compatible.

Oracle valide implicitement de nombreuses instructions DDL. OpenInfra ne revendique donc pas un rollback transactionnel global du DDL : les opérations DML sont annulées lorsque le pilote le permet, l’échec est persisté, et la reprise DDL est limitée aux erreurs idempotentes explicitement reconnues. Une sauvegarde/restauration Oracle testée reste obligatoire avant toute montée de version de production.

## SAML 2.0

```ini
OPENINFRA_SAML_TENANT_ID="default"
OPENINFRA_SAML_IDP_ENTITY_ID="https://idp.example.internal/metadata"
OPENINFRA_SAML_IDP_SSO_URL="https://idp.example.internal/sso"
OPENINFRA_SAML_IDP_X509_CERT_REF="file:///etc/openinfra/secrets/saml-idp.crt"
OPENINFRA_SAML_SP_ENTITY_ID="https://openinfra.example.internal/saml/metadata"
OPENINFRA_SAML_SP_ACS_URL="https://openinfra.example.internal/api/v1/auth/saml/acs"
OPENINFRA_SAML_SUBJECT_ATTRIBUTE="uid"
OPENINFRA_SAML_DISPLAY_NAME_ATTRIBUTE="displayName"
OPENINFRA_SAML_EMAIL_ATTRIBUTE="mail"
OPENINFRA_SAML_GROUPS_ATTRIBUTE="groups"
OPENINFRA_SAML_WANT_ASSERTIONS_SIGNED="true"
OPENINFRA_SAML_WANT_MESSAGES_SIGNED="false"
OPENINFRA_SAML_CLOCK_SKEW_SECONDS="120"
OPENINFRA_SAML_GROUP_ROLE_MAPPINGS="OpenInfra-Admins=admin;OpenInfra-Readers=reader"
```

```bash
sudo install -o root -g openinfra -m 0640 saml-idp.crt /etc/openinfra/secrets/saml-idp.crt
```

Le certificat, les mappings et les URLs sont relus depuis la configuration serveur à chaque initialisation du runtime. Ils ne sont jamais acceptés depuis la requête ACS.

## LDAP/IPA avancé

```ini
OPENINFRA_LDAP_MODE="ldap"
OPENINFRA_LDAP_URL="ldaps://ipa.example.internal:636"
OPENINFRA_LDAP_BASE_DN="dc=example,dc=internal"
OPENINFRA_LDAP_USER_BASE_DN="cn=users,cn=accounts,dc=example,dc=internal"
OPENINFRA_LDAP_GROUP_BASE_DN="cn=groups,cn=accounts,dc=example,dc=internal"
OPENINFRA_LDAP_USER_FILTER="(uid={username})"
OPENINFRA_LDAP_GROUP_FILTER="(member={user_dn})"
OPENINFRA_LDAP_BIND_DN_REF="file:///etc/openinfra/secrets/ldap-bind-dn"
OPENINFRA_LDAP_BIND_PASSWORD_REF="file:///etc/openinfra/secrets/ldap-bind-password"
OPENINFRA_LDAP_CA_CERT_REF="file:///etc/openinfra/secrets/ldap-ca.pem"
OPENINFRA_LDAP_PAGE_SIZE="500"
OPENINFRA_LDAP_SIZE_LIMIT="5000"
OPENINFRA_LDAP_CONNECT_TIMEOUT_SECONDS="5"
OPENINFRA_LDAP_OPERATION_TIMEOUT_SECONDS="15"
OPENINFRA_LDAP_FOLLOW_REFERRALS="false"
OPENINFRA_LDAP_START_TLS="false"
OPENINFRA_LDAP_NESTED_GROUPS="true"
OPENINFRA_LDAP_NESTED_GROUP_DEPTH="5"
```

Pour StartTLS, utiliser une URL `ldap://`, positionner `OPENINFRA_LDAP_START_TLS=true` et conserver une CA explicitement approuvée.

## Team Sync

Activer les sources :

```ini
OPENINFRA_TEAM_SYNC_SOURCES="ldap-main,oauth-hr,auth-proxy,okta-main"
```

Exemple LDAP :

```ini
OPENINFRA_TEAM_SYNC_LDAP_MAIN_PROVIDER="ldap"
OPENINFRA_TEAM_SYNC_LDAP_MAIN_TENANT_ID="default"
OPENINFRA_TEAM_SYNC_LDAP_MAIN_DEACTIVATE_ORPHANS="true"
OPENINFRA_TEAM_SYNC_LDAP_MAIN_GROUP_ROLE_MAPPINGS="OpenInfra-Admins=admin;OpenInfra-Readers=reader"
```

Exemple OAuth/Okta :

```ini
OPENINFRA_TEAM_SYNC_OAUTH_HR_PROVIDER="oauth"
OPENINFRA_TEAM_SYNC_OAUTH_HR_TENANT_ID="default"
OPENINFRA_TEAM_SYNC_OAUTH_HR_ENDPOINT="https://identity.example.internal/openinfra/teams"
OPENINFRA_TEAM_SYNC_OAUTH_HR_TOKEN_REF="file:///etc/openinfra/secrets/oauth-hr-token"
OPENINFRA_TEAM_SYNC_OKTA_MAIN_PROVIDER="okta"
OPENINFRA_TEAM_SYNC_OKTA_MAIN_TENANT_ID="default"
OPENINFRA_TEAM_SYNC_OKTA_MAIN_ENDPOINT="https://example.okta.com/api/v1"
OPENINFRA_TEAM_SYNC_OKTA_MAIN_TOKEN_REF="file:///etc/openinfra/secrets/okta-token"
```

La pagination est limitée à la même origine HTTPS que l’endpoint configuré.

Exemple Auth Proxy :

```ini
OPENINFRA_TEAM_SYNC_AUTH_PROXY_PROVIDER="auth_proxy"
OPENINFRA_TEAM_SYNC_AUTH_PROXY_TENANT_ID="default"
OPENINFRA_TEAM_SYNC_AUTH_PROXY_SNAPSHOT_FILE="/var/lib/openinfra/team-sync/auth-proxy.json"
OPENINFRA_TEAM_SYNC_AUTH_PROXY_SIGNATURE_SECRET_REF="file:///etc/openinfra/secrets/auth-proxy-hmac"
```

Le snapshot doit être un fichier normal, non symbolique, avec signature HMAC valide.

## Installation et unités systemd

```bash
sudo /opt/openinfra/venv/bin/python -m pip install '/opt/openinfra/openinfra-0.34.2-py3-none-any.whl[postgresql,advanced-identity]'
# Oracle : remplacer postgresql par oracle.
sudo install -o root -g root -m 0644 installers/systemd/openinfra-runtime-secrets.service /etc/systemd/system/
sudo install -o root -g root -m 0644 installers/systemd/openinfra-migrate.service /etc/systemd/system/
sudo install -o root -g root -m 0644 installers/systemd/openinfra-team-sync.service /etc/systemd/system/
sudo install -o root -g root -m 0644 installers/systemd/openinfra-team-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openinfra-runtime-secrets.service
sudo systemctl start openinfra-migrate.service
sudo systemctl enable --now openinfra.service openinfra-web.service openinfra-team-sync.timer
```

## Vérifications

```bash
sudo systemctl --no-pager --full status openinfra-runtime-secrets.service openinfra-migrate.service openinfra.service openinfra-web.service openinfra-team-sync.timer
sudo journalctl -u openinfra-migrate.service -u openinfra.service -u openinfra-team-sync.service --since today
sudo -u openinfra test -r /var/lib/openinfra/secrets/bootstrap-token
sudo stat -c '%U:%G %a %n' /var/lib/openinfra/secrets /var/lib/openinfra/secrets/bootstrap-token
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/ready
```

L’état attendu du secret est `openinfra:openinfra 700` pour le répertoire et `openinfra:openinfra 400` pour le fichier.

## Rollback

1. arrêter le timer Team Sync et les services applicatifs ;
2. restaurer le wheel précédent dans le virtualenv ;
3. restaurer la configuration et les secrets depuis leur sauvegarde contrôlée ;
4. ne jamais supprimer une migration déjà appliquée ; appliquer uniquement une migration corrective compatible ;
5. redémarrer les services et vérifier `/ready`, les journaux et l’état de migration.

```bash
sudo systemctl stop openinfra-team-sync.timer openinfra-web.service openinfra.service
sudo /opt/openinfra/venv/bin/python -m pip install --force-reinstall /opt/openinfra/releases/openinfra-0.34.1-py3-none-any.whl
sudo systemctl start openinfra-migrate.service openinfra.service openinfra-web.service openinfra-team-sync.timer
```
