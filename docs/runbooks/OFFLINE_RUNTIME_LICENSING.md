# Licence runtime offline OpenInfra

## Objet

Les éditions **Pro** et **Enterprise** exigent une licence commerciale signée pour autoriser le runtime lorsque `OPENINFRA_LICENSE_ENFORCEMENT=true`. L’édition **Lite** n’utilise pas cette licence.

La licence est liée cryptographiquement aux éléments suivants :

- UUID immuable de l’installation ;
- UUID de licence ;
- raison sociale de l’entreprise ;
- édition OpenInfra ;
- clé publique Ed25519 de l’installation ;
- plafond contractuel d’hôtes gérés ;
- dates de validité et période de grâce fixe de 30 jours.

Le serveur client ne nécessite aucun accès Internet. La clé privée de l’autorité de licence reste exclusivement dans l’environnement d’émission hors ligne et doit être chiffrée par mot de passe.

## Préconditions de sécurité

1. Générer les UUID avec une source cryptographiquement sûre, par exemple `uuidgen`.
2. Conserver le mot de passe d’autorité dans un secret manager ou un fichier temporaire de mode `0600`.
3. Ne jamais transférer la clé privée d’autorité vers le client.
4. Distribuer uniquement la clé publique de confiance dans `OPENINFRA_LICENSE_TRUST_BUNDLE`.
5. Protéger les répertoires de licence avec un propriétaire système dédié et des droits minimaux.
6. Sauvegarder l’état de licence avec la base OpenInfra ; ne jamais modifier manuellement les documents signés.

## 1. Génération de l’autorité hors ligne

Cette opération est réalisée une seule fois dans l’environnement sécurisé de l’éditeur :

```bash
install -d -m 0700 /srv/openinfra-license-authority
install -m 0600 /dev/null /run/openinfra-authority-password
printf '%s' "$OPENINFRA_AUTHORITY_PASSWORD" > /run/openinfra-authority-password

openinfra license authority-generate \
  --password-file /run/openinfra-authority-password \
  --private-key /srv/openinfra-license-authority/authority-private.pem \
  --public-key /srv/openinfra-license-authority/authority-public.pem

shred -u /run/openinfra-authority-password
```

La clé publique produite doit être distribuée aux installations Pro et Enterprise. La clé privée chiffrée doit être sauvegardée dans un coffre hors ligne avec contrôle d’accès et journalisation.

## 2. Bootstrap de l’installation cliente

Exemple PostgreSQL pour une édition Pro :

```bash
install -d -m 0700 -o openinfra -g openinfra /opt/openinfra/config/licensing

openinfra license bootstrap \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --edition pro \
  --installation-id "$(uuidgen)" \
  --license-id "$(uuidgen)" \
  --company "Entreprise Cliente SAS" \
  --max-hosts 500 \
  --output-dir /opt/openinfra/config/licensing \
  --actor installer
```

Le bootstrap :

- génère une paire Ed25519 propre à l’installation ;
- persiste l’identité immuable dans le backend sélectionné ;
- crée `installation-identity.json`, `activation-request.json`, `installation-private.pem` et `installation-public.pem` ;
- applique des permissions Unix strictes ;
- signe la demande avec la clé privée de l’installation.

Transférer uniquement `activation-request.json` vers l’environnement d’émission.

Pour Oracle Enterprise, remplacer les paramètres de connexion par :

```bash
--backend oracle \
--oracle-dsn "$OPENINFRA_ORACLE_DSN" \
--oracle-user "$OPENINFRA_ORACLE_USER" \
--edition enterprise
```

## 3. Émission de l’entitlement hors ligne

```bash
install -m 0600 /dev/null /run/openinfra-authority-password
printf '%s' "$OPENINFRA_AUTHORITY_PASSWORD" > /run/openinfra-authority-password

openinfra license issue \
  --request ./activation-request.json \
  --authority-private-key /srv/openinfra-license-authority/authority-private.pem \
  --password-file /run/openinfra-authority-password \
  --max-hosts 500 \
  --not-before 2026-07-20T00:00:00+00:00 \
  --expires-at 2027-07-20T00:00:00+00:00 \
  --output ./openinfra-entitlement.json

shred -u /run/openinfra-authority-password
```

L’émission refuse notamment :

- une demande dont la signature d’installation est invalide ;
- une limite d’hôtes supérieure à la demande signée ;
- une clé privée autre qu’Ed25519 ;
- une échéance antérieure ou égale à la date de prise d’effet ;
- une période de grâce différente de 30 jours.

Transférer uniquement `openinfra-entitlement.json` vers le client.

## 4. Activation

Le trust bundle doit pointer vers la clé publique de l’autorité :

```bash
install -m 0644 authority-public.pem /opt/openinfra/config/licensing/authority-public.pem
export OPENINFRA_LICENSE_TRUST_BUNDLE=/opt/openinfra/config/licensing/authority-public.pem
export OPENINFRA_LICENSE_ENFORCEMENT=true

openinfra license activate \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --edition pro \
  --entitlement ./openinfra-entitlement.json \
  --actor license-administrator
```

L’activation est transactionnelle : la signature, les bindings et le quota d’hôtes sont vérifiés sous la même unité de travail que la persistance et l’événement d’audit.

## 5. Vérification opérationnelle

```bash
openinfra license status \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --edition pro
```

États possibles :

- `not_required` : édition Lite ;
- `missing` : identité ou entitlement absent ;
- `active` : licence valide ;
- `grace` : licence expirée, période de renouvellement de 30 jours active ;
- `expired` : licence et période de grâce expirées ;
- `invalid` : signature, binding, quota, persistance ou horloge invalide.

En mode enforced, les états `missing`, `expired` et `invalid` bloquent les commandes métier et l’API renvoie HTTP `402 Payment Required`. Le portail affiche une notification accessible et rafraîchit l’état toutes les heures.

## 6. Renouvellement

Le client régénère ou réutilise sa demande d’activation liée à la même identité. L’éditeur émet un nouvel entitlement avec la même licence et une date d’expiration strictement postérieure. Le client applique ensuite :

```bash
openinfra license renew \
  --backend postgresql \
  --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --edition pro \
  --entitlement ./openinfra-entitlement-renewed.json \
  --actor license-administrator
```

Le renouvellement refuse tout changement d’installation, d’UUID de licence, d’entreprise, d’édition ou de fingerprint de clé publique.

## 7. Configuration de production

Exemple de configuration :

```ini
OPENINFRA_EDITION=pro
OPENINFRA_LICENSE_ENFORCEMENT=true
OPENINFRA_LICENSE_TRUST_BUNDLE=/opt/openinfra/config/licensing/authority-public.pem
```

Pour Enterprise avec Oracle :

```ini
OPENINFRA_EDITION=enterprise
OPENINFRA_DATABASE_BACKEND=oracle
OPENINFRA_LICENSE_ENFORCEMENT=true
OPENINFRA_LICENSE_TRUST_BUNDLE=/opt/openinfra/config/licensing/authority-public.pem
```

Ne pas activer l’enforcement avant que l’identité, le trust bundle et l’entitlement aient été installés, sauf lors d’un test explicite du comportement fail-closed.

## 8. Sauvegarde, restauration et reprise

- Sauvegarder l’état de licence dans la même politique que la base métier.
- Sauvegarder séparément `/opt/openinfra/config/licensing` en conservant les modes Unix.
- Restaurer la base et les fichiers sur la même installation ; une duplication vers une autre installation est rejetée par le binding cryptographique.
- Après restauration, exécuter `openinfra license status` avant d’ouvrir le trafic.
- Une restauration avec une horloge reculée de plus de cinq minutes est rejetée jusqu’à correction de l’horloge.

## 9. Qualification GATE-12

```bash
openinfra-gate12 \
  --project-root . \
  --candidate-id openinfra-0.34.19-rc1 \
  --source-commit "$(git rev-parse HEAD)" \
  --output artifacts/gate12/report.json \
  --enforce
```

GATE-12 exige sept contrôles : cryptographie, parité de stockage, enforcement runtime, CLI/HTTP, installateur, notification opérateur et sécurité du matériel de clé. La promotion REL-13 est interdite si un contrôle échoue.
